---
fecha: 2026-10-28 17:21
autor: TomaasGonzalezzz
agente: codex
rama: b/C04-entorno-windows
tarea: C04
---

# C04 entorno Windows y verificación remota

## Qué se hizo

- uv 0.13.6 permanente y PATH de usuario; Python 3.11.18 exacto, entorno nuevo y base locked.
- Autoría Git local y hooks activos; probados con Git de terminal normal en repo temporal.
- Doctor devuelve error si faltan hooks; dos tests nuevos. C03 cerrada por PR #2 integrado.
- GitHub: cuenta Tomás con push sin admin; main sin protección; squash sí; rulesets no
  habilitados por el plan privado. CI existente correcta, sin checks requeridos.
- C04 en curso: Windows listo; faltan Mac y resolución de protección, detalle en C04.md.

## Archivos cambiados

- .python-version, README.md, src/visionx/cli.py, tests/test_environment.py
- docs/coordinacion/TAREAS.md, FLUJO.md, C04.md y esta entrada

## Decisiones tomadas (y por qué)

- Pin 3.11.18: uv falla con enlace menor 3.11 de esta PC, pero versión exacta funciona.
- Base sin ML para primeras tareas B; instalar extra cuando una tarea neuronal lo requiera.
- No cambiar visibilidad ni pago de GitHub ni afirmar protección que no aplica el servidor.

## Cómo probarlo

- uv sync --locked; uv run --locked visionx doctor: correctos, hooks activos y ML opcional ausente.
- uv run --locked ruff format --check .: 15 conformes; ruff check: sin errores.
- uv run --locked pytest: 14 aprobados en 0,86 s.
- PATH sistema/usuario: uv/Git/doctor ejecutados sin herramientas temporales.
- Hooks: sintaxis 3/3, main y mensaje inválido rechazados; rama permitida; pre-push de rama
  ejecuta tests. Nunca se hizo push de prueba a main del proyecto.
- uv venv --python 3.11.18 crea entorno nuevo y su Python ejecuta correctamente.
- API GitHub: branch protected=false, squash permitido, permisos sin admin, rulesets 403;
  CI de ac66b96 correcta en los tres SO. No se inspeccionaron ni guardaron tokens en archivos.

## Pendiente / próximo paso

- Evidencia Mac de Bauty y decisión/aplicación de protección remota. Secuencia en C04.md.
- C04 no se marca globalmente hecha por completar solo Windows.

## Avisos para el otro

- Incorporar esta rama antes de ejecutar secuencia Mac. Hooks se configuran por clon.
- Sin cambios de dependencias/lock ni contratos. Los hooks no reemplazan protección remota.
