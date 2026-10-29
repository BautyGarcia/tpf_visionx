"""Geometría estéreo compartida: de disparidad a metros, ángulos y cambios de resolución.

Todo cambio de tamaño o recorte pasa por este módulo; nadie reescala a mano.

Convenciones:
- Par rectificado: los dos ojos miran paralelo y una misma fila de la imagen es la misma
  altura en los dos. Disparidad d = x_izquierda - x_derecha, en píxeles, positiva.
- Profundidad Z en metros, a lo largo del eje óptico: Z = fx * B / (d + doffs).
  doffs = cx_derecha - cx_izquierda (0 si la rectificación alinea los centros, como en la ELP;
  distinto de 0 en Middlebury).
- Coordenadas de píxel con el centro del primer píxel en (0, 0), como OpenCV. Al cambiar de
  tamaño se alinean los centros: x' = (x + 0.5) * escala - 0.5.
- Ángulos: horizontal positivo a la derecha, vertical positivo hacia arriba.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from visionx.shared import _validate as v
from visionx.shared.errors import IdentityMismatch, InvalidInput


@dataclass(frozen=True, slots=True)
class StereoGeometry:
    """Cámara estéreo rectificada a una resolución concreta. Inmutable.

    geometry_id se calcula de los parámetros: dos geometrías con los mismos números tienen el
    mismo id, y cualquier cambio (otra resolución, otra calibración) da otro id.
    """

    width: int
    height: int
    fx: float  # focal horizontal, en píxeles
    fy: float  # focal vertical, en píxeles
    cx: float  # centro óptico del ojo izquierdo, en píxeles
    cy: float
    baseline_m: float  # distancia entre los centros de los dos lentes
    doffs: float = 0.0  # cx_derecha - cx_izquierda, en píxeles
    geometry_id: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("width", "height"):
            value = getattr(self, name)
            if v.non_negative_int(name, value) == 0:
                raise InvalidInput(f"{name} tiene que ser > 0")
        if v.finite("fx", self.fx) <= 0 or v.finite("fy", self.fy) <= 0:
            raise InvalidInput("las focales tienen que ser > 0")
        v.finite("cx", self.cx, -0.5, self.width - 0.5)
        v.finite("cy", self.cy, -0.5, self.height - 0.5)
        if v.finite("baseline_m", self.baseline_m) <= 0:
            raise InvalidInput("baseline_m tiene que ser > 0")
        v.finite("doffs", self.doffs)
        object.__setattr__(self, "geometry_id", self._make_id())

    def _make_id(self) -> str:
        # Redondeo a 1e-6 para que el id no dependa del último bit del float.
        nums = (self.fx, self.fy, self.cx, self.cy, self.baseline_m, self.doffs)
        text = ",".join(f"{x:.6f}" for x in nums)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
        return f"{self.width}x{self.height}-{digest}"

    @property
    def size(self) -> tuple[int, int]:
        """(ancho, alto)."""
        return self.width, self.height

    # --- Construcción desde una calibración -----------------------------------------------

    @classmethod
    def from_projections(
        cls, p1: np.ndarray, p2: np.ndarray, width: int, height: int
    ) -> StereoGeometry:
        """Arma la geometría con las matrices P1 y P2 (3 x 4) de cv2.stereoRectify.

        P2[0, 3] = -fx * B, así que B = -P2[0, 3] / P2[0, 0].
        """
        p1 = np.asarray(p1, dtype=np.float64)
        p2 = np.asarray(p2, dtype=np.float64)
        if p1.shape != (3, 4) or p2.shape != (3, 4):
            raise InvalidInput("P1 y P2 tienen que ser matrices 3 x 4")
        fx, fy, cx, cy = p1[0, 0], p1[1, 1], p1[0, 2], p1[1, 2]
        if not math.isclose(p2[0, 0], fx, rel_tol=1e-9) or not math.isclose(p2[1, 2], cy):
            raise InvalidInput("P1 y P2 no son de un mismo par rectificado")
        return cls(
            width=width,
            height=height,
            fx=float(fx),
            fy=float(fy),
            cx=float(cx),
            cy=float(cy),
            baseline_m=float(-p2[0, 3] / p2[0, 0]),
            doffs=float(p2[0, 2] - cx),
        )

    # --- Disparidad <-> profundidad -------------------------------------------------------

    def disparity_to_depth(
        self, disparity_px: np.ndarray, valid: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Disparidad (float32) a profundidad en metros (float32).

        Devuelve (profundidad, máscara válida). Un píxel es válido si ya lo era en `valid`, es
        finito y d + doffs > 0. Fuera de la máscara la profundidad es NaN, nunca 0 ni infinito.
        """
        d = self._map(disparity_px, valid, "disparity_px")
        denom = d.astype(np.float64) + self.doffs
        ok = self._mask(d, valid) & np.isfinite(denom) & (denom > 0)
        z = np.full(d.shape, np.nan, np.float64)
        z[ok] = self.fx * self.baseline_m / denom[ok]
        return z.astype(np.float32), ok

    def depth_to_disparity(
        self, depth_m: np.ndarray, valid: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Profundidad en metros (float32) a disparidad en píxeles (float32).

        Válido si ya lo era, Z es finita y > 0, y la disparidad resultante es > 0.
        """
        z = self._map(depth_m, valid, "depth_m")
        z64 = z.astype(np.float64)
        ok = self._mask(z, valid) & np.isfinite(z64) & (z64 > 0)
        d = np.full(z.shape, np.nan, np.float64)
        d[ok] = self.fx * self.baseline_m / z64[ok] - self.doffs
        ok &= np.nan_to_num(d, nan=-1.0) > 0
        d[~ok] = np.nan
        return d.astype(np.float32), ok

    def depth_at(self, disparity_px: float) -> float | None:
        """Un valor suelto de disparidad a metros; None si no se puede medir."""
        if not math.isfinite(disparity_px) or disparity_px + self.doffs <= 0:
            return None
        return self.fx * self.baseline_m / (disparity_px + self.doffs)

    def disparity_at(self, depth_m: float) -> float | None:
        """Un valor suelto de metros a disparidad; None si no da una disparidad > 0."""
        if not math.isfinite(depth_m) or depth_m <= 0:
            return None
        d = self.fx * self.baseline_m / depth_m - self.doffs
        return d if d > 0 else None

    # --- Ángulos ------------------------------------------------------------------------

    def pixel_to_angles(self, u: float, v_: float) -> tuple[float, float]:
        """Píxel (columna u, fila v) del ojo izquierdo a (ángulo horizontal, vertical) en grados.

        Horizontal positivo a la derecha; vertical positivo hacia arriba (la fila crece hacia
        abajo, por eso el signo menos).
        """
        h = math.degrees(math.atan2(u - self.cx, self.fx))
        vert = -math.degrees(math.atan2(v_ - self.cy, self.fy))
        return h, vert

    # --- Cambios de resolución y recorte --------------------------------------------------

    def resized(self, width: int, height: int) -> StereoGeometry:
        """La misma cámara vista a otra resolución (sin recortar)."""
        if v.non_negative_int("width", width) == 0 or v.non_negative_int("height", height) == 0:
            raise InvalidInput("el tamaño nuevo tiene que ser > 0")
        sx = width / self.width
        sy = height / self.height
        return StereoGeometry(
            width=width,
            height=height,
            fx=self.fx * sx,
            fy=self.fy * sy,
            cx=(self.cx + 0.5) * sx - 0.5,
            cy=(self.cy + 0.5) * sy - 0.5,
            baseline_m=self.baseline_m,
            doffs=self.doffs * sx,
        )

    def cropped(self, x0: int, y0: int, width: int, height: int) -> StereoGeometry:
        """La misma cámara con la imagen recortada (el mismo recorte en los dos ojos).

        La focal y la disparidad no cambian; solo se corre el centro óptico.
        """
        for name, val in (("x0", x0), ("y0", y0), ("width", width), ("height", height)):
            v.non_negative_int(name, val)
        if width == 0 or height == 0 or x0 + width > self.width or y0 + height > self.height:
            raise InvalidInput(
                f"recorte ({x0}, {y0}, {width}, {height}) fuera de {self.width}x{self.height}"
            )
        return StereoGeometry(
            width=width,
            height=height,
            fx=self.fx,
            fy=self.fy,
            cx=self.cx - x0,
            cy=self.cy - y0,
            baseline_m=self.baseline_m,
            doffs=self.doffs,
        )

    def require_size(self, array: np.ndarray, name: str = "array") -> None:
        """Verifica que un mapa H x W (o H x W x C) tenga el tamaño de esta geometría."""
        if array.shape[:2] != (self.height, self.width):
            raise IdentityMismatch(
                f"{name} mide {array.shape[1]}x{array.shape[0]}, la geometría "
                f"{self.geometry_id} es {self.width}x{self.height}"
            )

    # --- Internos -------------------------------------------------------------------------

    def _map(self, values: np.ndarray, valid: np.ndarray | None, name: str) -> np.ndarray:
        arr = v.array(name, values, np.float32, 2)
        self.require_size(arr, name)
        if valid is not None:
            v.array("valid", valid, np.bool_, 2, arr.shape)
        return arr

    @staticmethod
    def _mask(values: np.ndarray, valid: np.ndarray | None) -> np.ndarray:
        return np.ones(values.shape, bool) if valid is None else valid.copy()


# --- Mapas: cambiar de tamaño sin inventar valores ----------------------------------------


def resize_mask(mask: np.ndarray, width: int, height: int) -> np.ndarray:
    """Cambia el tamaño de una máscara bool (H x W) o de un lote (N x H x W) por vecino más cercano.

    Nunca promedia: el resultado sigue siendo bool, sin valores intermedios.
    """
    if not isinstance(mask, np.ndarray) or mask.dtype != np.bool_ or mask.ndim not in (2, 3):
        raise InvalidInput("se esperaba una máscara bool H x W o N x H x W")
    if v.non_negative_int("width", width) == 0 or v.non_negative_int("height", height) == 0:
        raise InvalidInput("el tamaño nuevo tiene que ser > 0")
    if mask.ndim == 3:
        out = np.zeros((mask.shape[0], height, width), bool)
        for i, m in enumerate(mask):
            out[i] = resize_mask(m, width, height)
        return out
    small = cv2.resize(
        mask.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST_EXACT
    )
    return small.astype(bool)


def resize_disparity(
    disparity_px: np.ndarray, valid: np.ndarray, width: int, height: int
) -> tuple[np.ndarray, np.ndarray]:
    """Cambia el tamaño de un mapa de disparidad y su máscara.

    Usa vecino más cercano (interpolar mezclaría el borde de un objeto con el fondo e inventaría
    distancias que no existen) y multiplica los valores por el cociente de anchos, porque la
    disparidad se mide en píxeles horizontales.
    """
    d = v.array("disparity_px", disparity_px, np.float32, 2)
    v.array("valid", valid, np.bool_, 2, d.shape)
    if v.non_negative_int("width", width) == 0 or v.non_negative_int("height", height) == 0:
        raise InvalidInput("el tamaño nuevo tiene que ser > 0")
    sx = width / d.shape[1]
    out = cv2.resize(d, (width, height), interpolation=cv2.INTER_NEAREST_EXACT) * np.float32(sx)
    new_valid = resize_mask(valid, width, height)
    out[~new_valid] = np.nan
    return out.astype(np.float32), new_valid
