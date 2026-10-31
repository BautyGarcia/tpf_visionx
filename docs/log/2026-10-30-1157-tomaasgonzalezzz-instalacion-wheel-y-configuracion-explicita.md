---
fecha: 2026-10-30 11:57
autor: TomaasGonzalezzz
agente: codex
rama: b/B27-instalacion
tarea: B27.1
---

# instalación wheel y configuración explícita

## Qué se hizo

Defaults incluidos en wheel desde fuente única; --config explícito, doctor --runtime-only, YAML raíz validado y log con error claro fuera del checkout. Script portable verify_wheel.py comentado; independiente de schema 3.

## Archivos cambiados

- `README.md`
- `docs/coordinacion/B.md`
- `docs/coordinacion/RECEPCION-B27.md`
- `docs/coordinacion/tareas/B27.1.md`
- `pyproject.toml`
- `scripts/README.md`
- `scripts/verify_wheel.py`
- `src/visionx/cli.py`
- `src/visionx/devtools/worklog.py`
- `src/visionx/shared/config.py`
- `tests/test_installation.py`

## Decisiones tomadas (y por qué)

Priorizar corrección y legibilidad; cambios mínimos por tarea con comentarios de unidades/invariantes.

## Cómo probarlo

uv sync --locked; ruff format/check correctos; 150 tests aprobados; doctor correcto. Wheel construido/instalado en venv separado; cinco casos con cwd temporal y -I correctos: import/defaults y doctor runtime código 0; doctor sin Git, log y config inválida código 1 sin traceback ni escritura externa de docs/log.

## Pendiente / próximo paso

Commit/push y publicación autorizados por Tomás el 30/10/2026. Falta recepción I08 en Mac. No hay mediciones de hardware.

## Avisos para el otro

Ver guía RECEPCION-A04/RECEPCION-B27 en la rama correspondiente. Base 3034f40 más diff local, no un commit publicado.
<!-- cambios en contratos, dependencias nuevas, cosas que rompen o que tiene que saber -->

Regresión adicional del registro: conservar columnas de git status para no truncar nombres.

Wheel local verificado: outputs/wheel-final/visionx-0.1.0-py3-none-any.whl
SHA-256: b1d8f7ef7aed5f1da76428c838e6f46e1f237f1b465302c7ed81951a6e7a1b18. Artefacto ignorado por Git; no publicado en almacén.
