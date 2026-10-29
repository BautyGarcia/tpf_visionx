"""Relojes. Las duraciones se miden siempre con un reloj monotónico.

En vivo se usa MonotonicClock. En replay y en tests se usa ManualClock, que avanza con la
reproducción: así los vencimientos (TTL) se evalúan con el tiempo de la grabación y no con el
reloj de la máquina. Nunca se restan monotónicos de máquinas distintas (PC y Raspberry Pi).
"""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


def now_ns() -> int:
    """Reloj monotónico local, en nanosegundos."""
    return time.monotonic_ns()


@runtime_checkable
class Clock(Protocol):
    def now_ns(self) -> int: ...


class MonotonicClock:
    """Reloj real de esta máquina."""

    def now_ns(self) -> int:
        return time.monotonic_ns()


class ManualClock:
    """Reloj que solo avanza cuando se lo pide. Para replay y tests."""

    def __init__(self, start_ns: int = 0) -> None:
        self._t = int(start_ns)

    def now_ns(self) -> int:
        return self._t

    def set(self, t_ns: int) -> None:
        if t_ns < self._t:
            raise ValueError("un reloj monotónico no retrocede")
        self._t = int(t_ns)

    def advance(self, dt_ns: int) -> None:
        self.set(self._t + int(dt_ns))
