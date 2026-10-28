"""Crea entradas del registro de trabajo en docs/log/, un archivo por entrada."""

from __future__ import annotations

import re
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path

from visionx.shared.config import ROOT

LOG_DIR = ROOT / "docs" / "log"

TEMPLATE = """---
fecha: {fecha}
autor: {autor}
agente: {agente}
rama: {rama}
tarea: {tarea}
---

# {tema}

## Qué se hizo


## Archivos cambiados
{archivos}

## Decisiones tomadas (y por qué)


## Cómo probarlo


## Pendiente / próximo paso


## Avisos para el otro
<!-- cambios en contratos, dependencias nuevas, cosas que rompen o que tiene que saber -->
"""


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:50] or "entrada"


def changed_files() -> list[str]:
    """Archivos cambiados respecto de main, más los no commiteados."""
    files: set[str] = set()
    base = _git("merge-base", "HEAD", "main")
    if base:
        files.update(_git("diff", "--name-only", base).splitlines())
    files.update(line[3:] for line in _git("status", "--porcelain").splitlines() if line)
    return sorted(f for f in files if f and not f.startswith("docs/log/"))


def new_entry(tema: str, agente: str = "", tarea: str = "", now: datetime | None = None) -> Path:
    now = now or datetime.now()
    autor = _git("config", "user.name") or "sin-nombre"
    rama = _git("branch", "--show-current") or "sin-rama"
    archivos = "\n".join(f"- `{f}`" for f in changed_files()) or "- (ninguno detectado)"
    name = f"{now:%Y-%m-%d-%H%M}-{slugify(autor)}-{slugify(tema)}.md"
    path = LOG_DIR / name
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        TEMPLATE.format(
            fecha=f"{now:%Y-%m-%d %H:%M}",
            autor=autor,
            agente=agente or "-",
            rama=rama,
            tarea=tarea or "-",
            tema=tema,
            archivos=archivos,
        ),
        encoding="utf-8",
    )
    return path


def recent(n: int = 5) -> list[dict[str, str]]:
    """Últimas n entradas del registro, de la más nueva a la más vieja."""
    entries = []
    for path in sorted(LOG_DIR.glob("20*.md"), reverse=True)[:n]:
        meta: dict[str, str] = {"archivo": path.name}
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines()[1:]:
            if line.strip() == "---":
                break
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
        title = next((ln[2:] for ln in text.splitlines() if ln.startswith("# ")), path.stem)
        meta["tema"] = title
        entries.append(meta)
    return entries


def tasks_in_progress() -> list[str]:
    """Líneas de TAREAS.md que están en curso, en revisión o bloqueadas, y los pedidos."""
    path = ROOT / "docs" / "coordinacion" / "TAREAS.md"
    if not path.exists():
        return []
    keep = ("[en curso]", "[en revisión]", "[bloqueada]")
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("- ") and any(k in ln for k in keep)
    ]
