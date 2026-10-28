---
fecha: 2026-10-28 17:32
autor: Bauty Garcia
agente: claude-code
rama: a/C04-mac
tarea: C04
---

# C04 entorno Mac y protección de main

## Qué se hizo

- Comprobación de la Mac física, con los comandos de `docs/coordinacion/C04.md`, sobre `main` en
  `0843227`:

| Componente | Resultado |
|---|---|
| Equipo | macOS 15.7.3, arm64 (Apple M2 Max, 32 GB) |
| uv | 0.13.6 (actualizado desde 0.9.28 con `uv self update`) |
| Git | 2.39.5 (Apple Git-154) |
| Python | 3.11.18, instalado con `uv python install 3.11.18` |
| Dependencias | `uv sync --locked --extra ml` correcto; uv.lock sin cambios |
| Hooks | `core.hooksPath = .githooks`; doctor los informa activos |
| Doctor | código 0; numpy 2.4.6, OpenCV 5.0.0, ChArUco y WLS disponibles |
| ML | torch 2.15.0, MPS disponible, CUDA no |
| Formato / lint | 15 archivos conformes; sin errores |
| Tests | 14 aprobados |

- Repositorio pasado a **público** por decisión de Bauty (dueño), para poder usar rulesets sin
  GitHub Pro.
- Ruleset `proteger-main` (id 26067558) activo sobre la rama por defecto, sin excepciones
  (bypass vacío). Verificado por API: `branches/main` devuelve `protected: true`.
  - Pull request obligatorio con **0 aprobaciones**, sin revisión de code owners, conversaciones
    resueltas y merge solo por squash.
  - Checks obligatorios `core-ubuntu-latest`, `core-windows-latest` y `core-macos-latest`, con la
    rama al día con main.
  - Bloqueados borrado de main y force push; historia lineal.

## Archivos cambiados

- docs/log/2026-10-28-1732-bauty-garcia-c04-entorno-mac-y-proteccion-de-main.md

## Decisiones tomadas (y por qué)

- Repo público en vez de GitHub Pro: funciona en el momento y no depende de una aprobación externa.
- El ruleset existente exigía un check llamado `test`, que dejó de existir cuando la CI pasó a la
  matriz `core-<so>`. Se reemplazó por los tres checks nuevos; si no, ningún PR se podía mergear.
- 0 aprobaciones, según la decisión 0001 (merge del autor con checks).

## Cómo probarlo

```text
uv run --locked visionx doctor
uv run --locked pytest
gh api repos/BautyGarcia/tpf_visionx/rulesets/26067558
gh api repos/BautyGarcia/tpf_visionx/branches/main --jq .protected
```

## Pendiente / próximo paso

- Tomás tilda en `C04.md` los ítems de Mac y protección remota y marca C04 hecha.

## Avisos para el otro

- Con uv anterior a 0.13 no se encuentra Python 3.11.18: hay que correr `uv self update`.
- Si se renombran los jobs de la CI, hay que actualizar los checks obligatorios del ruleset; si no,
  los PR quedan bloqueados esperando un check que no existe.
- El repo es público: nada de datos personales, claves ni grabaciones de personas.
