"""Chequeos de arrays usados por los contratos. Uso interno de shared/."""

from __future__ import annotations

import math

import numpy as np

from visionx.shared.errors import InvalidInput


def array(
    name: str,
    value: object,
    dtype: type | np.dtype,
    ndim: int,
    shape: tuple[int | None, ...] | None = None,
) -> np.ndarray:
    """Verifica que value sea un ndarray con el dtype, la cantidad de ejes y la forma pedidos.

    En shape, None significa "cualquier tamaño en ese eje".
    """
    if not isinstance(value, np.ndarray):
        raise InvalidInput(f"{name}: se esperaba numpy.ndarray, llegó {type(value).__name__}")
    if value.dtype != np.dtype(dtype):
        raise InvalidInput(f"{name}: se esperaba dtype {np.dtype(dtype)}, llegó {value.dtype}")
    if value.ndim != ndim:
        raise InvalidInput(f"{name}: se esperaban {ndim} ejes, llegó forma {value.shape}")
    if shape is not None:
        for axis, (got, want) in enumerate(zip(value.shape, shape, strict=True)):
            if want is not None and got != want:
                raise InvalidInput(
                    f"{name}: eje {axis} mide {got}, se esperaba {want} (forma {value.shape})"
                )
    return value


def text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput(f"{name}: se esperaba texto no vacío, llegó {value!r}")
    return value


def non_negative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | np.integer) or value < 0:
        raise InvalidInput(f"{name}: se esperaba entero >= 0, llegó {value!r}")
    return int(value)


def finite(name: str, value: object, low: float | None = None, high: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | np.integer | np.floating):
        raise InvalidInput(f"{name}: se esperaba un número, llegó {value!r}")
    v = float(value)
    if not math.isfinite(v):
        raise InvalidInput(f"{name}: tiene que ser finito, llegó {v}")
    if low is not None and v < low:
        raise InvalidInput(f"{name}: tiene que ser >= {low}, llegó {v}")
    if high is not None and v > high:
        raise InvalidInput(f"{name}: tiene que ser <= {high}, llegó {v}")
    return v


def finite_positive_inside(name: str, values: np.ndarray, mask: np.ndarray) -> None:
    """Dentro de la máscara, todos los valores son finitos y > 0. Afuera, cualquier cosa."""
    inside = values[mask]
    if inside.size and not (np.all(np.isfinite(inside)) and np.all(inside > 0)):
        raise InvalidInput(f"{name}: dentro de la máscara válida hay NaN, infinitos o valores <= 0")


def snapshot(value: np.ndarray) -> np.ndarray:
    """Copia estable y de solo lectura; el almacenamiento bytes no admite setflags(write=True)."""
    # Solo setflags(write=False) no alcanza: el dueño del array original podría volver
    # a escribir. Copiamos a bytes, que es inmutable, y reconstruimos una vista NumPy.
    # La copia conserva dtype/shape y evita compartir memoria con buffers de captura.
    storage = value.tobytes(order="C")
    read_only_array = np.frombuffer(storage, dtype=value.dtype)
    return read_only_array.reshape(value.shape)
