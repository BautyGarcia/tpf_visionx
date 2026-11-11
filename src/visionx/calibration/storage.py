"""Calibración guardada: archivo YAML legible, rectificación y geometría compartida.

El archivo guarda todo lo necesario para rectificar y para pasar de disparidad a metros,
más de dónde salió: tablero, modelo, fotos (hash), métricas y versión de OpenCV.
Las distancias van en **metros** (T, baseline). La herramienta de la cátedra guarda
milímetros: `from_i308_pickle` convierte.

`calibration_id` se calcula del contenido numérico. Si algo cambia, cambia el id: un
frame rectificado con una calibración no se puede mezclar con otra sin que se note.
"""

from __future__ import annotations

import hashlib
import math
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from visionx.calibration import models as m
from visionx.calibration.models import Intrinsics, LensModel, Rectification
from visionx.shared.errors import InvalidInput
from visionx.shared.geometry import StereoGeometry

FORMAT = "visionx-calibracion-estereo"
FORMAT_VERSION = 1


@dataclass(frozen=True)
class StereoCalibration:
    image_size: tuple[int, int]  # (ancho, alto) de cada ojo, en la foto original
    model: LensModel
    left: Intrinsics
    right: Intrinsics
    R: np.ndarray  # rotación ojo izquierdo -> ojo derecho
    T: np.ndarray  # traslación izquierdo -> derecho, en metros (T_x ~ -baseline)
    rect: Rectification
    alpha: float
    info: dict[str, Any] = field(default_factory=dict)  # tablero, métricas, fotos, versión
    calibration_id: str = field(init=False)

    def __post_init__(self) -> None:
        w, h = self.image_size
        if w <= 0 or h <= 0:
            raise InvalidInput("image_size tiene que ser positivo")
        for name, value in self._arrays().items():
            if not np.isfinite(value).all():
                raise InvalidInput(f"{name} tiene valores no finitos")
        if self.T.ravel()[0] >= 0:
            raise InvalidInput("T_x tiene que ser negativo: el ojo derecho está a la derecha")
        object.__setattr__(self, "calibration_id", self._make_id())

    def _arrays(self) -> dict[str, np.ndarray]:
        return {
            "K1": self.left.K, "D1": self.left.D, "K2": self.right.K, "D2": self.right.D,
            "R": self.R, "T": self.T, "R1": self.rect.R1, "R2": self.rect.R2,
            "P1": self.rect.P1, "P2": self.rect.P2, "Q": self.rect.Q,
        }  # fmt: skip

    def _make_id(self) -> str:
        digest = hashlib.sha256()
        digest.update(f"{self.model.value}|{self.image_size}|{self.alpha!r}".encode())
        for name, value in self._arrays().items():
            digest.update(name.encode())
            digest.update(np.ascontiguousarray(value, np.float64).tobytes())
        w, h = self.image_size
        return f"elp-{w}x{h}-{self.model.value}-{digest.hexdigest()[:10]}"

    # --- Uso -----------------------------------------------------------------------------

    @property
    def baseline_m(self) -> float:
        return float(np.linalg.norm(self.T))

    def geometry(self) -> StereoGeometry:
        """Geometría del par rectificado, a la resolución de la foto original."""
        w, h = self.image_size
        return StereoGeometry.from_projections(self.rect.P1, self.rect.P2, w, h)

    def rectify_maps(self) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]:
        """Mapas de cv2.remap para (izquierdo, derecho). Calcularlos una vez y reutilizar."""
        left = m.init_maps(self.model, self.left, self.rect.R1, self.rect.P1, self.image_size)
        right = m.init_maps(self.model, self.right, self.rect.R2, self.rect.P2, self.image_size)
        return left, right

    def rectify(
        self, left: np.ndarray, right: np.ndarray, maps: tuple | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Rectifica un par. Después, el mismo punto cae en la misma fila en los dos ojos."""
        w, h = self.image_size
        for name, image in (("left", left), ("right", right)):
            if image.shape[1] != w or image.shape[0] != h:
                raise InvalidInput(
                    f"{name} mide {image.shape[1]}x{image.shape[0]}, la calibración es {w}x{h}"
                )
        (l1, l2), (r1, r2) = maps or self.rectify_maps()
        return (
            cv2.remap(left, l1, l2, cv2.INTER_LINEAR),
            cv2.remap(right, r1, r2, cv2.INTER_LINEAR),
        )

    # --- Archivo -------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        def mat(a: np.ndarray) -> list:
            # float de Python con repr exacto: el YAML conserva el valor sin redondear.
            return np.asarray(a, np.float64).tolist()

        return {
            "formato": FORMAT,
            "version": FORMAT_VERSION,
            "calibration_id": self.calibration_id,
            "modelo": self.model.value,
            "tamaño_imagen": list(self.image_size),
            "unidades": "K/P en píxeles; T y baseline en metros",
            "baseline_m": self.baseline_m,
            "alpha": self.alpha,
            "izquierda": {"K": mat(self.left.K), "D": mat(self.left.D.ravel())},
            "derecha": {"K": mat(self.right.K), "D": mat(self.right.D.ravel())},
            "R": mat(self.R),
            "T": mat(self.T.ravel()),
            "rectificacion": {
                "R1": mat(self.rect.R1),
                "R2": mat(self.rect.R2),
                "P1": mat(self.rect.P1),
                "P2": mat(self.rect.P2),
                "Q": mat(self.rect.Q),
                "roi_izquierda": list(self.rect.roi1),
                "roi_derecha": list(self.rect.roi2),
            },
            "info": self.info,
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(self.to_dict(), allow_unicode=True, sort_keys=False, width=100)
        path.write_text(text, encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> StereoCalibration:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("formato") != FORMAT:
            raise InvalidInput(f"{path}: no es un archivo de calibración VisionX")
        if data.get("version") != FORMAT_VERSION:
            raise InvalidInput(f"{path}: versión {data.get('version')} no soportada")
        rect = data["rectificacion"]
        arr = lambda v: np.asarray(v, np.float64)  # noqa: E731
        calib = cls(
            image_size=tuple(int(x) for x in data["tamaño_imagen"]),
            model=LensModel(data["modelo"]),
            left=Intrinsics(
                arr(data["izquierda"]["K"]), arr(data["izquierda"]["D"]).reshape(-1, 1)
            ),
            right=Intrinsics(arr(data["derecha"]["K"]), arr(data["derecha"]["D"]).reshape(-1, 1)),
            R=arr(data["R"]),
            T=arr(data["T"]).reshape(3, 1),
            rect=Rectification(
                arr(rect["R1"]),
                arr(rect["R2"]),
                arr(rect["P1"]),
                arr(rect["P2"]),
                arr(rect["Q"]),
                tuple(rect["roi_izquierda"]),
                tuple(rect["roi_derecha"]),
            ),  # fmt: skip
            alpha=float(data["alpha"]),
            info=data.get("info") or {},
        )
        if calib.calibration_id != data.get("calibration_id"):
            raise InvalidInput(f"{path}: el contenido no coincide con su calibration_id")
        return calib


def from_parameters(
    model: LensModel,
    image_size: tuple[int, int],
    left: Intrinsics,
    right: Intrinsics,
    R: np.ndarray,
    T_m: np.ndarray,
    alpha: float = 0.0,
    info: dict[str, Any] | None = None,
) -> StereoCalibration:
    """Arma la calibración rectificando a partir de intrínsecos y extrínsecos (T en metros)."""
    T_m = np.asarray(T_m, np.float64).reshape(3, 1)
    rect = m.rectify(model, left, right, image_size, np.asarray(R, np.float64), T_m, alpha)
    return StereoCalibration(image_size, model, left, right, R, T_m, rect, alpha, info or {})


def from_i308_pickle(path: str | Path, alpha: float = 0.0) -> StereoCalibration:
    """Importa `stereo_calibration.pkl` de la herramienta de la cátedra (T en mm).

    Usa pickle: abrir solo archivos generados por nosotros, nunca uno descargado.
    """
    with Path(path).open("rb") as f:
        data = pickle.load(f)  # noqa: S301 - archivo propio de la herramienta i308-calib
    try:
        size = tuple(int(x) for x in data["image_size"])
        left = Intrinsics(np.asarray(data["left_K"], float), np.asarray(data["left_dist"], float))
        right = Intrinsics(
            np.asarray(data["right_K"], float), np.asarray(data["right_dist"], float)
        )
        R = np.asarray(data["R"], float)
        T_m = np.asarray(data["T"], float).reshape(3, 1) / 1000.0  # mm -> m
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidInput(f"{path}: no tiene el formato de i308-calib") from exc
    left = Intrinsics(left.K, left.D.reshape(-1, 1))
    right = Intrinsics(right.K, right.D.reshape(-1, 1))
    info = {"origen": "i308-calib", "archivo": Path(path).name}
    return from_parameters(LensModel.PINHOLE5, size, left, right, R, T_m, alpha, info)


def nan_to_none(value: Any) -> Any:
    """YAML/JSON sin NaN: reemplaza por None para que el archivo sea portable."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: nan_to_none(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [nan_to_none(v) for v in value]
    return value
