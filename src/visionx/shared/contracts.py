"""Contratos entre módulos.

Cada módulo produce y consume solo estos mensajes. Así cada parte se puede probar con datos
simulados o grabados sin esperar a las demás. Si un campo cambia de significado, se sube
SCHEMA_VERSION.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum

import numpy as np

SCHEMA_VERSION = 1


def now_ns() -> int:
    """Reloj monotónico común a todos los módulos, en nanosegundos."""
    return time.monotonic_ns()


@dataclass(slots=True)
class StereoFrame:
    """Un par de imágenes capturadas al mismo tiempo."""

    frame_id: int
    capture_ns: int
    left: np.ndarray  # H x W x 3, BGR uint8
    right: np.ndarray  # H x W x 3, BGR uint8
    calibration_id: str | None = None
    rectified: bool = False
    source_id: str = "elp"
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.left.shape != self.right.shape:
            raise ValueError(f"ojos de distinto tamaño: {self.left.shape} vs {self.right.shape}")
        if self.left.ndim != 3 or self.left.shape[2] != 3:
            raise ValueError(f"se esperaba H x W x 3, llegó {self.left.shape}")

    @property
    def size(self) -> tuple[int, int]:
        """(ancho, alto) de cada ojo."""
        h, w = self.left.shape[:2]
        return w, h


class UncertaintyKind(StrEnum):
    NONE = "none"
    LAPLACE_B = "laplace_b"  # b: escala de Laplace, en píxeles de disparidad
    LR_CONSISTENCY = "lr_consistency"


@dataclass(slots=True)
class DepthResult:
    """Salida de cualquier método de profundidad (SGBM, Depth Anything, Fusion, Lite...)."""

    frame_id: int
    model_id: str
    disparity_px: np.ndarray  # H x W float32, en píxeles de la resolución de cómputo
    valid_mask: np.ndarray  # H x W bool
    inference_ms: float
    depth_m: np.ndarray | None = None
    uncertainty: np.ndarray | None = None
    uncertainty_kind: UncertaintyKind = UncertaintyKind.NONE
    alignment_quality: float | None = None
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.disparity_px.shape != self.valid_mask.shape:
            raise ValueError("disparidad y máscara de distinto tamaño")
        if self.uncertainty is not None and self.uncertainty.shape != self.disparity_px.shape:
            raise ValueError("incertidumbre y disparidad de distinto tamaño")
        if (self.uncertainty is None) != (self.uncertainty_kind is UncertaintyKind.NONE):
            raise ValueError("uncertainty y uncertainty_kind tienen que venir juntos")


@dataclass(slots=True)
class Detection:
    """Objetos detectados en un frame."""

    frame_id: int
    boxes: np.ndarray  # N x 4, xyxy en píxeles de la imagen izquierda
    classes: list[str]
    scores: np.ndarray  # N
    track_ids: list[int | None] = field(default_factory=list)
    masks: np.ndarray | None = None  # N x H x W bool
    schema: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        n = len(self.classes)
        if self.boxes.shape != (n, 4) or self.scores.shape != (n,):
            raise ValueError("boxes, classes y scores no coinciden en cantidad")
        if self.track_ids and len(self.track_ids) != n:
            raise ValueError("track_ids no coincide con la cantidad de objetos")


class DistancePolicy(StrEnum):
    """Qué decide decir el criterio de confianza."""

    SPEAK_METERS = "speak_meters"
    DIRECTION_ONLY = "direction_only"
    ASK_REFRAME = "ask_reframe"
    ABSTAIN = "abstain"


@dataclass(slots=True)
class SpatialObject:
    """Un objeto ubicado en el espacio, listo para que el controlador lo comunique."""

    frame_id: int
    track_id: int | None
    label: str
    angle_h_deg: float  # positivo a la derecha
    angle_v_deg: float  # positivo hacia arriba
    z_m: float | None
    confidence: float
    valid_fraction: float
    policy: DistancePolicy
    schema: int = SCHEMA_VERSION


class Mode(StrEnum):
    IDLE = "idle"
    SEARCH = "search"
    CHOOSE = "choose"
    GUIDE = "guide"
    DISTANCE = "distance"
    DESCRIBE = "describe"
    READ = "read"
    CONTROL = "control"


@dataclass(slots=True)
class Command:
    request_id: int
    mode: Mode
    utterance: str
    timestamp_ns: int
    target: str | None = None
    schema: int = SCHEMA_VERSION


class Priority(IntEnum):
    """Mayor número, mayor prioridad: lo de más prioridad corta a lo de menos."""

    LONG = 0  # descripciones y lecturas
    SHORT = 1  # respuestas cortas
    SEARCH = 2  # sonidos de búsqueda
    ALERT = 3  # alerta de cercanía


@dataclass(slots=True)
class AudioEvent:
    request_id: int
    priority: Priority
    text_or_sound: str
    cancelable: bool = True
    originating_frame_id: int | None = None
    deadline_ns: int | None = None
    schema: int = SCHEMA_VERSION
