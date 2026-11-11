"""Sesiones de fotos: una carpeta con pares left_N / right_N y sus esquinas detectadas.

Una sesión es una tanda de fotos sacada sin tocar la cámara (mismo foco, misma
resolución). Mantener sesiones separadas permite comprobar que dos calibraciones
independientes den lo mismo, como pide la métrica M3.

Las detecciones se guardan en `.visionx-esquinas.json` dentro de la carpeta, indexadas
por el hash de cada imagen: si la foto no cambia, no se vuelve a detectar.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from visionx.calibration.board import Checkerboard
from visionx.calibration.detection import DETECTOR_VERSION, Corners, detect_corners, match_order
from visionx.shared.errors import InvalidInput

CACHE_NAME = ".visionx-esquinas.json"
_PAIR_RE = re.compile(r"^(left|right)_(\d+)\.(jpg|jpeg|png)$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PairView:
    """Un par estéreo con el tablero detectado completo en los dos ojos."""

    session: str
    index: int
    left: np.ndarray  # (N, 2) float32, píxeles del ojo izquierdo
    right: np.ndarray  # (N, 2) float32, mismo orden físico que left
    image_size: tuple[int, int]  # (ancho, alto) de cada ojo
    left_sha256: str
    right_sha256: str
    sharpness: tuple[float, float]
    reordered: bool = False  # True si hubo que invertir la numeración del ojo derecho

    @property
    def key(self) -> str:
        return f"{self.session}#{self.index}"


@dataclass(slots=True)
class Session:
    name: str
    folder: Path
    views: list[PairView] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)  # pares sin detección o incompletos
    total_pairs: int = 0


def find_pairs(folder: Path) -> tuple[list[tuple[int, Path, Path]], list[str]]:
    """Empareja left_N con right_N. Devuelve (pares ordenados por N, avisos)."""
    if not folder.is_dir():
        raise InvalidInput(f"no existe la carpeta de fotos {folder}")
    found: dict[int, dict[str, Path]] = {}
    for path in folder.iterdir():
        match = _PAIR_RE.match(path.name)
        if match:
            found.setdefault(int(match.group(2)), {})[match.group(1).lower()] = path
    pairs, problems = [], []
    for index in sorted(found):
        eyes = found[index]
        if "left" in eyes and "right" in eyes:
            pairs.append((index, eyes["left"], eyes["right"]))
        else:
            missing = "right" if "left" in eyes else "left"
            problems.append(f"par {index}: falta la foto {missing}_{index}")
    return pairs, problems


def load_session(
    folder: str | Path,
    board: Checkerboard,
    name: str | None = None,
    workers: int | None = None,
    use_cache: bool = True,
) -> Session:
    """Detecta el tablero en todos los pares de la carpeta (en paralelo, con caché)."""
    folder = Path(folder)
    # La herramienta de la cátedra guarda en <sesión>/calib: usar el nombre de la sesión.
    default_name = folder.parent.name if folder.name == "calib" else folder.name
    session = Session(name or default_name, folder)
    pairs, session.problems = find_pairs(folder)
    session.total_pairs = len(pairs)
    if not pairs:
        raise InvalidInput(f"{folder}: no hay fotos left_N.jpg / right_N.jpg")

    cache_path = folder / CACHE_NAME
    cache = _read_cache(cache_path, board) if use_cache else {}
    paths = [p for _, left, right in pairs for p in (left, right)]
    hashes = {p: _sha256(p) for p in paths}
    todo = [p for p in paths if hashes[p] not in cache]

    # OpenCV libera el GIL mientras detecta: los hilos sí corren en paralelo.
    with ThreadPoolExecutor(max_workers=workers or min(8, os.cpu_count() or 1)) as pool:
        results = pool.map(lambda p: _detect_file(p, board), todo)
        for path, result in zip(todo, results, strict=True):
            cache[hashes[path]] = result
    if use_cache and todo:
        _write_cache(cache_path, board, cache)

    for index, left_path, right_path in pairs:
        left, right = cache[hashes[left_path]], cache[hashes[right_path]]
        if left is None or right is None:
            eye = "izquierdo" if left is None else "derecho"
            if left is None and right is None:
                eye = "los dos ojos"
            session.problems.append(f"par {index}: tablero no detectado en {eye}")
            continue
        if left["size"] != right["size"]:
            session.problems.append(f"par {index}: los dos ojos tienen distinto tamaño")
            continue
        right_points, reordered = match_order(left["corners"].points, right["corners"].points)
        session.views.append(
            PairView(
                session=session.name,
                index=index,
                left=left["corners"].points,
                right=right_points,
                image_size=tuple(left["size"]),
                left_sha256=hashes[left_path],
                right_sha256=hashes[right_path],
                sharpness=(left["corners"].sharpness, right["corners"].sharpness),
                reordered=reordered,
            )
        )
    sizes = {view.image_size for view in session.views}
    if len(sizes) > 1:
        raise InvalidInput(f"{folder}: hay fotos de resoluciones distintas {sorted(sizes)}")
    return session


def _detect_file(path: Path, board: Checkerboard) -> dict | None:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise InvalidInput(f"no se pudo leer la imagen {path}")
    corners = detect_corners(image, board)
    size = [int(image.shape[1]), int(image.shape[0])]
    return None if corners is None else {"corners": corners, "size": size}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_signature(board: Checkerboard) -> dict:
    return {"detector": DETECTOR_VERSION, "opencv": cv2.__version__, "board": board.label}


def _read_cache(path: Path, board: Checkerboard) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if data.get("signature") != _cache_signature(board):
        return {}  # otro tablero, otro detector u otra versión de OpenCV: detectar de nuevo
    cache = {}
    for sha, item in data.get("entries", {}).items():
        if item is None:
            cache[sha] = None
            continue
        points = np.asarray(item["points"], dtype=np.float32)
        cache[sha] = {
            "corners": Corners(points, item["method"], float(item["sharpness"])),
            "size": item["size"],
        }
    return cache


def _write_cache(path: Path, board: Checkerboard, cache: dict) -> None:
    entries = {}
    for sha, item in cache.items():
        if item is None:
            entries[sha] = None
        else:
            corners: Corners = item["corners"]
            entries[sha] = {
                # float32 -> float de Python es exacto: releer da el mismo array.
                "points": corners.points.tolist(),
                "method": corners.method,
                "sharpness": corners.sharpness,
                "size": item["size"],
            }
    payload = {"signature": _cache_signature(board), "entries": entries}
    try:
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # la caché es una comodidad: si la carpeta es de solo lectura, se recalcula
