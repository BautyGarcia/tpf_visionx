"""Contratos entre módulos (especificación: docs/CONTRATOS.md).

Cada módulo produce y consume solo estos mensajes, y cada mensaje se valida al crearse: un dato
mal formado da un error, nunca una medición silenciosa. Si un campo cambia de significado, se
sube SCHEMA_VERSION.

Convenciones:
- Identidad de un frame: (session_id, frame_id). Las predicciones conservan esa identidad.
- Imágenes BGR uint8 H x W x 3 (el orden de OpenCV). La conversión a RGB la hace quien prepara
  la red, no el contrato.
- Disparidad float32 en píxeles de la resolución de cómputo; profundidad float32 en metros;
  máscaras bool. Z y d+doffs positivas dentro de máscara; afuera puede haber NaN.
- Tiempos en nanosegundos de un reloj monotónico (ver clock.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from visionx.shared.geometry import StereoGeometry

import numpy as np

from visionx.shared import _validate as v
from visionx.shared.clock import now_ns
from visionx.shared.errors import Expired, IdentityMismatch, InvalidInput, SchemaMismatch

# Schema 3 añade referencia geométrica a Detection y admite d <= 0 si d+doffs > 0.
# Los mensajes de schema 2 deben reconstruirse explícitamente; ver docs/CONTRATOS.md.
SCHEMA_VERSION = 3

__all__ = [
    "SCHEMA_VERSION",
    "AudioEvent",
    "CaptureClock",
    "Command",
    "DepthResult",
    "DepthStatus",
    "Detection",
    "DistancePolicy",
    "FrameKey",
    "Mode",
    "Priority",
    "SpatialObject",
    "StereoFrame",
    "UncertaintyKind",
    "check_geometry",
    "check_detection_frame",
    "check_depth_geometry",
    "check_not_expired",
    "check_same_frame",
    "check_schema",
    "now_ns",
]


def _check_schema_field(obj: object) -> None:
    schema = getattr(obj, "schema", None)
    if type(schema) is not int or schema != SCHEMA_VERSION:
        raise SchemaMismatch(
            f"{type(obj).__name__}: esquema {schema}, este código usa {SCHEMA_VERSION}"
        )


@dataclass(frozen=True, slots=True)
class FrameKey:
    """Identidad de un frame: la sesión (grabación o corrida en vivo) y el número de frame."""

    session_id: str
    frame_id: int

    def __post_init__(self) -> None:
        v.text("session_id", self.session_id)
        v.non_negative_int("frame_id", self.frame_id)


class CaptureClock(StrEnum):
    """De dónde sale capture_ns."""

    NONE = "none"  # no hay hora de captura; solo received_ns
    DEVICE = "device"  # la puso la cámara o el driver
    ESTIMATED = "estimated"  # la estimó el backend (por ejemplo, recepción menos latencia)


@dataclass(frozen=True, slots=True)
class StereoFrame:
    """Un par de imágenes capturadas al mismo tiempo.

    received_ns es el reloj de quien consume: en vivo, el monotónico local al recibir; en replay,
    el reloj de la reproducción. replay_original_ns guarda el received_ns de la grabación.
    """

    session_id: str
    frame_id: int
    left: np.ndarray  # H x W x 3, BGR uint8
    right: np.ndarray  # H x W x 3, BGR uint8
    received_ns: int
    capture_ns: int | None = None
    capture_clock: CaptureClock = CaptureClock.NONE
    replay_original_ns: int | None = None
    rectified: bool = False
    calibration_id: str | None = None
    geometry_id: str | None = None
    source_id: str = "elp"
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_schema_field(self)
        FrameKey(self.session_id, self.frame_id)
        v.array("left", self.left, np.uint8, 3, (None, None, 3))
        v.array("right", self.right, np.uint8, 3, (None, None, 3))
        if self.left.shape != self.right.shape:
            raise InvalidInput(f"ojos de distinto tamaño: {self.left.shape} vs {self.right.shape}")
        if self.left.shape[0] == 0 or self.left.shape[1] == 0:
            raise InvalidInput("imagen vacía")
        v.non_negative_int("received_ns", self.received_ns)
        if not isinstance(self.capture_clock, CaptureClock):
            raise InvalidInput("capture_clock inválido")
        if type(self.rectified) is not bool:
            raise InvalidInput("rectified debe ser bool")
        for name in ("calibration_id", "geometry_id"):
            if getattr(self, name) is not None:
                v.text(name, getattr(self, name))
        if (self.capture_ns is None) != (self.capture_clock is CaptureClock.NONE):
            raise InvalidInput("capture_ns y capture_clock tienen que venir juntos")
        if self.capture_ns is not None:
            v.non_negative_int("capture_ns", self.capture_ns)
        if self.replay_original_ns is not None:
            v.non_negative_int("replay_original_ns", self.replay_original_ns)
        if self.rectified and (self.calibration_id is None or self.geometry_id is None):
            raise InvalidInput("un par rectificado necesita calibration_id y geometry_id")
        v.text("source_id", self.source_id)
        # Cada mensaje conserva su propio contenido aunque la cámara reutilice su buffer.
        # object.__setattr__ solo se usa al construir una dataclass frozen.
        for name in ("left", "right"):
            image = getattr(self, name)
            object.__setattr__(self, name, v.snapshot(image))

    @property
    def key(self) -> FrameKey:
        return FrameKey(self.session_id, self.frame_id)

    @property
    def size(self) -> tuple[int, int]:
        """(ancho, alto) de cada ojo."""
        h, w = self.left.shape[:2]
        return w, h

    @property
    def is_replay(self) -> bool:
        return self.replay_original_ns is not None


class UncertaintyKind(StrEnum):
    NONE = "none"
    LAPLACE_B = "laplace_b"  # b de Laplace, en píxeles de disparidad; > 0
    LR_CONSISTENCY = "lr_consistency"  # |d_izq - d_der| en píxeles; >= 0. No es b.


class DepthStatus(StrEnum):
    VALID = "valid"  # hay medición en la zona útil
    PARTIAL = "partial"  # hay medición, pero con huecos o un fallback declarado en reason
    UNMEASURABLE = "unmeasurable"  # ningún píxel válido; reason dice por qué


@dataclass(frozen=True, slots=True)
class DepthResult:
    """Salida de cualquier método de profundidad (SGBM, Depth Anything, B4, Fusion, Lite...).

    geometry_id identifica la resolución y la cámara en la que está expresada la disparidad.
    """

    session_id: str
    frame_id: int
    model_id: str
    geometry_id: str
    disparity_px: np.ndarray  # H x W float32
    valid_mask: np.ndarray  # H x W bool
    status: DepthStatus
    inference_ms: float
    reason: str | None = None
    depth_m: np.ndarray | None = None  # H x W float32
    uncertainty: np.ndarray | None = None  # H x W float32
    uncertainty_kind: UncertaintyKind = UncertaintyKind.NONE
    alignment_quality: float | None = None
    # Offset entre centros ópticos; debe salir de la geometría usada por el estimador.
    doffs: float = field(default=0.0, kw_only=True)
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_schema_field(self)
        FrameKey(self.session_id, self.frame_id)
        v.text("model_id", self.model_id)
        v.text("geometry_id", self.geometry_id)
        d = v.array("disparity_px", self.disparity_px, np.float32, 2)
        mask = v.array("valid_mask", self.valid_mask, np.bool_, 2, d.shape)
        v.finite("doffs", self.doffs)
        # La magnitud física es d+doffs. Rechazar d negativa descartaría puntos válidos
        # de cámaras cuyos centros ópticos rectificados no están alineados.
        effective = d[mask].astype(np.float64) + self.doffs
        if not np.isfinite(effective).all() or np.any(effective <= 0):
            raise InvalidInput("disparidad efectiva d+doffs debe ser finita y positiva")
        if 0 in d.shape:
            raise InvalidInput("mapa de profundidad vacío")
        v.finite("inference_ms", self.inference_ms, low=0.0)

        if not isinstance(self.status, DepthStatus):
            raise InvalidInput(f"status inválido: {self.status!r}")
        has_valid = bool(mask.any())
        if has_valid and self.status is DepthStatus.UNMEASURABLE:
            raise InvalidInput("status unmeasurable pero la máscara tiene píxeles válidos")
        if not has_valid and self.status is not DepthStatus.UNMEASURABLE:
            raise InvalidInput("máscara vacía: el status tiene que ser unmeasurable")
        if self.status is not DepthStatus.VALID:
            v.text("reason", self.reason)

        if self.depth_m is not None:
            z = v.array("depth_m", self.depth_m, np.float32, 2, d.shape)
            v.finite_positive_inside("depth_m", z, mask)

        if not isinstance(self.uncertainty_kind, UncertaintyKind):
            raise InvalidInput("uncertainty_kind inválido")
        if (self.uncertainty is None) != (self.uncertainty_kind is UncertaintyKind.NONE):
            raise InvalidInput("uncertainty y uncertainty_kind tienen que venir juntos")
        if self.uncertainty is not None:
            u = v.array("uncertainty", self.uncertainty, np.float32, 2, d.shape)
            inside = u[mask]
            if not np.all(np.isfinite(inside)):
                raise InvalidInput("uncertainty: hay NaN o infinitos dentro de la máscara")
            if self.uncertainty_kind is UncertaintyKind.LAPLACE_B and np.any(inside <= 0):
                raise InvalidInput("b de Laplace tiene que ser > 0 dentro de la máscara")
            if np.any(inside < 0):
                raise InvalidInput("uncertainty no puede ser negativa")

        if self.alignment_quality is not None:
            v.finite("alignment_quality", self.alignment_quality)
        for name in ("disparity_px", "valid_mask", "depth_m", "uncertainty"):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, v.snapshot(getattr(self, name)))

    @property
    def key(self) -> FrameKey:
        return FrameKey(self.session_id, self.frame_id)

    @property
    def size(self) -> tuple[int, int]:
        h, w = self.disparity_px.shape
        return w, h


@dataclass(frozen=True, slots=True)
class Detection:
    """Objetos detectados en un frame. Cero objetos es un resultado válido.

    Las cajas y máscaras están en la imagen de referencia de tamaño image_size (izquierda
    rectificada a 1080p en la aplicación). Si el modelo falla, el detector lanza
    EstimatorError en vez de devolver una detección vacía.
    """

    session_id: str
    frame_id: int
    model_id: str
    # Mismo tamaño no significa misma imagen: identificar rectificación/recorte y sesión
    # de calibración permite rechazar una máscara aplicada sobre coordenadas ajenas.
    geometry_id: str = field(kw_only=True)
    calibration_id: str | None = field(default=None, kw_only=True)
    image_size: tuple[int, int]  # (ancho, alto) de la imagen de referencia
    boxes: np.ndarray  # N x 4 float32, xyxy en píxeles
    classes: tuple[str, ...]
    scores: np.ndarray  # N float32, en [0, 1]
    inference_ms: float
    track_ids: tuple[int | None, ...] | None = None
    masks: np.ndarray | None = None  # N x H x W bool
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_schema_field(self)
        FrameKey(self.session_id, self.frame_id)
        v.text("model_id", self.model_id)
        v.text("geometry_id", self.geometry_id)
        if self.calibration_id is not None:
            v.text("calibration_id", self.calibration_id)
        if (
            not isinstance(self.image_size, tuple)
            or len(self.image_size) != 2
            or any(isinstance(s, bool) or not isinstance(s, int) or s <= 0 for s in self.image_size)
        ):
            raise InvalidInput(f"image_size tiene que ser (ancho, alto) > 0: {self.image_size!r}")
        if not isinstance(self.classes, tuple):
            raise InvalidInput("classes tiene que ser una tupla")
        n = len(self.classes)
        for c in self.classes:
            v.text("classes[]", c)
        boxes = v.array("boxes", self.boxes, np.float32, 2, (n, 4))
        scores = v.array("scores", self.scores, np.float32, 1, (n,))
        if not np.all(np.isfinite(boxes)):
            raise InvalidInput("boxes: hay NaN o infinitos")
        if np.any(boxes[:, 2] < boxes[:, 0]) or np.any(boxes[:, 3] < boxes[:, 1]):
            raise InvalidInput("boxes: se esperaba xyxy con x2 >= x1 y y2 >= y1")
        if not (np.all(np.isfinite(scores)) and np.all((scores >= 0) & (scores <= 1))):
            raise InvalidInput("scores tienen que estar en [0, 1]")
        v.finite("inference_ms", self.inference_ms, low=0.0)
        if self.track_ids is not None:
            if not isinstance(self.track_ids, tuple) or len(self.track_ids) != n:
                raise InvalidInput("track_ids tiene que ser una tupla con un id por objeto")
            for t in self.track_ids:
                if t is not None:
                    v.non_negative_int("track_ids[]", t)
        if self.masks is not None:
            w, h = self.image_size
            v.array("masks", self.masks, np.bool_, 3, (n, h, w))
        for name in ("boxes", "scores", "masks"):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, v.snapshot(getattr(self, name)))

    @property
    def key(self) -> FrameKey:
        return FrameKey(self.session_id, self.frame_id)

    def __len__(self) -> int:
        return len(self.classes)


class DistancePolicy(StrEnum):
    """Qué decide decir el criterio de confianza."""

    SPEAK_METERS = "speak_meters"
    DIRECTION_ONLY = "direction_only"
    ASK_REFRAME = "ask_reframe"
    ABSTAIN = "abstain"


@dataclass(frozen=True, slots=True)
class SpatialObject:
    """Un objeto ubicado en el espacio, listo para que el controlador lo comunique.

    z_m es la distancia axial (a lo largo del eje óptico) de la superficie visible típica del
    objeto; None si no se pudo medir. detector_score y la calidad de la profundidad
    (valid_fraction, z_spread_m) se informan por separado: no se combinan en una probabilidad.
    """

    session_id: str
    frame_id: int
    detection_index: int  # posición del objeto en la Detection de origen
    track_id: int | None
    label: str
    depth_model_id: str
    angle_h_deg: float  # positivo a la derecha
    angle_v_deg: float  # positivo hacia arriba
    z_m: float | None
    z_spread_m: float | None  # dispersión robusta de Z dentro de la máscara
    valid_fraction: float  # fracción de la máscara con profundidad válida, en [0, 1]
    detector_score: float  # en [0, 1]
    policy: DistancePolicy
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_schema_field(self)
        FrameKey(self.session_id, self.frame_id)
        v.non_negative_int("detection_index", self.detection_index)
        if self.track_id is not None:
            v.non_negative_int("track_id", self.track_id)
        v.text("label", self.label)
        v.text("depth_model_id", self.depth_model_id)
        v.finite("angle_h_deg", self.angle_h_deg, -90.0, 90.0)
        v.finite("angle_v_deg", self.angle_v_deg, -90.0, 90.0)
        if self.z_m is not None:
            if v.finite("z_m", self.z_m) <= 0:
                raise InvalidInput(f"z_m tiene que ser > 0 o None, llegó {self.z_m}")
        if self.z_spread_m is not None:
            v.finite("z_spread_m", self.z_spread_m, low=0.0)
        v.finite("valid_fraction", self.valid_fraction, 0.0, 1.0)
        v.finite("detector_score", self.detector_score, 0.0, 1.0)
        if not isinstance(self.policy, DistancePolicy):
            raise InvalidInput(f"policy inválida: {self.policy!r}")
        if self.policy is DistancePolicy.SPEAK_METERS and self.z_m is None:
            raise InvalidInput("no se pueden decir metros sin z_m")

    @property
    def key(self) -> FrameKey:
        return FrameKey(self.session_id, self.frame_id)


class Mode(StrEnum):
    IDLE = "idle"
    SEARCH = "search"
    CHOOSE = "choose"
    GUIDE = "guide"
    DISTANCE = "distance"
    DESCRIBE = "describe"
    READ = "read"
    CONTROL = "control"


@dataclass(frozen=True, slots=True)
class Command:
    """Una orden ya interpretada. Un request_id nuevo invalida los resultados de los anteriores.

    frame es el frame consultado cuando la orden lo congela (por ejemplo, Distancia).
    """

    request_id: int
    mode: Mode
    utterance: str
    issued_ns: int
    target: str | None = None
    deadline_ns: int | None = None
    frame: FrameKey | None = None
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_schema_field(self)
        v.non_negative_int("request_id", self.request_id)
        if not isinstance(self.mode, Mode):
            raise InvalidInput(f"mode inválido: {self.mode!r}")
        if not isinstance(self.utterance, str):
            raise InvalidInput("utterance tiene que ser texto")
        v.non_negative_int("issued_ns", self.issued_ns)
        if self.target is not None:
            v.text("target", self.target)
        _check_deadline(self.issued_ns, self.deadline_ns)
        if self.frame is not None and not isinstance(self.frame, FrameKey):
            raise InvalidInput("frame tiene que ser un FrameKey")


class Priority(IntEnum):
    """Mayor número, mayor prioridad: lo de más prioridad corta a lo de menos."""

    LONG = 0  # descripciones y lecturas
    SHORT = 1  # respuestas cortas
    SEARCH = 2  # sonidos de búsqueda
    ALERT = 3  # alerta de cercanía


@dataclass(frozen=True, slots=True)
class AudioEvent:
    """Algo para decir o hacer sonar. Si pasó deadline_ns, ya no se reproduce."""

    request_id: int
    priority: Priority
    text_or_sound: str
    created_ns: int
    deadline_ns: int | None = None
    cancelable: bool = True
    frame: FrameKey | None = None  # frame que originó el evento, si hay uno
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_schema_field(self)
        v.non_negative_int("request_id", self.request_id)
        if not isinstance(self.priority, Priority):
            raise InvalidInput(f"priority inválida: {self.priority!r}")
        v.text("text_or_sound", self.text_or_sound)
        v.non_negative_int("created_ns", self.created_ns)
        if type(self.cancelable) is not bool:
            raise InvalidInput("cancelable debe ser bool")
        _check_deadline(self.created_ns, self.deadline_ns)
        if self.frame is not None and not isinstance(self.frame, FrameKey):
            raise InvalidInput("frame tiene que ser un FrameKey")


def _check_deadline(start_ns: int, deadline_ns: int | None) -> None:
    if deadline_ns is not None:
        v.non_negative_int("deadline_ns", deadline_ns)
        if deadline_ns < start_ns:
            raise InvalidInput("deadline_ns es anterior a la creación")


# --- Chequeos para quien recibe mensajes -------------------------------------------------


def check_schema(msg: object) -> None:
    """Lanza SchemaMismatch si msg no es de la versión de esquema de este código."""
    _check_schema_field(msg)


def check_same_frame(*msgs: object) -> FrameKey:
    """Verifica que todos los mensajes sean del mismo frame de la misma sesión.

    Acepta mensajes con .key o FrameKey sueltos. Devuelve la identidad común.
    """
    if not msgs:
        raise ValueError("check_same_frame necesita al menos un mensaje")
    for msg in msgs:
        if not isinstance(msg, FrameKey):
            check_schema(msg)
    keys = [m if isinstance(m, FrameKey) else m.key for m in msgs]  # type: ignore[attr-defined]
    if any(k != keys[0] for k in keys[1:]):
        raise IdentityMismatch(f"frames distintos: {[(k.session_id, k.frame_id) for k in keys]}")
    return keys[0]


def check_geometry(msg: object, geometry_id: str) -> None:
    """Verifica que msg esté expresado en la geometría esperada."""
    check_schema(msg)
    v.text("geometry_id esperado", geometry_id)
    got = getattr(msg, "geometry_id", None)
    if got != geometry_id:
        raise IdentityMismatch(f"geometría {got!r}, se esperaba {geometry_id!r}")


def check_not_expired(msg: Command | AudioEvent, now: int) -> None:
    """Lanza Expired si msg tiene deadline y now ya lo pasó. now viene del Clock en uso."""
    check_schema(msg)
    v.non_negative_int("now", now)
    if msg.deadline_ns is not None and now > msg.deadline_ns:
        raise Expired(
            f"request {msg.request_id} vencido hace {(now - msg.deadline_ns) / 1e6:.1f} ms"
        )


def check_detection_frame(frame: StereoFrame, detections: Detection) -> None:
    """Valida detecciones ya expresadas en la imagen de referencia.

    Llamar antes de usar cajas/máscaras sobre ese frame. No hace resize ni rectifica:
    transformar datos exige un paso explícito que actualice geometry_id e image_size.
    """
    check_same_frame(frame, detections)
    if frame.geometry_id is None:
        raise IdentityMismatch("el frame necesita referencia geométrica para combinar detecciones")
    check_geometry(detections, frame.geometry_id)
    if detections.calibration_id != frame.calibration_id:
        raise IdentityMismatch("detecciones y frame tienen calibraciones distintas")
    if detections.image_size != frame.size:
        raise IdentityMismatch("detecciones y frame tienen tamaños distintos")


def check_depth_geometry(depth: DepthResult, geometry: StereoGeometry) -> None:
    """Comprueba contexto de cómputo; no asume misma resolución que el detector.

    Llamar al recibir profundidad, antes de convertirla a metros o agregar por objeto.
    Si el productor entrega también depth_m, verificar que no contradiga su disparidad.
    """
    check_schema(depth)
    check_geometry(depth, geometry.geometry_id)
    if depth.size != geometry.size or depth.doffs != geometry.doffs:
        raise IdentityMismatch("depth y geometría discrepan en tamaño o doffs")
    if depth.depth_m is not None:
        expected, valid = geometry.disparity_to_depth(depth.disparity_px, depth.valid_mask)
        if not np.array_equal(valid, depth.valid_mask) or not np.allclose(
            depth.depth_m[valid], expected[valid], rtol=1e-5, atol=1e-6
        ):
            raise IdentityMismatch("depth_m no corresponde a disparity_px y su geometría")
