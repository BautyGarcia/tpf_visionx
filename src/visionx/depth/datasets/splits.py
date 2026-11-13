"""Particiones por escena, deterministas y sin fuga.

Regla (TECNICO T04): pares casi iguales de una misma escena/sesión no pueden quedar en
grupos distintos. Por eso se reparten **escenas**, no pares.

El orden se decide con SHA-256 de "semilla:escena", no con `random` ni con `hash()` de
Python: da lo mismo en Windows, Mac y cualquier versión, y el orden relativo de las escenas
no depende de cuáles otras haya.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from visionx.shared.errors import InvalidInput


def _rank(seed: str, scene: str) -> str:
    return hashlib.sha256(f"{seed}:{scene}".encode()).hexdigest()


def split_scenes(scenes: Iterable[str], fraction: float, seed: str) -> tuple[list[str], list[str]]:
    """Separa escenas en (resto, apartadas) con ~`fraction` de las escenas apartadas.

    Se apartan las escenas con menor rango: al menos una si fraction > 0.
    """
    unique = sorted(set(scenes))
    if not 0.0 <= fraction < 1.0:
        raise InvalidInput("fraction tiene que estar en [0, 1)")
    if not unique:
        raise InvalidInput("no hay escenas para partir")
    n_out = round(len(unique) * fraction)
    if fraction > 0:
        n_out = max(1, n_out)
    if n_out >= len(unique):
        raise InvalidInput("la fracción deja el resto vacío")
    ranked = sorted(unique, key=lambda s: _rank(seed, s))
    held = sorted(ranked[:n_out])
    rest = sorted(ranked[n_out:])
    return rest, held


def check_no_leak(groups: dict[str, Iterable[str]]) -> None:
    """Falla si una escena aparece en dos grupos (p. ej. train y val)."""
    seen: dict[str, str] = {}
    for group, scenes in groups.items():
        for scene in scenes:
            if scene in seen and seen[scene] != group:
                raise InvalidInput(f"fuga: la escena {scene!r} está en {seen[scene]} y {group}")
            seen[scene] = group
