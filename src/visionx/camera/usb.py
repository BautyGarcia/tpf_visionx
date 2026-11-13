"""Fuente de pares en vivo desde la cámara USB (ELP) con OpenCV.

Lo que aprendimos midiendo la ELP (BITACORA 2026-11-12) y que este módulo respeta:
- Si se pide un modo que la cámara no tiene, entrega otro sin avisar. Por eso se compara el
  tamaño recibido con el pedido y, si no coincide, se corta con SourceError.
- `CAP_PROP_FPS` informa 5 aunque la cámara entregue ~60. Los FPS se miden, no se leen.

Un fallo de lectura no es "fin de la grabación": se intenta reabrir la cámara unas veces y,
si no vuelve, se lanza SourceError. Los frame_id siguen corriendo después de reconectar, así
la identidad (session_id, frame_id) nunca se repite dentro de una sesión.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

import cv2
import numpy as np

from visionx.camera.sbs import split_sbs
from visionx.shared import _validate as v
from visionx.shared.clock import Clock, MonotonicClock
from visionx.shared.contracts import StereoFrame
from visionx.shared.errors import InvalidInput, SourceError

# Nombres de la config -> constantes de OpenCV. "auto" deja elegir a OpenCV.
BACKENDS = {
    "auto": cv2.CAP_ANY,
    "avfoundation": cv2.CAP_AVFOUNDATION,  # macOS
    "dshow": cv2.CAP_DSHOW,  # Windows, DirectShow
    "msmf": cv2.CAP_MSMF,  # Windows, Media Foundation
    "v4l2": cv2.CAP_V4L2,  # Linux
}


class VideoCaptureLike(Protocol):
    """Lo que usamos de cv2.VideoCapture. Los tests lo reemplazan por una cámara falsa."""

    def isOpened(self) -> bool: ...  # noqa: N802 (nombre de OpenCV)

    def read(self) -> tuple[bool, np.ndarray | None]: ...

    def release(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CameraSettings:
    """Cómo abrir la cámara. Sale de la sección `camera` de la config."""

    device: int = 0
    backend: str = "auto"
    capture_size: tuple[int, int] = (3840, 1080)  # (ancho, alto) del cuadro SBS completo
    fourcc: str = "MJPG"
    fps: int = 30  # pedido al driver; el valor real se mide
    swap_eyes: bool = False
    reconnect_attempts: int = 3
    reconnect_wait_s: float = 0.5
    warmup_frames: int = 5  # los primeros cuadros suelen salir oscuros o repetidos
    source_id: str = "elp"
    extra: dict[str, Any] = field(default_factory=dict)  # resto de la sección, solo informativo

    def __post_init__(self) -> None:
        v.non_negative_int("device", self.device)
        if self.backend not in BACKENDS:
            raise InvalidInput(f"backend desconocido {self.backend!r}; opciones: {list(BACKENDS)}")
        w, h = self.capture_size
        v.non_negative_int("capture_size ancho", w)
        v.non_negative_int("capture_size alto", h)
        if w == 0 or h == 0 or w % 2:
            raise InvalidInput(f"capture_size tiene que tener ancho par y > 0: {self.capture_size}")
        if len(self.fourcc) != 4:
            raise InvalidInput(f"fourcc tiene que tener 4 letras, llegó {self.fourcc!r}")
        v.non_negative_int("fps", self.fps)
        v.non_negative_int("reconnect_attempts", self.reconnect_attempts)
        v.finite("reconnect_wait_s", self.reconnect_wait_s, low=0.0)
        v.non_negative_int("warmup_frames", self.warmup_frames)
        v.text("source_id", self.source_id)

    @property
    def eye_size(self) -> tuple[int, int]:
        """(ancho, alto) de cada ojo."""
        w, h = self.capture_size
        return w // 2, h

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> CameraSettings:
        """Construye los ajustes desde la config completa (load_config())."""
        cam = dict(cfg.get("camera") or {})
        known = {
            "device": int(cam.pop("device", 0)),
            "backend": str(cam.pop("backend", "auto")),
            "capture_size": tuple(int(x) for x in cam.pop("capture", (3840, 1080))),
            "fourcc": str(cam.pop("fourcc", "MJPG")),
            "fps": int(cam.pop("fps", 30)),
            "swap_eyes": bool(cam.pop("swap_eyes", False)),
            "reconnect_attempts": int(cam.pop("reconnect_attempts", 3)),
            "warmup_frames": int(cam.pop("warmup_frames", 5)),
        }
        return cls(**known, extra=cam)

    def describe(self) -> dict[str, Any]:
        """Resumen para guardar en el manifiesto de una grabación."""
        return {
            "device": self.device,
            "backend": self.backend,
            "capture_pedido": list(self.capture_size),
            "fourcc": self.fourcc,
            "fps_pedido": self.fps,
            "swap_eyes": self.swap_eyes,
        }


def open_capture(settings: CameraSettings) -> VideoCaptureLike:
    """Abre la cámara con OpenCV y pide formato, tamaño y FPS."""
    cap = cv2.VideoCapture(settings.device, BACKENDS[settings.backend])
    # El formato va antes que el tamaño: algunos backends de Windows solo ofrecen
    # 3840x1080 en MJPEG y rechazan el tamaño si todavía están en YUY2.
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*settings.fourcc))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.capture_size[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.capture_size[1])
    cap.set(cv2.CAP_PROP_FPS, settings.fps)
    return cap


def new_session_id(source_id: str = "elp") -> str:
    """Id de sesión legible y único en la práctica: fuente + fecha y hora local."""
    return f"{source_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


@dataclass(slots=True)
class CaptureStats:
    """Contadores de una sesión en vivo, para el manifiesto y el diagnóstico."""

    frames: int = 0
    read_failures: int = 0
    reconnects: int = 0


class UsbStereoSource:
    """FrameSource en vivo: cada read() devuelve el próximo par de la ELP.

    No rectifica: para eso se envuelve con RectifiedSource. Así la grabación guarda el par
    original y la rectificación se puede rehacer con otra calibración.
    """

    def __init__(
        self,
        settings: CameraSettings,
        *,
        session_id: str | None = None,
        clock: Clock | None = None,
        open_fn: Callable[[CameraSettings], VideoCaptureLike] = open_capture,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.session_id = session_id or new_session_id(settings.source_id)
        v.text("session_id", self.session_id)
        self.stats = CaptureStats()
        self._clock = clock or MonotonicClock()
        self._open_fn = open_fn
        self._sleep = sleep
        self._next_id = 0
        self._cap: VideoCaptureLike | None = None
        self._open()

    # --- Apertura -------------------------------------------------------------------------

    def _open(self) -> None:
        cap = self._open_fn(self.settings)
        if not cap.isOpened():
            cap.release()
            raise SourceError(
                f"no se pudo abrir la cámara {self.settings.device} "
                f"(backend {self.settings.backend})"
            )
        try:
            for _ in range(self.settings.warmup_frames + 1):
                ok, image = cap.read()
            if not ok or image is None:
                raise SourceError("la cámara abrió pero no entrega imágenes")
            self._check_size(image)
        except SourceError:
            cap.release()
            raise
        self._cap = cap

    def _check_size(self, image: np.ndarray) -> None:
        got = (image.shape[1], image.shape[0])
        if got != self.settings.capture_size:
            w, h = self.settings.capture_size
            raise SourceError(
                f"la cámara entregó {got[0]}x{got[1]} en vez de {w}x{h}; la ELP cambia de modo "
                "sin avisar cuando el pedido no existe (revisar backend, fourcc y capture)"
            )

    # --- FrameSource ----------------------------------------------------------------------

    def read(self) -> StereoFrame:
        """Próximo par. En vivo nunca devuelve None: un fallo persistente es SourceError."""
        if self._cap is None:
            raise SourceError("la fuente está cerrada")
        ok, image = self._cap.read()
        if not ok or image is None:
            self.stats.read_failures += 1
            image = self._reconnect()
        received_ns = self._clock.now_ns()
        self._check_size(image)
        left, right = split_sbs(image, swap_eyes=self.settings.swap_eyes)
        frame = StereoFrame(
            session_id=self.session_id,
            frame_id=self._next_id,
            left=left,
            right=right,
            received_ns=received_ns,
            source_id=self.settings.source_id,
        )
        self._next_id += 1
        self.stats.frames += 1
        return frame

    def _reconnect(self) -> np.ndarray:
        """Reabre la cámara hasta reconnect_attempts veces y devuelve el primer cuadro."""
        last_error = "lectura fallida"
        for _ in range(self.settings.reconnect_attempts):
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            self._sleep(self.settings.reconnect_wait_s)
            try:
                self._open()
            except SourceError as exc:
                last_error = str(exc)
                continue
            self.stats.reconnects += 1
            assert self._cap is not None
            ok, image = self._cap.read()
            if ok and image is not None:
                return image
            last_error = "reabrió pero no entrega imágenes"
        self.close()
        raise SourceError(
            f"la cámara dejó de entregar cuadros y no volvió tras "
            f"{self.settings.reconnect_attempts} intentos: {last_error}"
        )

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
