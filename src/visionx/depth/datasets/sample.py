"""Una muestra de dataset estéreo con su GT, igual para todos los adaptadores.

Cada dataset guarda la disparidad a su manera (PNG x100, PFM con infinitos, máscaras con
128/255...). Los adaptadores traducen todo a esta forma única, así el resto del código
(B0–B4, Fusion, evaluación) no conoce detalles de ningún dataset:

- Imágenes BGR uint8, como entrega OpenCV y como espera StereoFrame.
- Disparidad GT en píxeles, convención d = x_izquierda - x_derecha, float32.
  Donde no hay GT vale NaN y `valid` es False: nunca un 0 que parezca medición.
- `nonoccluded`: subconjunto de `valid` visible en los dos ojos (si el dataset lo publica).
  Las métricas "noc" de los papers usan esta máscara.
- `geometry`: cámara a la resolución de la muestra, solo si el dataset publica calibración.
  InStereo2K no la publica: ahí no se puede pasar a metros y no se inventa.
- `scene_id`: agrupa pares casi iguales. Las particiones reparten escenas, nunca pares
  sueltos, para que validación y test no vean "la misma foto movida un poco".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from visionx.shared import _validate as v
from visionx.shared.errors import InvalidInput
from visionx.shared.geometry import StereoGeometry


@dataclass(frozen=True)
class StereoSample:
    dataset: str
    sample_id: str  # único dentro del dataset, p. ej. "Adirondack" o "train/000123"
    scene_id: str  # unidad de partición
    left: np.ndarray  # H x W x 3 BGR uint8
    right: np.ndarray
    disparity: np.ndarray  # H x W float32, píxeles; NaN fuera de valid
    valid: np.ndarray  # H x W bool
    nonoccluded: np.ndarray | None = None  # H x W bool, subconjunto de valid
    geometry: StereoGeometry | None = None
    grayscale: bool = False  # imagen original en grises, replicada a 3 canales (ETH3D)
    files: tuple[str, ...] = field(default_factory=tuple)  # rutas relativas leídas

    def __post_init__(self) -> None:
        for name in ("dataset", "sample_id", "scene_id"):
            v.text(name, getattr(self, name))
        v.array("left", self.left, np.uint8, 3, (None, None, 3))
        h, w = self.left.shape[:2]
        v.array("right", self.right, np.uint8, 3, (h, w, 3))
        v.array("disparity", self.disparity, np.float32, 2, (h, w))
        v.array("valid", self.valid, np.bool_, 2, (h, w))
        if not np.isfinite(self.disparity[self.valid]).all():
            raise InvalidInput(f"{self.sample_id}: disparidad no finita dentro de valid")
        if not np.isnan(self.disparity[~self.valid]).all():
            raise InvalidInput(f"{self.sample_id}: fuera de valid la disparidad tiene que ser NaN")
        if self.nonoccluded is not None:
            v.array("nonoccluded", self.nonoccluded, np.bool_, 2, (h, w))
            if (self.nonoccluded & ~self.valid).any():
                raise InvalidInput(f"{self.sample_id}: nonoccluded tiene píxeles sin GT")
        if self.geometry is not None:
            if self.geometry.size != (w, h):
                raise InvalidInput(
                    f"{self.sample_id}: geometría {self.geometry.size} e imagen {(w, h)} difieren"
                )
            effective = self.disparity[self.valid].astype(np.float64) + self.geometry.doffs
            if (effective <= 0).any():
                raise InvalidInput(f"{self.sample_id}: d + doffs <= 0 dentro de valid")

    @property
    def size(self) -> tuple[int, int]:
        """(ancho, alto)."""
        h, w = self.left.shape[:2]
        return w, h

    def depth(self) -> tuple[np.ndarray, np.ndarray]:
        """Profundidad GT en metros y su máscara; solo si el dataset publica calibración."""
        if self.geometry is None:
            raise InvalidInput(f"{self.dataset}: sin calibración publicada, no hay metros")
        return self.geometry.disparity_to_depth(self.disparity, self.valid)
