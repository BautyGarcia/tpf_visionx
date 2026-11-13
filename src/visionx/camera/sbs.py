"""Separar el cuadro side by side (SBS) de la ELP en ojo izquierdo y derecho.

La ELP entrega una sola imagen con los dos ojos uno al lado del otro: la mitad izquierda del
cuadro es el ojo izquierdo y la derecha, el derecho. Si en alguna unidad o montaje aparecen
invertidos, se corrige con `swap_eyes` en la config, nunca negando disparidades o metros.
"""

from __future__ import annotations

import numpy as np

from visionx.shared.errors import InvalidInput


def split_sbs(frame: np.ndarray, *, swap_eyes: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve (izquierdo, derecho) a partir de un cuadro SBS BGR uint8 de H x W x 3.

    Las mitades son vistas del mismo buffer: StereoFrame las copia al construirse, así que
    la cámara puede reutilizar su buffer sin alterar un par ya entregado.
    """
    if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8:
        raise InvalidInput("el cuadro SBS tiene que ser un ndarray uint8")
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise InvalidInput(f"el cuadro SBS tiene que ser H x W x 3, llegó {frame.shape}")
    height, width = frame.shape[:2]
    if width == 0 or height == 0 or width % 2:
        raise InvalidInput(f"el ancho SBS tiene que ser par y > 0, llegó {width}x{height}")
    half = width // 2
    left, right = frame[:, :half], frame[:, half:]
    return (right, left) if swap_eyes else (left, right)
