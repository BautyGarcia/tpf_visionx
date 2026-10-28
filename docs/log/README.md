# Registro de trabajo

Un archivo por entrada: `AAAA-MM-DD-HHMM-<autor>-<tema>.md`. Al ser archivos distintos, dos ramas
nunca chocan al mezclar. Ordenados por nombre quedan en orden cronológico.

Se crea con `uv run visionx log "tema"`, que completa fecha, autor, rama y archivos cambiados.
Después se completan a mano las secciones.

Para ponerse al día: `uv run visionx novedades` (anda igual en macOS y Windows).
