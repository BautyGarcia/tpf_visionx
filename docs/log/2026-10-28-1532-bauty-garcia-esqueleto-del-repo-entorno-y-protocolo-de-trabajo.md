---
fecha: 2026-10-28 15:32
autor: Bauty Garcia
agente: claude-code
rama: main
tarea: C01
---

# Esqueleto del repo, entorno y protocolo de trabajo

## Qué se hizo
- Entorno con uv y Python 3.11: base (numpy, OpenCV contrib, pyyaml), extra `ml` (PyTorch) y dev (pytest, ruff).
- Paquete `visionx` con `shared/contracts.py` (StereoFrame, DepthResult, Detection, SpatialObject, Command, AudioEvent) y `shared/config.py`.
- Comandos `visionx doctor` y `visionx log`.
- Protocolo de trabajo: AGENTS.md, CLAUDE.md, TAREAS.md, registro en docs/log/, plantilla de decisiones y de PR.
- Hooks: sin commits ni push directo a main, sin archivos grandes, pesos ni claves, formato de commit, sin coautoría de agentes.
- Soporte para Windows y Codex: `.gitattributes` con LF, hooks portables, comando `visionx novedades`, sección de reglas para dos sistemas operativos.

## Archivos cambiados
- `.claude/`
- `.env.example`
- `.githooks/`
- `.github/`
- `.gitignore`
- `.python-version`
- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `configs/`
- `docs/`
- `entregas/`
- `pyproject.toml`
- `scripts/`
- `src/`
- `tests/`
- `uv.lock`

## Decisiones tomadas (y por qué)
- Registro con un archivo por entrada: dos ramas nunca chocan al mezclar.
- TAREAS.md con una sección por persona: cada uno edita solo la suya, sin conflictos.
- Hooks en `.githooks/` versionados, en vez de la librería pre-commit: sin dependencias extra.

## Cómo probarlo
`uv sync --extra ml`, `git config core.hooksPath .githooks`, `uv run visionx doctor`, `uv run pytest`.

## Pendiente / próximo paso
- Completar nombres en AGENTS.md (quién es A y quién B) y los usuarios en `.github/CODEOWNERS`.
- Proteger `main` en GitHub (Settings → Branches).

## Avisos para el otro
<!-- cambios en contratos, dependencias nuevas, cosas que rompen o que tiene que saber -->
- Después de clonar: `uv sync --extra ml` y `git config core.hooksPath .githooks`. Leer AGENTS.md.
- En Windows, si tenés GPU NVIDIA, PyTorch hay que instalarlo con CUDA (pedilo antes de cambiar `pyproject.toml`, es compartido).
