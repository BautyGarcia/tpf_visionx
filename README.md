# VisionX

Proyecto de I308 Visión Artificial, UdeSA, primavera 2026. Buscamos que una cámara estéreo
ayude a una persona con baja visión a buscar objetos, consultar distancias, leer y describir
escenas mediante audio. Primero funcionará por USB en computadora; después incorporará
Raspberry, batería y las capacidades del roadmap completo.

## Por dónde empezar

| Archivo | Para qué leerlo |
|---|---|
| [ROADMAP](docs/ROADMAP.md) | Entender el proyecto, sus etapas, alternativas y las 20 tareas |
| [TECNICO](docs/TECNICO.md) | Entender cada componente, sus entradas/salidas, decisiones y pruebas previstas |
| [BITACORA](docs/BITACORA.md) | Saber qué se hizo realmente, qué falló y qué falta; base del informe final |
| [AGENTS](AGENTS.md) | Trabajar con personas y agentes sin pisarse ni adelantarse al pedido |

Son documentos internos de aprendizaje y trabajo, no un texto para presentar al jurado.
Las siglas se explican en TECNICO. La entrega es el **10 de diciembre de 2026**.
Completar la entrega académica no equivale a terminar todas las capacidades de VisionX.

## Estado real

Hay entorno, contratos y geometría compartida, validadores, tests y utilidades de diagnóstico.
La aplicación completa, la CNN entrenada, los comparadores y las mediciones físicas siguen
pendientes. Los detalles y la evidencia están en ROADMAP y BITACORA.
Esta revisión documental no implementa los módulos futuros.

## Preparar el entorno cuando se vaya a implementar

Python 3.11.18 y [uv](https://docs.astral.sh/uv/). Desde el repositorio:

```text
uv sync --locked
git config core.hooksPath .githooks
uv run visionx doctor
```

En Windows con Smart App Control activado, los `.exe` que uv genera para los comandos
(`visionx.exe`, `pytest.exe`) pueden quedar bloqueados («os error 4551»). Usar el intérprete:
`uv run python -m visionx doctor` y `uv run python -m pytest`. Si el bloqueado es
`.venv\Scripts\python.exe`, renombrar `.venv` y volver a correr `uv sync --locked`.

Las tareas neuronales usan `uv sync --locked --extra ml`; los modelos/pesos se obtienen
por separado y se verifican antes de usarlos. `configs/local.yaml` solo se carga si se elige
explícitamente con el mecanismo indicado por el comando; existir no lo activa.
Una instalación distribuida usa `visionx doctor --runtime-only`.
Consultar TECNICO para las verificaciones futuras; no ejecutarlas por leer este README.

## Qué carpetas quedan

`src/` contiene código; `tests/` sus pruebas; `configs/` parámetros; `scripts/` utilidades.
`docs/` contiene los tres documentos principales y referencias originales de la materia.
`entregas/` conserva la propuesta HTML/PDF anterior: sus cifras son propuestas, no mediciones,
y hay que sincronizarla antes de una nueva entrega. Datos, videos y pesos van al almacén compartido.

El plan distribuido anterior y los registros originales se pueden recuperar desde el historial
de Git. La correspondencia de sus IDs está al final de ROADMAP. No hay que navegar por
esas fichas para empezar una tarea nueva. `docs/CONTRATOS.md` queda solo como enlace de
compatibilidad, porque hay comentarios del código publicado que apuntan a esa ruta.

Para ponerse al día, Bauty puede actualizar su `main` limpio con `git pull --ff-only` y abrir
los tres documentos. Si hay cambios locales o una tarea en curso, conservarlos y actualizar
su rama según AGENTS; no descartar trabajo para forzar el pull.

`visionx log` y `visionx novedades` todavía usan el esquema documental anterior: no muestran
ni mantienen estos archivos nuevos. Hasta adaptar esas utilidades, escribir directamente en
BITACORA y consultar ROADMAP. No perder resultados por confiar en el comando heredado.
