# VisionX: reglas de ejecución para personas y agentes

## 1. Plan y responsables

Leer [PLAN.md](docs/coordinacion/PLAN.md), el índice [A.md](docs/coordinacion/A.md) o
[B.md](docs/coordinacion/B.md), la ficha en docs/coordinacion/tareas/ y su integración Ixx.
El [tablero](docs/coordinacion/TAREAS.md) es la entrada común. Los PDF históricos son referencias.

| Persona | Responsabilidad | Rutas propias |
|---|---|---|
| A: Bauty, Mac/Claude Code | Datos, profundidad clásica, CNN y evaluación | src/visionx/depth/, datasets/, experiments/, docs/coordinacion/A.md |
| B: Tomás, Windows/Codex | Cámara, calibración, detección, aplicación y hardware | src/visionx/{camera,calibration,detection,speech,modes,gui,transport}/, docs/coordinacion/B.md |

Tests/configs/scripts del módulo pertenecen al mismo responsable. B mantiene cli.py.
A mantiene depth/spatial/ (objeto + profundidad -> posición/política).
shared/, dependencias, CI y documentos comunes: reservar editor por WhatsApp/en persona y
registrarlo en la tarea. No se necesita aprobación de contenido del compañero.

## 2. Trabajar sin pisarse

1. Leer git status y uv run visionx novedades; no borrar ni mover cambios de otra tarea.
2. Cada persona/coordinador actualiza solo su fichero A/B. Agentes de implementación no compiten
   por editar el tablero. Registrar estado, rama y rutas reservadas.
3. Una tarea por rama **y un worktree/carpeta por agente simultáneo que modifica archivos**.
   No ejecutar git switch en el checkout ajeno. Ramas a/Axx-tema o b/Bxx-tema desde origin/main
   actualizado. Procedimiento en docs/coordinacion/FLUJO.md.
4. Reservar cámara, GPU, micrófono, puertos y outputs. Worktrees no aíslan hardware.
   Usar fakes/replay mientras el recurso está ocupado.
5. Consumir APIs públicas de docs/CONTRATOS.md, nunca privados del otro. Cambio semántico de
   contrato: versión, fixture y migración en PR pequeño; comunicar al consumidor.

## 3. Integrar sin aprobaciones cruzadas

- PR como registro y diff. **No se requiere revisión ni aprobación del compañero**.
  El autor puede hacer squash merge cuando pasan checks y dependencias.
- No commits ni push directo a main. Integrar cambios pequeños y compatibles durante la etapa.
  No forzar merge con checks fallidos ni sobrescribir cambios ajenos.
- Archivo compartido: reservar edición. Consultar solo cambios de decisión/interfaz/unidad que
  afecten al otro; no pedir aprobación de cada PR.
- Consumidor actualiza su rama y ejecuta recepción I00-I08 después del merge. Es una prueba de
  compatibilidad, no una aprobación del contenido.
- Checkbox [x] y estado hecha solo con aceptación y evidencia. Si el código ya está en main y falta recepción:
  conservar estado por integrar y anotar `integrado: <commit>; recepción: pendiente` en su índice.
  Esa API puede habilitar otras tareas; no confundir recepción pendiente con código sin integrar. No tildar hitos sin prueba de ambos lados.
- Política remota objetivo: PR, **0 aprobaciones**, sin code-owner review y checks técnicos
  requeridos. C04 verifica esos ajustes; los archivos locales no cambian reglas de GitHub.

## 4. Verificación y registro

Python 3.11 y uv. Base para captura/tests; extra ml solo para tareas neuronales.

~~~text
uv sync --locked
uv sync --locked --extra ml
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run visionx doctor
uv run visionx novedades
uv run visionx log "tema" --agente codex --tarea B02
~~~

Antes de integrar: checks pertinentes, registro corto, evidencia y contrato/lock actualizados.
Documentación sola: validar enlaces, IDs/dependencias y diff; no afirmar tests o mediciones
no ejecutados. Reformatear solo si no altera cambios ajenos.
Commits tipo(área): descripción en español (feat/fix/test/docs/refactor/chore/exp).
Sin firmas ni coautoría de herramientas. Agentes solo commitean/pushean por pedido explícito
para esa tarea. Resolver conflictos preservando ambos trabajos.

## 5. Reproducibilidad y límites

- Parámetros en configs/; overrides en configs/local.yaml ignorado. El llamador debe cargarlo
  explícitamente: su existencia no implica carga automática.
- Dependencias con uv add y lock versionado. Videos/pesos/calibraciones por
  docs/coordinacion/ARTEFACTOS.md; nunca rutas personales como fuente compartida.
- Texto UTF-8 y LF; rutas pathlib; código portable. Núcleo/replay en Windows y Mac.
  Mac prueba MPS; Windows CPU; CUDA/VM si se requiere. Demo objetivo Mac por USB.
- Tests automáticos sin cámara, GPU, internet ni modelos descargados. Mediciones físicas aparte,
  con hardware, commit, config, hashes, n y unidades. Nunca inventar resultados.
- No secretos ni pesos en Git; fixtures pequeñas <1 MB. No push --force, reset --hard,
  borrados ajenos ni reescritura de main sin pedido explícito.

## 6. Consigna para una IA

Indicar persona, ID, rama/worktree, rutas y recursos disponibles. Implementar el alcance,
ejecutar verificación y devolver artefacto, métricas, límites y prueba para el consumidor.
No solicitar aprobación del compañero por cada paso. Si falta hardware, usar el fake acordado
y dejar la medición física pendiente.

## Traspaso entre agentes

La unidad es la tarea, no el agente: un worktree por tarea (`../visionx-wt/<ID>-tema`, rama
`a/` o `b/` según FLUJO.md). Claude y Codex pueden alternarse en el mismo worktree sin aviso.
- Al empezar: leer `TRASPASO.md` en la raíz del worktree (si existe), `git status`/`git diff`
  y `uv run visionx novedades`.
- Después de cada paso significativo, actualizar `TRASPASO.md` con:
  tarea (Axx/Bxx/Ixx), objetivo, hecho, en curso, próximo paso concreto,
  decisiones tomadas, lo que se probó y falló, y comandos de verificación.
- Si la tarea produce o consume una integración Ixx, anotar qué falta del otro lado;
  el estado oficial sigue en A.md/B.md.
- Mantenerlo corto (máx. ~40 líneas); reemplazar, no acumular.
- No commitear `TRASPASO.md`.

## Ejecución paralela v2

A/B son responsables de integración, no límites de ejecutores. Varios agentes por área con
rutas separadas. Las fichas no duplican estados; el coordinador actualiza el índice A/B.
No editar índices ajenos salvo tarea documental expresamente delegada, como C09.
WhatsApp sirve para recursos/decisiones humanas; especificación/evidencia queda en Git.
