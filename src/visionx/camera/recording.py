"""Grabar pares estéreo en disco para reprocesarlos después (replay).

Una grabación es una carpeta:

    manifest.yaml   qué se grabó: sesión, fuente, cámara, equipo, formato, estado y resumen
    frames.jsonl    una línea JSON por par: identidad, tiempos, archivos y SHA-256
    frames/         000000_L.jpg, 000000_R.jpg, ...

Par atómico: primero se escriben los dos archivos (con nombre temporal y después renombrados)
y recién entonces se agrega su línea a frames.jsonl. El replay solo confía en las líneas, así
que un corte a mitad de escritura deja a lo sumo imágenes sueltas que se ignoran, nunca un par
con un ojo de otro frame.

Las imágenes llegan decodificadas por OpenCV, así que se vuelven a comprimir una vez: JPEG de
calidad alta para grabaciones largas o PNG sin pérdida cuando el contenido exacto importa.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import queue
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from visionx.shared.contracts import SCHEMA_VERSION, StereoFrame
from visionx.shared.errors import IdentityMismatch, InvalidInput

FORMAT = "visionx-grabacion"
VERSION = 1
MANIFEST = "manifest.yaml"
INDEX = "frames.jsonl"
FRAMES_DIR = "frames"


@dataclass(frozen=True, slots=True)
class ImageFormat:
    """Cómo se guarda cada ojo."""

    ext: str = "jpg"  # jpg | png
    jpeg_quality: int = 95  # 0-100; 95 casi no deja artefactos visibles
    png_compression: int = 1  # 0-9; bajo = más rápido, archivos más grandes

    def __post_init__(self) -> None:
        if self.ext not in ("jpg", "png"):
            raise InvalidInput(f"formato de imagen {self.ext!r}: se admite jpg o png")
        if not 0 <= self.jpeg_quality <= 100:
            raise InvalidInput("jpeg_quality tiene que estar entre 0 y 100")
        if not 0 <= self.png_compression <= 9:
            raise InvalidInput("png_compression tiene que estar entre 0 y 9")

    def encode(self, image: np.ndarray) -> bytes:
        if self.ext == "jpg":
            params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
        else:
            params = [cv2.IMWRITE_PNG_COMPRESSION, self.png_compression]
        ok, buffer = cv2.imencode(f".{self.ext}", image, params)
        if not ok:
            raise OSError(f"OpenCV no pudo codificar la imagen como {self.ext}")
        return buffer.tobytes()

    def describe(self) -> dict[str, Any]:
        if self.ext == "jpg":
            return {"formato": "jpg", "calidad": self.jpeg_quality}
        return {"formato": "png", "compresion": self.png_compression}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def timing_summary(received_ns: Sequence[int]) -> dict[str, Any]:
    """FPS efectivo e intervalos entre pares, a partir de los tiempos de recepción.

    Un "hueco" es un intervalo mayor a 1,5 veces el típico (la mediana): un cuadro que la
    cámara no entregó o que se descartó.
    """
    n = len(received_ns)
    if n < 2:
        return {"pares": n}
    t = np.asarray(received_ns, dtype=np.int64)
    dt_ms = np.diff(t) / 1e6
    typical = float(np.median(dt_ms))
    span_s = float(t[-1] - t[0]) / 1e9  # float de Python: el manifiesto YAML no acepta numpy
    return {
        "pares": n,
        "duracion_s": round(span_s, 3),
        "fps_efectivo": round((n - 1) / span_s, 2) if span_s > 0 else None,
        "intervalo_mediano_ms": round(typical, 2),
        "intervalo_max_ms": round(float(dt_ms.max()), 2),
        "huecos": int(np.sum(dt_ms > 1.5 * typical)) if typical > 0 else 0,
    }


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)  # en el mismo disco, renombrar es atómico


def _equipo() -> dict[str, str]:
    return {
        "sistema": platform.platform(),
        "python": platform.python_version(),
        "opencv": cv2.__version__,
    }


_STOP = object()  # marca de fin para el hilo escritor


class Recorder:
    """Guarda StereoFrames de una misma sesión en una carpeta nueva.

    Con queue_size=0 escribe en el mismo hilo (simple; la captura espera al disco). Con
    queue_size>0 un hilo escribe en segundo plano: si el disco no da abasto y la cola se
    llena, el par se descarta, se cuenta y write() devuelve False. Nunca se bloquea la
    captura en silencio ni se mezclan pares.
    """

    def __init__(
        self,
        folder: str | Path,
        *,
        image_format: ImageFormat | None = None,
        queue_size: int = 0,
        info: dict[str, Any] | None = None,
        encode: Callable[[np.ndarray], bytes] | None = None,
    ) -> None:
        self.folder = Path(folder)
        if self.folder.exists() and any(self.folder.iterdir()):
            raise InvalidInput(f"{self.folder} ya existe y no está vacía: no se sobrescribe")
        self.image_format = image_format or ImageFormat()
        self._encode = encode or self.image_format.encode
        self.info = dict(info or {})  # se puede completar antes de close()
        (self.folder / FRAMES_DIR).mkdir(parents=True, exist_ok=True)
        self._index = open(self.folder / INDEX, "a", encoding="utf-8", newline="\n")  # noqa: SIM115
        self._first: StereoFrame | None = None
        self._last_id = -1
        self._received: list[int] = []  # tiempos de los pares guardados
        self.dropped: list[int] = []  # frame_id descartados por cola llena
        self._created = datetime.now().astimezone().isoformat(timespec="seconds")
        self._closed = False
        self._error: BaseException | None = None
        self._queue: queue.Queue | None = None
        self._thread: threading.Thread | None = None
        if queue_size < 0:
            raise InvalidInput("queue_size no puede ser negativo")
        if queue_size > 0:
            self._queue = queue.Queue(maxsize=queue_size)
            self._thread = threading.Thread(target=self._writer, name="visionx-recorder")
            self._thread.start()
        self._write_manifest("grabando")

    @property
    def stored(self) -> int:
        """Pares ya escritos en disco."""
        return len(self._received)

    # --- Escritura ----------------------------------------------------------------------

    def write(self, frame: StereoFrame) -> bool:
        """Encola o escribe un par. Devuelve False si se descartó por cola llena."""
        if self._closed:
            raise InvalidInput("la grabación ya está cerrada")
        if self._error is not None:
            raise self._error
        self._check_frame(frame)
        if self._queue is None:
            self._store(frame)
            return True
        try:
            self._queue.put_nowait(frame)
        except queue.Full:
            self.dropped.append(frame.frame_id)
            return False
        return True

    def _check_frame(self, frame: StereoFrame) -> None:
        if not isinstance(frame, StereoFrame):
            raise InvalidInput(f"se esperaba StereoFrame, llegó {type(frame).__name__}")
        first = self._first
        if first is None:
            self._first = frame
        else:
            if frame.session_id != first.session_id:
                raise IdentityMismatch(
                    f"sesión {frame.session_id!r} en una grabación de {first.session_id!r}"
                )
            same = (
                frame.size == first.size
                and frame.source_id == first.source_id
                and frame.rectified == first.rectified
                and frame.calibration_id == first.calibration_id
                and frame.geometry_id == first.geometry_id
            )
            if not same:
                raise IdentityMismatch(
                    f"frame {frame.frame_id}: tamaño, fuente o geometría distinta del primero"
                )
        if frame.frame_id <= self._last_id:
            raise InvalidInput(f"frame_id {frame.frame_id} no avanza (último {self._last_id})")
        self._last_id = frame.frame_id

    def _writer(self) -> None:
        assert self._queue is not None
        while True:
            item = self._queue.get()
            if item is _STOP:
                return
            if self._error is None:
                try:
                    self._store(item)
                except BaseException as exc:  # se relanza en write()/close()
                    self._error = exc

    def _store(self, frame: StereoFrame) -> None:
        stem = f"{frame.frame_id:06d}"
        entry: dict[str, Any] = {
            "frame_id": frame.frame_id,
            "received_ns": frame.received_ns,
            "capture_ns": frame.capture_ns,
            "capture_clock": frame.capture_clock.value,
        }
        for eye, image in (("L", frame.left), ("R", frame.right)):
            data = self._encode(image)
            relative = f"{FRAMES_DIR}/{stem}_{eye}.{self.image_format.ext}"
            _write_atomic(self.folder / relative, data)
            key = "left" if eye == "L" else "right"
            entry[key] = relative
            entry[f"sha256_{key}"] = sha256_bytes(data)
        # La línea va después de los dos archivos: es la que hace "existir" al par.
        self._index.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._index.flush()
        self._received.append(frame.received_ns)

    # --- Cierre -------------------------------------------------------------------------

    def close(self) -> dict[str, Any]:
        """Termina de escribir, cierra el índice y deja el manifiesto en estado 'cerrada'."""
        if self._closed:
            return self._read_manifest()
        self._closed = True
        if self._thread is not None:
            assert self._queue is not None
            self._queue.put(_STOP)
            self._thread.join()
        self._index.close()
        manifest = self._write_manifest("cerrada" if self._error is None else "con_error")
        if self._error is not None:
            raise self._error
        return manifest

    def __enter__(self) -> Recorder:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _manifest(self, state: str) -> dict[str, Any]:
        first = self._first
        return {
            "formato": FORMAT,
            "version": VERSION,
            "schema_contratos": SCHEMA_VERSION,
            "estado": state,  # grabando | cerrada | con_error
            "creado": self._created,
            "session_id": None if first is None else first.session_id,
            "source_id": None if first is None else first.source_id,
            "ojo": None if first is None else list(first.size),
            "rectificado": None if first is None else first.rectified,
            "calibration_id": None if first is None else first.calibration_id,
            "geometry_id": None if first is None else first.geometry_id,
            "imagen": self.image_format.describe(),
            "equipo": _equipo(),
            "pares": self.stored,
            "descartados": {"cantidad": len(self.dropped), "frame_ids": list(self.dropped)},
            "tiempos": timing_summary(self._received),
            "info": self.info,
        }

    def _write_manifest(self, state: str) -> dict[str, Any]:
        manifest = self._manifest(state)
        text = yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False)
        _write_atomic(self.folder / MANIFEST, text.encode("utf-8"))
        return manifest

    def _read_manifest(self) -> dict[str, Any]:
        return yaml.safe_load((self.folder / MANIFEST).read_text(encoding="utf-8"))
