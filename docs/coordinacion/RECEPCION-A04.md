# A04.1–A04.6: cambios y recepción de schema 3

Implementación delegada a Codex por Tomás; integrada en PR #10, commit `d8a38bd`.
Rama original `a/A04-auditoria`, base `3034f40`. Recepción I00 de Bauty pendiente.
A conserva responsabilidad de shared; no se editó A.md ni se declaró recepción realizada.
Reserva: shared/, tests de contratos/geometría y documentación asociada. Sin hardware.

## Qué corrige

1. Z=fB/(d+doffs): admitir d negativa/cero cuando la disparidad efectiva es positiva.
2. Mantener geometría válida tras recortes cuyo centro óptico queda fuera de la imagen.
3. Rechazar P1/P2 no finitas, incompatibles o no horizontales canónicas.
4. Validar identificadores, enums, bools y versión sin coerciones silenciosas.
5. Guardar imágenes/mapas/cajas/máscaras como copias independientes de solo lectura.
6. Comprobar identidad de frame, tamaño, geometría y calibración de detecciones.

Prevención adicional: ManualClock rechaza fracciones/negativos sin truncar; conversiones y
resize invalidan desbordamientos; geometry_id distingue cambios antes ocultos por redondeo.
Si depth_m contradice disparity_px y su geometría, check_depth_geometry lo rechaza.

## Prueba del consumidor

Una vez publicada e integrada la rama, actualizar el worktree propio desde origin/main.
Ejecutar `uv sync --locked`, `uv run ruff check .`, `uv run pytest` y `uv run visionx doctor`.
Caso mínimo: `uv run pytest tests/test_audit_regressions.py`.
La fixture pública `tests/fixtures/schema3-negative-disparity.yaml` describe un plano virtual
a 1 m con d=-4, doffs=10 y disparidad efectiva 6. Su test une frame/detección/profundidad.
No es una captura ni una calibración de la ELP.

## Adaptar productores y consumidores

Al construir Detection, indicar `geometry_id=frame.geometry_id` y
`calibration_id=frame.calibration_id` cuando las salidas estén en ese frame. El frame debe
tener referencia geométrica explícita; no inventar un ID para eludir validación.
DepthResult usa `doffs=geometry.doffs`. El estimador conserva sesión/frame y referencia
geométrica de cómputo, que puede tener otra resolución que la imagen del detector.

Antes de usar una máscara: `check_detection_frame(frame, detections)`.
Antes de medir desde depth: `check_depth_geometry(depth, compute_geometry)`.
Si hace falta resize/recorte, hacerlo explícitamente con geometría actualizada; no cambiar
solo el ID ni asumir que dos arrays del mismo tamaño representan las mismas coordenadas.

## Límites y registro

Schema 2 se rechaza. Reprocesar datos externos con contexto conocido; no migración automática.
Los snapshots consumen memoria/copia; medir antes de diseñar zero-copy. No se ejecutó Mac,
MPS, cámara, modelos ni audio. Registrar commit/fixture/comando/salida en I00 tras recepción;
antes de eso las fichas conservan su estado oficial pendiente en A.md.

Próximos pasos y criterios: [mejoras preventivas](MEJORAS-PREVENTIVAS.md).
