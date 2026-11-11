"""Detección de las esquinas del damero en una imagen.

La herramienta de la cátedra achica la imagen para ir rápido y después refina. Acá
priorizamos precisión: el detector `findChessboardCornersSB` de OpenCV trabaja a
resolución completa y estima cada esquina con precisión subpíxel ajustando el patrón
de luz alrededor, en vez de buscar el máximo de un gradiente. Si falla, se prueba el
detector clásico con refinamiento `cornerSubPix`.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from visionx.calibration.board import Checkerboard
from visionx.shared.errors import InvalidInput

# Cambiar este número invalida las detecciones guardadas en caché.
DETECTOR_VERSION = 1


@dataclass(frozen=True, slots=True)
class Corners:
    """Esquinas detectadas en un ojo: (N, 2) float32 en píxeles, mismo orden que el tablero."""

    points: np.ndarray
    method: str  # "sb" (preciso) o "classic" (respaldo)
    sharpness: float  # nitidez en la zona del tablero; baja = foto movida o desenfocada


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    raise InvalidInput("se esperaba una imagen gris (H x W) o BGR (H x W x 3)")


def detect_corners(image: np.ndarray, board: Checkerboard) -> Corners | None:
    """Busca el tablero completo. Devuelve None si no aparecen todas las esquinas."""
    gray = to_gray(image)
    method = "sb"
    flags = cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCornersSB(gray, board.pattern_size, flags=flags)
    if not found:
        method = "classic"
        flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
        found, corners = cv2.findChessboardCorners(gray, board.pattern_size, flags=flags)
        if not found:
            return None
        # La ventana de refinamiento tiene que ser menor que medio cuadrado; si no,
        # mezcla dos esquinas vecinas.
        side = _min_square_px(corners.reshape(-1, 2), board)
        half = int(np.clip(side / 4, 2, 11))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-4)
        corners = cv2.cornerSubPix(gray, corners, (half, half), (-1, -1), criteria)
    points = np.ascontiguousarray(corners.reshape(-1, 2), dtype=np.float32)
    if points.shape != (board.n_corners, 2) or not np.isfinite(points).all():
        return None
    return Corners(points, method, _sharpness(gray, points))


def match_order(left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, bool]:
    """Garantiza que la esquina i sea el mismo punto físico en los dos ojos.

    Un damero con distinta cantidad de esquinas por lado solo admite una ambigüedad:
    girarlo 180° da la numeración al revés. Si los dos ojos la eligen distinto, el par
    es basura para el estéreo. Lo detectamos comparando la dirección "primera -> última
    esquina" en cada ojo. Devuelve (right corregido, si hubo que invertirlo).
    """
    forward_left = left[-1] - left[0]
    forward_right = right[-1] - right[0]
    if float(np.dot(forward_left, forward_right)) < 0:
        return np.ascontiguousarray(right[::-1]), True
    return right, False


def _min_square_px(points: np.ndarray, board: Checkerboard) -> float:
    grid = points.reshape(board.rows, board.cols, 2)
    along_row = np.linalg.norm(np.diff(grid, axis=1), axis=2)
    along_col = np.linalg.norm(np.diff(grid, axis=0), axis=2)
    return float(min(along_row.min(), along_col.min()))


def _sharpness(gray: np.ndarray, points: np.ndarray) -> float:
    """Varianza del laplaciano dentro del rectángulo del tablero (más alto = más nítido)."""
    x0, y0 = np.floor(points.min(axis=0)).astype(int)
    x1, y1 = np.ceil(points.max(axis=0)).astype(int)
    h, w = gray.shape
    patch = gray[max(y0, 0) : min(y1, h), max(x0, 0) : min(x1, w)]
    if patch.size == 0:
        return 0.0
    return float(cv2.Laplacian(patch, cv2.CV_64F).var())
