---
fecha: 2026-10-30 11:56
autor: TomaasGonzalezzz
agente: codex
rama: a/A04-auditoria
tarea: A04
---

# correcciones de geometría y contratos schema 3

## Qué se hizo

A04.1–A04.6: doffs/recortes/P1-P2, validadores, snapshots y referencia geométrica. Schema 3, fixture pública y migración. Reloj, overflow y comentarios explicativos. Código de B27.1 separado en worktree propio; sin cambios al índice A.

## Archivos cambiados

- `docs/CONTRATOS.md`
- `docs/coordinacion/AUDITORIA.md`
- `docs/coordinacion/MEJORAS-PREVENTIVAS.md`
- `docs/coordinacion/RECEPCION-A04.md`
- `docs/coordinacion/tareas/A04.1.md`
- `docs/coordinacion/tareas/A04.2.md`
- `docs/coordinacion/tareas/A04.3.md`
- `docs/coordinacion/tareas/A04.4.md`
- `docs/coordinacion/tareas/A04.5.md`
- `docs/coordinacion/tareas/A04.6.md`
- `src/visionx/shared/_validate.py`
- `src/visionx/shared/clock.py`
- `src/visionx/shared/contracts.py`
- `src/visionx/shared/geometry.py`
- `tests/fixtures/schema3-negative-disparity.yaml`
- `tests/test_audit_regressions.py`
- `tests/test_contracts.py`
- `tests/test_geometry.py`
- `tests/test_interfaces.py`

## Decisiones tomadas (y por qué)

Priorizar corrección y legibilidad; cambios mínimos por tarea con comentarios de unidades/invariantes.

## Cómo probarlo

uv sync --locked; ruff format/check correctos; 185 tests aprobados; doctor correcto; sin hardware/modelos. Incluye cv2.stereoRectify con cámara virtual y rotaciones pequeñas.

## Pendiente / próximo paso

Commit/push y publicación autorizados por Tomás el 30/10/2026. Falta recepción I00/Mac y compatibilidad de futuros consumidores.

## Avisos para el otro

Ver guía RECEPCION-A04/RECEPCION-B27 en la rama correspondiente. Base 3034f40 más diff local, no un commit publicado.
<!-- cambios en contratos, dependencias nuevas, cosas que rompen o que tiene que saber -->
