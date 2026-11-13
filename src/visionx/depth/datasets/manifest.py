"""Manifiestos de datasets: qué archivos hay, cuánto pesan y su SHA-256.

Los datos no van a Git. Lo que va a Git es `datasets/<nombre>.yaml` con el origen, la
licencia, las reglas de GT, las particiones y el hash de cada archivo descargado. Con eso,
otra computadora puede comprobar que tiene exactamente los mismos bytes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from visionx.shared.errors import InvalidInput

CHUNK = 1 << 20  # leer de a 1 MiB: los zips pueden pesar GB


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def file_entry(path: Path, root: Path) -> dict[str, Any]:
    """Entrada de manifiesto con ruta relativa portable (con /), bytes y hash."""
    return {
        "ruta": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def load_manifest(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "nombre" not in data:
        raise InvalidInput(f"{path}: no es un manifiesto de dataset")
    return data


def save_manifest(path: str | Path, data: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    path.write_text(text, encoding="utf-8")
    return path


def verify_files(entries: list[dict[str, Any]], root: Path) -> list[str]:
    """Problemas encontrados (faltante, tamaño o hash distinto). Lista vacía = todo bien."""
    problems = []
    for entry in entries:
        path = root / entry["ruta"]
        if not path.exists():
            problems.append(f"falta {entry['ruta']}")
        elif path.stat().st_size != entry["bytes"]:
            problems.append(f"tamaño distinto: {entry['ruta']}")
        elif sha256_file(path) != entry["sha256"]:
            problems.append(f"hash distinto: {entry['ruta']}")
    return problems
