"""Reproducir una grabación como si fuera la cámara (FrameSource).

Conserva la identidad y los tiempos originales: cada par sale con el mismo session_id y
frame_id que tuvo al grabarse, y replay_original_ns guarda su received_ns original. El
received_ns nuevo es el del reloj de la reproducción:

- Con ManualClock (tests, comparación científica) el reloj avanza exactamente lo que avanzó
  la grabación, sin esperar: los vencimientos se evalúan con el tiempo grabado.
- Con realtime=True se espera entre pares para respetar el ritmo original (demo, panel).
- Si no, los pares salen tan rápido como se leen del disco.

Un archivo faltante, un hash distinto o un índice roto son SourceError: no es lo mismo que
el fin normal de la grabación, que se indica devolviendo None.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from visionx.camera.recording import FORMAT, INDEX, MANIFEST, VERSION
from visionx.shared.clock import Clock, ManualClock, MonotonicClock
from visionx.shared.contracts import CaptureClock, StereoFrame
from visionx.shared.errors import SourceError


def load_recording(folder: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    """Lee manifiesto e índice. Devuelve (manifiesto, entradas, índice_truncado).

    Si la grabación se cortó a mitad de escribir una línea, esa última línea incompleta se
    ignora y se informa como truncado. Una línea rota en el medio es un error.
    """
    folder = Path(folder)
    try:
        manifest = yaml.safe_load((folder / MANIFEST).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SourceError(f"{folder}: no hay {MANIFEST}; no es una grabación") from exc
    if not isinstance(manifest, dict) or manifest.get("formato") != FORMAT:
        raise SourceError(f"{folder}: el manifiesto no es de formato {FORMAT}")
    if manifest.get("version") != VERSION:
        raise SourceError(
            f"{folder}: grabación versión {manifest.get('version')}, este código lee {VERSION}"
        )
    try:
        raw = (folder / INDEX).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SourceError(f"{folder}: falta {INDEX}") from exc

    lines = raw.split("\n")
    # Si el archivo termina en salto de línea, el último elemento es "" y todo está completo.
    complete, tail = lines[:-1], lines[-1]
    entries: list[dict[str, Any]] = []
    for number, line in enumerate(complete, start=1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SourceError(f"{folder / INDEX}: línea {number} ilegible") from exc
    truncated = bool(tail.strip())  # una línea sin salto final quedó a medio escribir

    last = -1
    for entry in entries:
        frame_id = entry.get("frame_id")
        if not isinstance(frame_id, int) or frame_id <= last:
            raise SourceError(f"{folder / INDEX}: frame_id {frame_id!r} fuera de orden")
        last = frame_id
    return manifest, entries, truncated


class ReplaySource:
    """FrameSource que lee una grabación de Recorder."""

    def __init__(
        self,
        folder: str | Path,
        *,
        clock: Clock | None = None,
        realtime: bool = False,
        verify_hashes: bool = True,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.folder = Path(folder)
        self.manifest, self._entries, self.truncated = load_recording(self.folder)
        session_id = self.manifest.get("session_id")
        if self._entries and not (isinstance(session_id, str) and session_id.strip()):
            raise SourceError(f"{self.folder}: el manifiesto no tiene session_id")
        # Una grabación sin pares es válida: read() devuelve None enseguida.
        self.session_id: str = session_id or "vacia"
        self._clock = clock or MonotonicClock()
        self._realtime = realtime
        self._verify = verify_hashes
        self._sleep = sleep
        self._position = 0
        self._closed = False
        # Punto de partida para traducir tiempos grabados a tiempos de reproducción.
        self._origin_recorded: int | None = None
        self._origin_clock = self._clock.now_ns()
        self._origin_wall = time.monotonic_ns()

    def __len__(self) -> int:
        return len(self._entries)

    def read(self) -> StereoFrame | None:
        if self._closed:
            raise SourceError("la reproducción está cerrada")
        if self._position >= len(self._entries):
            return None  # fin normal de la grabación
        entry = self._entries[self._position]
        self._position += 1
        left = self._load(entry, "left")
        right = self._load(entry, "right")
        received_ns = self._advance(int(entry["received_ns"]))
        capture_ns = entry.get("capture_ns")
        try:
            return StereoFrame(
                session_id=self.session_id,
                frame_id=int(entry["frame_id"]),
                left=left,
                right=right,
                received_ns=received_ns,
                capture_ns=capture_ns,
                capture_clock=CaptureClock(entry.get("capture_clock", "none")),
                replay_original_ns=int(entry["received_ns"]),
                rectified=bool(self.manifest.get("rectificado") or False),
                calibration_id=self.manifest.get("calibration_id"),
                geometry_id=self.manifest.get("geometry_id"),
                source_id=self.manifest.get("source_id") or "replay",
            )
        except ValueError as exc:  # InvalidInput hereda de ValueError
            raise SourceError(f"frame {entry.get('frame_id')}: {exc}") from exc

    def _load(self, entry: dict[str, Any], eye: str) -> np.ndarray:
        relative = entry.get(eye)
        if not isinstance(relative, str):
            raise SourceError(f"frame {entry.get('frame_id')}: falta la ruta del ojo {eye}")
        path = self.folder / relative
        try:
            data = path.read_bytes()
        except FileNotFoundError as exc:
            raise SourceError(f"falta {path}") from exc
        if self._verify and hashlib.sha256(data).hexdigest() != entry.get(f"sha256_{eye}"):
            raise SourceError(f"{path}: el SHA-256 no coincide con el registrado al grabar")
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise SourceError(f"{path}: OpenCV no pudo decodificar la imagen")
        expected = self.manifest.get("ojo")
        if expected and [image.shape[1], image.shape[0]] != list(expected):
            raise SourceError(
                f"{path}: mide {image.shape[1]}x{image.shape[0]}, se esperaba {expected}"
            )
        return image

    def _advance(self, recorded_ns: int) -> int:
        """Lleva el reloj de reproducción al tiempo que corresponde a este par."""
        if self._origin_recorded is None:
            self._origin_recorded = recorded_ns
        offset = max(0, recorded_ns - self._origin_recorded)
        if isinstance(self._clock, ManualClock):
            target = self._origin_clock + offset
            if target > self._clock.now_ns():
                self._clock.set(target)
        elif self._realtime:
            wait_ns = self._origin_wall + offset - time.monotonic_ns()
            if wait_ns > 0:
                self._sleep(wait_ns / 1e9)
        return self._clock.now_ns()

    def close(self) -> None:
        self._closed = True
