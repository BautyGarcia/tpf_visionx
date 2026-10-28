# AGENTS.md: reglas para trabajar en VisionX

Este archivo lo leen las personas y los agentes de IA (Claude Code, Codex u otros) antes de tocar
el repo. Si una regla de acá choca con una costumbre del agente, gana este archivo.

## 1. Quiénes trabajan

Dos personas, cada una con su agente, en sistemas distintos: una en **macOS con Claude Code** y
otra en **Windows con GPT (Codex)**. Todo lo del repo tiene que funcionar en los dos. Cada persona
es dueña de un área:

| Rol | Persona | Área | Carpetas |
|---|---|---|---|
| **A** | Bauty, `BautyGarcia` (macOS, Claude Code) | Datos, red y evaluación | `src/visionx/depth/learned/`, `src/visionx/depth/eval/`, `datasets/`, `experiments/` |
| **B** | Tomás, `TomaasGonzalezzz` (Windows, Codex) | Cámara, aplicación y hardware | `src/visionx/camera/`, `calibration/`, `detection/`, `speech/`, `modes/`, `gui/`, `transport/` |
| Ambos | | Compartido | `src/visionx/shared/`, `configs/default.yaml`, `pyproject.toml`, `AGENTS.md`, `.github/` |

`src/visionx/depth/classical/` (SGBM, WLS, regla fija B4) es de A, y B lo usa desde la aplicación.

## 2. Antes de empezar cualquier tarea

1. `git switch main && git pull` y `uv sync --extra ml`.
2. `uv run visionx novedades`: muestra las últimas entradas de `docs/log/` y las tareas en curso.
   Leer las entradas nuevas del otro: qué hizo, qué quedó pendiente, qué avisó.
3. Anotarse la tarea en `TAREAS.md`, en **su propia sección**, con estado `en curso` y la rama.
4. Crear la rama desde `main` actualizado: `git switch -c <a|b>/<id>-<tema-corto>`,
   por ejemplo `b/T03-captura-elp`.

## 3. Mientras se trabaja

- **Una tarea por rama, una rama por agente.** Dos agentes nunca trabajan en la misma rama.
- **Solo tocar el área propia.** Si hace falta cambiar algo del área del otro, no se edita: se anota
  en `TAREAS.md` como pedido en la sección del dueño, o se avisa a la persona.
- **Lo compartido se cambia en un PR aparte, chico, que revisan los dos.** En especial
  `src/visionx/shared/contracts.py`: si cambia el significado de un campo, se sube
  `SCHEMA_VERSION` y se explica en el PR.
- **Los módulos se hablan solo con los contratos** de `shared/contracts.py`. Nada de importar
  funciones internas del área del otro.
- **Probar sin hardware.** Todo módulo tiene una versión falsa o un replay para que el otro pueda
  usarlo sin cámara ni GPU. Los tests no usan cámara, internet ni GPU.
- **Dependencias:** `uv add <paquete>` (o `uv add --optional ml <paquete>`). Nunca `pip install`.
  Si cambian `pyproject.toml` y `uv.lock`, se dice en el PR.
- **Parámetros en `configs/`, no en el código.** Lo personal (índice de cámara, rutas) va en
  `configs/local.yaml`, que no se sube.
- **Nada pesado a git:** datos, pesos, grabaciones y calibraciones de sesión quedan fuera
  (ver `.gitignore`). Los fixtures de tests van en `tests/fixtures/` y pesan menos de 1 MB.

## 4. Antes de abrir el pull request

1. `uv run ruff format . && uv run ruff check . && uv run pytest` sin errores.
2. Escribir la entrada del registro: `uv run visionx log "tema corto" --agente <claude-code|codex>
   --tarea <ID>` crea el archivo en `docs/log/`; completar todas las secciones.
3. Actualizar `TAREAS.md` (estado `en revisión`).
4. Commits con el formato `tipo(área): descripción`, en español. Tipos: `feat`, `fix`, `test`,
   `docs`, `refactor`, `chore`, `exp` (experimento). Ejemplo: `feat(camera): separar par estéreo`.
5. `git pull --rebase origin main` para quedar al día, y abrir el PR con la plantilla.

## 5. Revisión y merge

- `main` está protegida: no se commitea directo (el hook lo frena) y no se hace push directo.
- Todo PR lo revisa la otra persona (o su agente, y la persona aprueba). Los PR que tocan
  lo compartido los aprueban los dos.
- Merge con **squash**. Se borra la rama después.
- Si hay conflicto, lo resuelve quien abrió el PR, nunca descartando cambios del otro sin hablarlo.

## 6. Lo que un agente nunca hace sin que su persona lo pida explícitamente

- `git push --force`, `git reset --hard`, borrar ramas ajenas, reescribir historia de `main`.
- Commitear o pushear (salvo que la persona lo haya pedido para esa tarea).
- Borrar o mover archivos del área del otro.
- Agregar secretos, claves de API o datos personales al repo. Las claves van en `.env`.
- Inventar resultados: números de métricas o latencias solo salen de scripts que se corrieron,
  y se guardan en `experiments/`.

**Autoría.** Los agentes nunca figuran como autores ni colaboradores. Los commits no llevan
líneas `Co-Authored-By` de agentes, y los commits, PRs y documentos no llevan firmas como
"Generated with Claude Code". El autor es siempre la persona. El hook `commit-msg` borra esas
líneas si aparecen.

## 7. Dos sistemas operativos

- **Código portable:** rutas con `pathlib`, nunca `"carpeta\\archivo"` ni `"carpeta/archivo"` armadas
  a mano. Abrir archivos de texto siempre con `encoding="utf-8"`. Nada de comandos de shell
  dentro del código de Python.
- **Saltos de línea:** `.gitattributes` guarda todo con LF. No cambiarlo. Los hooks fallan con CRLF.
- **Cámara:** el backend de OpenCV se elige en `configs/default.yaml` (`camera.backend`). En Windows
  suele hacer falta `dshow` o `msmf`. El índice de cámara de cada uno va en `configs/local.yaml`.
- **PyTorch:** en la Mac usa MPS; en Windows corre en CPU. Nadie del equipo tiene GPU NVIDIA:
  lo que exige CUDA (Fast-FoundationStereo, FoundationStereo, MonSter, DEFOM) se corre en una
  máquina virtual con GPU, solo para entrenar y comparar. La demo en vivo corre en la Mac.
  `uv run visionx doctor` dice qué acelerador está activo.
- **Comandos en la documentación:** los que se escriben para el otro tienen que andar en PowerShell
  y en zsh. Para cosas del equipo se usa `uv run visionx ...`, que anda igual en los dos.
- **Hooks en Windows:** Git for Windows los corre con su propio `sh`; no hace falta nada más,
  salvo que `uv` esté en el PATH.

## 8. Comandos

Instalar uv: macOS `curl -LsSf https://astral.sh/uv/install.sh | sh`; Windows (PowerShell)
`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.

```bash
uv sync --extra ml            # entorno
uv run visionx doctor         # diagnóstico
uv run pytest                 # tests
uv run ruff format . && uv run ruff check .
uv run visionx novedades      # qué hizo el otro y qué está en curso
uv run visionx log "tema" --agente codex --tarea B02   # nueva entrada del registro
git config core.hooksPath .githooks   # una sola vez por clon: activa los hooks
```

## 9. Dónde está cada cosa

- `docs/coordinacion/TAREAS.md`: tablero de tareas, una sección por persona.
- `docs/log/`: registro de trabajo, un archivo por entrada (así nunca hay conflictos).
- `docs/decisiones/`: una nota por decisión importante.
- Plan técnico completo: artifact "Plan VisionX". Propuesta a la cátedra: `entregas/`.
