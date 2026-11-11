"""Tablero de calibración: qué medimos en el mundo real.

Usamos un damero común. Lo que importa para OpenCV no son los cuadrados sino las
**esquinas internas**: los puntos donde se tocan cuatro cuadrados. Un tablero de
10 x 7 cuadrados tiene 9 x 6 esquinas internas.

El tamaño del cuadrado se mide con regla sobre el tablero impreso. Todas las distancias
que salgan después (baseline, metros) heredan ese número: si está mal medido un 2 %,
todas las distancias quedan mal un 2 %.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from visionx.shared.errors import InvalidInput


@dataclass(frozen=True, slots=True)
class Checkerboard:
    """Damero plano con `cols` x `rows` esquinas internas y cuadrados de `square_m` metros."""

    cols: int  # esquinas internas en horizontal
    rows: int  # esquinas internas en vertical
    square_m: float  # lado de un cuadrado, en metros

    def __post_init__(self) -> None:
        for name in ("cols", "rows"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 3:
                raise InvalidInput(f"{name} tiene que ser un entero >= 3 (esquinas internas)")
        # Con la misma cantidad en las dos direcciones, el tablero se ve igual girado 90°
        # y OpenCV no puede saber cuál es la primera esquina: los dos ojos podrían
        # numerarlas distinto sin que nada lo detecte.
        if self.cols == self.rows:
            raise InvalidInput("usar un tablero con distinta cantidad de esquinas por lado")
        if not math.isfinite(self.square_m) or self.square_m <= 0:
            raise InvalidInput("square_m tiene que ser un número > 0, en metros")
        if self.square_m > 1:
            raise InvalidInput("square_m va en metros: 28 mm es 0.028")

    @classmethod
    def parse(cls, pattern: str, square_mm: float) -> Checkerboard:
        """Arma el tablero desde el texto '9x6' (esquinas internas) y el cuadrado en mm."""
        match = re.fullmatch(r"\s*(\d+)\s*[xX]\s*(\d+)\s*", pattern)
        if match is None:
            raise InvalidInput(f"tablero '{pattern}': se esperaba COLSxFILAS, por ejemplo 9x6")
        return cls(int(match.group(1)), int(match.group(2)), float(square_mm) / 1000.0)

    @property
    def pattern_size(self) -> tuple[int, int]:
        """(cols, rows), en el orden que pide OpenCV."""
        return self.cols, self.rows

    @property
    def n_corners(self) -> int:
        return self.cols * self.rows

    @property
    def label(self) -> str:
        return f"{self.cols}x{self.rows}@{self.square_m * 1000:g}mm"

    def object_points(self) -> np.ndarray:
        """Esquinas en el sistema del tablero, en metros, forma (N, 3) float32.

        El tablero está en el plano Z = 0. El orden es fila por fila, con x variando más
        rápido: es el mismo orden en que OpenCV devuelve las esquinas detectadas.
        """
        grid = np.mgrid[0 : self.cols, 0 : self.rows].T.reshape(-1, 2)
        points = np.zeros((self.n_corners, 3), np.float32)
        points[:, :2] = grid * self.square_m
        return points
