# VisionX

Anteojos con cámara estéreo que le dicen por voz a una persona con baja visión dónde están las cosas.
TPF de I308 Visión Artificial, UdeSA, Primavera 2026. El plan operativo vigente está en
[`docs/coordinacion/PLAN.md`](docs/coordinacion/PLAN.md). Propuesta para la cátedra en `entregas/`.

**Antes de trabajar, leer [`AGENTS.md`](AGENTS.md)**: reglas para las dos personas y sus agentes.

## Entorno

Requiere [uv](https://docs.astral.sh/uv/) y Python 3.11.18 (fijado en `.python-version`).

```bash
uv sync --locked            # dependencias base + herramientas de desarrollo
uv sync --locked --extra ml # además PyTorch (MPS en la Mac, CUDA en la VM)
uv run visionx doctor   # revisa OpenCV, ChArUco, WLS, config y PyTorch
uv run pytest           # tests
uv run ruff check .     # lint
git config core.hooksPath .githooks   # una vez por clon: activa los hooks
```

Preparación Windows/Mac: [C04](docs/coordinacion/C04.md). Cada clon activa sus hooks;
la CI de GitHub no reemplaza la verificación del equipo físico.

## Estructura

```
configs/        configuración (default.yaml) y, más adelante, calibraciones elegidas
src/visionx/
  shared/       contratos entre módulos, config y reloj común
  devtools/     registro de trabajo y otras herramientas del equipo
  cli.py        comando `visionx` (doctor, log)
tests/          tests que corren sin cámara ni GPU
scripts/        utilidades de una sola vez (descargas, preprocesado)
docs/           consignas, propuesta y decisiones (docs/decisiones/)
entregas/       documentos para la cátedra
```

Las carpetas por módulo (`camera/`, `calibration/`, `depth/`, `detection/`, `speech/`, `modes/`,
`gui/`, `transport/`) se agregan cuando se empieza cada uno.

## Coordinación

- Reglas y procedimiento: [`AGENTS.md`](AGENTS.md).
- Tablero/arranque: [`TAREAS.md`](docs/coordinacion/TAREAS.md).
- Consignas completas: [A01-A29, Bauty](docs/coordinacion/A.md) y [B01-B28, Tomás](docs/coordinacion/B.md).
- **Cuándo combinar resultados:** [I00-I08](docs/coordinacion/INTEGRACIONES.md).
- [Métricas](docs/coordinacion/METRICAS.md), [contratos objetivo](docs/CONTRATOS.md) y
  [entrega de artefactos](docs/coordinacion/ARTEFACTOS.md).
- [Flujo Git](docs/coordinacion/FLUJO.md): una rama/worktree por tarea, checks y merge del autor;
  **sin aprobación obligatoria del compañero**. Después se verifica recepción técnica.
- Registro de trabajo: [`docs/log/`](docs/log/), un archivo por entrada (`uv run visionx log "tema"`).
- Decisiones: [`docs/decisiones/`](docs/decisiones/).
