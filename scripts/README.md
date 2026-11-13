# Utilidades

Los scripts complementan las tareas del [ROADMAP](../docs/ROADMAP.md).
Ejecutarlos solo al implementar o verificar el trabajo solicitado.

`verify_wheel.py --python <intérprete>` comprueba una instalación distribuida desde un
directorio externo. Procedimiento y límites en [TECNICO](../docs/TECNICO.md#reproducibilidad).
No abre hardware ni descarga pesos; requiere un wheel instalado previamente.

## `calibracion/` (T02/T03, abren la cámara salvo `zonas`, `control` y `offset_cinta`)

Herramientas usadas en las sesiones de la ELP; cada archivo explica su uso al principio.
Los datos que generan quedan en carpetas locales ignoradas por Git y pueden mostrar personas.

- `auto_captura.py`: fotos de calibración sin manos (dispara con el tablero quieto).
- `cinta.py`: distancia estéreo contra cinta métrica; guarda pares y `resultados.csv`.
- `offset_cinta.py`: con los pares de `cinta.py`, ajusta la corrección de disparidad (δ) y la
  verifica por `calib.geometry()`; `--salida` guarda la calibración corregida.
- `modos.py`: modos reales, FPS medidos y corrida larga con caídas y memoria.
- `deriva_captura.py`: un par cada N segundos con todo quieto, para medir deriva térmica.
- `zonas.py`: zona 3x3 y giro de cada foto, con mosaico para revisar cobertura.
- `control.py`: error vertical y escala de fotos nuevas con una calibración fija.
