---
fecha: 2026-10-28 16:35
autor: Tomás
agente: codex
rama: b/C03-planificacion-integracion
tarea: C03
---

# Planificación completa y puntos de integración

## Qué se hizo

- Plan E0-E8, 29 tareas A y 28 B con dependencia, consigna, entrega, métricas y consumidor.
- I00-I08 definen orden de merge, artefactos cruzados y recepción técnica; sin aprobación
  obligatoria del compañero. C02 corregida a hecha por commit bf9d43a/PR #1.
- Contratos objetivo, métricas M0-M12, protocolo de artefactos y flujo con worktrees.
- Reglas/plantilla/CODEOWNERS alineados con merge del autor y checks; CI del núcleo en
  Windows/macOS/Linux y lock estricto. Reglas remotas NO verificadas ni modificadas.
- Novedades lee tareas activas de A/B/hitos, conservando compatibilidad del tablero anterior.

## Archivos cambiados

- AGENTS.md, CLAUDE.md, README.md, .github/{CODEOWNERS,pull_request_template.md,workflows/ci.yml}
- docs/coordinacion/{TAREAS,PLAN,A,B,INTEGRACIONES,METRICAS,ARTEFACTOS,FLUJO}.md
- docs/CONTRATOS.md, docs/decisiones/0001-plan-operativo-y-merge-autonomo.md
- src/visionx/{cli.py,devtools/worklog.py}, tests/test_worklog.py

## Decisiones tomadas (y por qué)

- Pedido de Tomás: coordinación directa, sin aprobar contenido del otro. Se conserva recepción
  técnica para saber que una entrega realmente puede usarse; no es autorización de un PR.
- Fusion 10 canales es principal; v7 Lite 7 canales es antecedente. Lite/wearable condicionados.
- Se conservan IDs existentes y se ordena por etapa/dependencia. No se inventan fechas/horas
  ni se marcan tareas futuras implementadas. La API objetivo queda asignada a A04.

## Cómo probarlo

- uv sync --locked (CPython 3.11.18 explícito para evitar problema de enlace de instalación uv).
- uv run --locked ruff format --check .: 15 archivos conformes.
- uv run --locked ruff check .: sin errores.
- uv run --locked pytest: 12 tests aprobados, incluidos 2 nuevos del tablero distribuido.
- uv run --locked visionx novedades: muestra C03 y registro; admite estados nuevos y anteriores.
- Validación estática: 74 IDs únicos (A29/B28/C8/I9), referencias/enlaces/anclas válidos;
  grafo de dependencias principal sin ciclos. I07 admite no aplica y variantes seleccionadas.
- git diff --check: sin errores. CI remota y macOS/Linux aún no ejecutados desde esta rama.

## Pendiente / próximo paso

- Cambios locales sin commit/push; C03 en curso hasta integrar/publicar por pedido de la persona.
- C04: uv se usó desde carpeta temporal para verificar; todavía no está instalado en PATH.
  Doctor verifica numpy/OpenCV/ChArUco/WLS/config; avisa hooks inactivos y ml no instalado.
  No equivale a completar ambos entornos ni reglas de GitHub. Preparar eso en C04.
- C05: elegir ubicación real de artefactos. C06: confirmar alcance/equipo/fechas con cátedra.

## Avisos para el otro

- Leer docs/coordinacion/PLAN.md y A.md/B.md; los PDF viejos no son instrucciones vigentes.
- Primer intercambio: A04 -> A05/B02/B04 -> I00; luego A06 + B05-B07 -> I01 sin esperar CNN.
- GitHub debe permitir 0 aprobaciones y checks. Si main exige reviews actualmente, un
  administrador ajusta reglas en C04; cambiar CODEOWNERS local no modifica ese requisito.
