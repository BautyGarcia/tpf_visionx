"""Lector y escritor de PFM, el formato de disparidad de Middlebury y ETH3D.

PFM es texto + floats crudos:
    línea 1: "Pf" (un canal) o "PF" (tres canales)
    línea 2: ancho alto
    línea 3: escala; su signo da el orden de bytes (negativa = little-endian)
    después: floats de 32 bits, **de la fila de abajo hacia arriba**.

Por eso al leer se invierten las filas: queremos la fila 0 arriba, como en las imágenes.
Middlebury marca los píxeles sin GT con infinito; acá no se interpreta nada, eso lo decide
cada adaptador.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from visionx.shared.errors import InvalidInput


def read_pfm(path: str | Path) -> np.ndarray:
    """Devuelve float32 H x W (o H x W x 3), con la fila 0 arriba."""
    path = Path(path)
    with path.open("rb") as f:
        header = f.readline().strip()
        if header not in (b"Pf", b"PF"):
            raise InvalidInput(f"{path}: no es PFM (encabezado {header!r})")
        channels = 1 if header == b"Pf" else 3
        try:
            width, height = (int(x) for x in f.readline().split())
            scale = float(f.readline().strip())
        except ValueError as exc:
            raise InvalidInput(f"{path}: encabezado PFM mal formado") from exc
        if width <= 0 or height <= 0 or scale == 0:
            raise InvalidInput(f"{path}: tamaño o escala PFM inválidos")
        dtype = "<f4" if scale < 0 else ">f4"
        count = width * height * channels
        data = np.frombuffer(f.read(count * 4), dtype=dtype)
    if data.size != count:
        raise InvalidInput(f"{path}: PFM truncado ({data.size} de {count} valores)")
    shape = (height, width) if channels == 1 else (height, width, 3)
    return np.flipud(data.reshape(shape)).astype(np.float32)


def write_pfm(path: str | Path, values: np.ndarray) -> None:
    """Escribe float32 H x W (o H x W x 3) en PFM little-endian. Se usa en tests."""
    values = np.asarray(values, np.float32)
    if values.ndim not in (2, 3) or (values.ndim == 3 and values.shape[2] != 3):
        raise InvalidInput("PFM admite H x W o H x W x 3")
    header = "Pf" if values.ndim == 2 else "PF"
    height, width = values.shape[:2]
    with Path(path).open("wb") as f:
        f.write(f"{header}\n{width} {height}\n-1.0\n".encode("ascii"))
        f.write(np.flipud(values).astype("<f4").tobytes())
