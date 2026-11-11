"""Modelos de lente: cómo se deforma la imagen antes de llegar al sensor.

La ELP tiene una lente gran angular (unos 115° horizontales a 1920 px): las rectas
cerca del borde salen curvas. Tres formas de describir esa deformación:

- `pinhole5`: el modelo estándar de OpenCV, 5 coeficientes (k1, k2, p1, p2, k3). Es el
  que usa la herramienta de la cátedra.
- `rational`: 8 coeficientes (k1..k6, p1, p2). Sigue mejor las lentes gran angular.
- `fisheye`: modelo equidistante de 4 coeficientes, pensado para ojos de pez.

No se elige por nombre: se calibran todos y se queda el que mejor predice fotos de
validación que no participaron del ajuste.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np


class LensModel(StrEnum):
    PINHOLE5 = "pinhole5"
    RATIONAL = "rational"
    FISHEYE = "fisheye"


_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 1e-9)


@dataclass(frozen=True, slots=True)
class Intrinsics:
    """Un ojo: matriz K (píxeles) y coeficientes de distorsión del modelo."""

    K: np.ndarray  # 3 x 3 float64
    D: np.ndarray  # columna float64; largo según el modelo


@dataclass(frozen=True, slots=True)
class Rectification:
    R1: np.ndarray
    R2: np.ndarray
    P1: np.ndarray  # 3 x 4, ojo izquierdo rectificado
    P2: np.ndarray  # 3 x 4, ojo derecho; P2[0, 3] = -fx * baseline (metros)
    Q: np.ndarray
    roi1: tuple[int, int, int, int]  # zona con píxeles válidos (x, y, w, h)
    roi2: tuple[int, int, int, int]


def _pinhole_flags(model: LensModel) -> int:
    return cv2.CALIB_RATIONAL_MODEL if model is LensModel.RATIONAL else 0


def _fisheye_flag(name: str) -> int:
    # OpenCV 4 define las constantes en cv2.fisheye; OpenCV 5 las movió a cv2, con otros
    # valores. Buscarlas por nombre funciona en las dos versiones.
    return int(getattr(cv2.fisheye, name, None) or getattr(cv2, name))


def _fisheye_flags() -> int:
    # Sin CHECK_COND: con una vista mala, OpenCV aborta toda la calibración; preferimos
    # calibrar y descartar esa vista por su error, con el motivo registrado.
    return _fisheye_flag("CALIB_RECOMPUTE_EXTRINSIC") | _fisheye_flag("CALIB_FIX_SKEW")


def _as_fisheye(points: list[np.ndarray], dims: int) -> list[np.ndarray]:
    # La API fisheye exige (1, N, k) float64; la estándar acepta (N, k) float32.
    return [np.asarray(p, np.float64).reshape(1, -1, dims) for p in points]


def calibrate_mono(
    model: LensModel, objects: list[np.ndarray], images: list[np.ndarray], size: tuple[int, int]
) -> tuple[Intrinsics, list[np.ndarray], list[np.ndarray]]:
    """Calibra un ojo. Devuelve intrínsecos y la pose del tablero en cada vista."""
    if model is LensModel.FISHEYE:
        K = np.eye(3)
        D = np.zeros((4, 1))
        _, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
            _as_fisheye(objects, 3), _as_fisheye(images, 2), size, K, D,
            flags=_fisheye_flags(), criteria=_CRITERIA,
        )  # fmt: skip
    else:
        _, K, D, rvecs, tvecs = cv2.calibrateCamera(
            objects, images, size, None, None, flags=_pinhole_flags(model), criteria=_CRITERIA
        )
    return Intrinsics(K, D.reshape(-1, 1)), list(rvecs), list(tvecs)


def calibrate_stereo(
    model: LensModel,
    objects: list[np.ndarray],
    left: list[np.ndarray],
    right: list[np.ndarray],
    intr_left: Intrinsics,
    intr_right: Intrinsics,
    size: tuple[int, int],
    refine_intrinsics: bool,
) -> tuple[float, Intrinsics, Intrinsics, np.ndarray, np.ndarray]:
    """Calibra la posición relativa de los ojos (R, T).

    Con `refine_intrinsics=False` los intrínsecos de cada ojo quedan fijos y solo se
    ajustan R y T: es más estable. Con True se reajusta todo junto partiendo de esos
    valores: puede mejorar algo o sobreajustar; lo decide la validación.
    """
    K1, D1, K2, D2 = intr_left.K, intr_left.D, intr_right.K, intr_right.D
    if model is LensModel.FISHEYE:
        flags = _fisheye_flags()
        if refine_intrinsics:
            flags |= _fisheye_flag("CALIB_USE_INTRINSIC_GUESS")
        else:
            flags |= _fisheye_flag("CALIB_FIX_INTRINSIC")
        result = cv2.fisheye.stereoCalibrate(
            _as_fisheye(objects, 3), _as_fisheye(left, 2), _as_fisheye(right, 2),
            K1.copy(), D1.copy(), K2.copy(), D2.copy(), size, flags=flags, criteria=_CRITERIA,
        )  # fmt: skip
        rms, K1, D1, K2, D2, R, T = result[:7]
    else:
        flags = _pinhole_flags(model)
        flags |= cv2.CALIB_USE_INTRINSIC_GUESS if refine_intrinsics else cv2.CALIB_FIX_INTRINSIC
        rms, K1, D1, K2, D2, R, T, *_ = cv2.stereoCalibrate(
            objects, left, right, K1.copy(), D1.copy(), K2.copy(), D2.copy(), size,
            flags=flags, criteria=_CRITERIA,
        )  # fmt: skip
    return (
        float(rms),
        Intrinsics(K1, D1.reshape(-1, 1)),
        Intrinsics(K2, D2.reshape(-1, 1)),
        np.asarray(R, np.float64),
        np.asarray(T, np.float64).reshape(3, 1),
    )


def rectify(
    model: LensModel,
    intr_left: Intrinsics,
    intr_right: Intrinsics,
    size: tuple[int, int],
    R: np.ndarray,
    T: np.ndarray,
    alpha: float,
) -> Rectification:
    """Gira virtualmente los dos ojos para que miren paralelo (misma fila = misma altura).

    `alpha` entre 0 y 1: 0 recorta hasta que todos los píxeles sean válidos, 1 conserva
    toda la imagen con bordes negros. CALIB_ZERO_DISPARITY deja doffs = 0.
    """
    K1, D1, K2, D2 = intr_left.K, intr_left.D, intr_right.K, intr_right.D
    if model is LensModel.FISHEYE:
        R1, R2, P1, P2, Q = cv2.fisheye.stereoRectify(
            K1, D1, K2, D2, size, R, T, cv2.CALIB_ZERO_DISPARITY,
            newImageSize=size, balance=float(alpha), fov_scale=1.0,
        )  # fmt: skip
        full = (0, 0, size[0], size[1])
        return Rectification(R1, R2, P1, P2, Q, full, full)
    R1, R2, P1, P2, Q, roi1, roi2 = cv2.stereoRectify(
        K1, D1, K2, D2, size, R, T, flags=cv2.CALIB_ZERO_DISPARITY, alpha=float(alpha)
    )
    return Rectification(R1, R2, P1, P2, Q, tuple(map(int, roi1)), tuple(map(int, roi2)))


def undistort_points(
    model: LensModel, points: np.ndarray, intr: Intrinsics, R: np.ndarray, P: np.ndarray
) -> np.ndarray:
    """Píxeles de la foto original -> píxeles de la imagen rectificada (N, 2)."""
    pts = np.asarray(points, np.float64).reshape(-1, 1, 2)
    if model is LensModel.FISHEYE:
        out = cv2.fisheye.undistortPoints(pts, intr.K, intr.D, R=R, P=P)
    else:
        out = cv2.undistortPoints(pts, intr.K, intr.D, R=R, P=P)
    return out.reshape(-1, 2)


def project(
    model: LensModel, objects: np.ndarray, rvec: np.ndarray, tvec: np.ndarray, intr: Intrinsics
) -> np.ndarray:
    """Puntos 3D (sistema del tablero) -> píxeles de la foto original (N, 2)."""
    if model is LensModel.FISHEYE:
        out, _ = cv2.fisheye.projectPoints(
            np.asarray(objects, np.float64).reshape(1, -1, 3), rvec, tvec, intr.K, intr.D
        )
    else:
        out, _ = cv2.projectPoints(np.asarray(objects, np.float64), rvec, tvec, intr.K, intr.D)
    return out.reshape(-1, 2)


def board_pose(
    model: LensModel, objects: np.ndarray, image: np.ndarray, intr: Intrinsics
) -> tuple[np.ndarray, np.ndarray]:
    """Pose del tablero vista desde un ojo con intrínsecos conocidos (rvec, tvec)."""
    if model is LensModel.FISHEYE:
        ok, rvec, tvec = cv2.fisheye.solvePnP(
            np.asarray(objects, np.float64).reshape(1, -1, 3),
            np.asarray(image, np.float64).reshape(1, -1, 2), intr.K, intr.D,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )  # fmt: skip
    else:
        ok, rvec, tvec = cv2.solvePnP(
            np.asarray(objects, np.float64), np.asarray(image, np.float64), intr.K, intr.D,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )  # fmt: skip
    if not ok:
        raise cv2.error("solvePnP no convergió")
    return rvec.reshape(3, 1), tvec.reshape(3, 1)


def init_maps(
    model: LensModel,
    intr: Intrinsics,
    R: np.ndarray,
    P: np.ndarray,
    size: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Mapas para cv2.remap que llevan la foto original a la rectificada."""
    if model is LensModel.FISHEYE:
        return cv2.fisheye.initUndistortRectifyMap(intr.K, intr.D, R, P, size, cv2.CV_16SC2)
    return cv2.initUndistortRectifyMap(intr.K, intr.D, R, P, size, cv2.CV_16SC2)
