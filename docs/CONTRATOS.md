# Contratos técnicos objetivo

Especificación a implementar en **A04/B02/B04**. A04 prepara cambio compartido, tests y
migración; B aporta requisitos de replay. No crear una segunda familia de mensajes. Cambios
semánticos se versionan.

## Estado de la implementación

**A04 (schema 2)**: mensajes, interfaces, errores, relojes y geometría en `src/visionx/shared/`.

| Archivo | Contenido |
|---|---|
| `contracts.py` | FrameKey, StereoFrame, DepthResult (+DepthStatus), Detection, SpatialObject, Command, AudioEvent; `check_schema`, `check_same_frame`, `check_geometry`, `check_not_expired` |
| `interfaces.py` | Protocols FrameSource, DepthEstimator, Detector, SpatialEstimator, AudioSink |
| `errors.py` | InvalidInput, SchemaMismatch, IdentityMismatch, Expired (ValueError); SourceError, EstimatorError (RuntimeError) |
| `clock.py` | `now_ns`, Clock, MonotonicClock (vivo), ManualClock (replay y tests) |
| `geometry.py` | StereoGeometry (fx, fy, cx, cy, B, doffs, `geometry_id`), `from_projections` (P1/P2 de OpenCV), d <-> Z, `pixel_to_angles`, `resized`, `cropped`; `resize_mask` y `resize_disparity` por vecino más cercano |

- Los mensajes son inmutables y se validan al crearse; un esquema distinto da SchemaMismatch.
  No había datos persistidos con schema 1, así que no hace falta migración.
- Fallo de cámara o de modelo: excepción (SourceError/EstimatorError). Fin de grabación:
  `read()` devuelve None. Cero objetos: Detection vacía. Profundidad no medible: DepthResult con
  status y reason.
- Geometría: Z = fx·B / (d + doffs), con doffs = cx_der - cx_izq. Al cambiar de tamaño se
  alinean centros de píxel: x' = (x + 0.5)·s - 0.5; la disparidad escala con el ancho. Los mapas
  y máscaras nunca se interpolan: vecino más cercano, para no inventar distancias en los bordes.

## Interfaces públicas

| Servicio | Operación objetivo | Resultado/fallo |
|---|---|---|
| FrameSource (B) | read() -> StereoFrame o None; close() | None solo EOS normal de replay; error de dispositivo explícito |
| DepthEstimator (A) | predict(frame) -> DepthResult; close() | status válido/parcial/no medible con motivo |
| Detector (B) | predict(frame) -> Detection; close() | cero objetos válido; fallo de modelo distinto de ausencia |
| SpatialEstimator (A) | locate(frame, depth, detections) | lista SpatialObject; rechazar IDs/geometrías incompatibles |
| AudioSink (B) | submit(event); cancel(request_id); close() | eventos medibles de inicio/fin/cancelación |

B conecta APIs sin importar privados de A. Fakes y reales tienen la misma firma. Comandos CLI
de fichas son entregables futuros hasta que la tarea correspondiente se cierre.

## Identidad y geometría

- Clave: sesión + frame_id; predicciones conservan esa identidad. Referenciar calibración y
  geometry_id directamente o mediante contexto inmutable accesible; no unir frames diferentes.
- Imagen pública BGR uint8 HxWx3; ojos del mismo par. A convierte RGB solo al preparar red.
  Validar dtype/tamaños; operaciones inválidas no se convierten en mediciones silenciosas.
- Máscaras: izquierda rectificada a 1080p. Depth: par rectificado 720p u otra resolución declarada.
  Conservar escala/recorte, P1/P2/Q y transformación a resolución original.
- Transformar en un solo lugar: máscaras vecino cercano; disparidad escala con el ancho;
  intrínsecos/doffs se ajustan al resize/recorte. No usar K cruda tras rectificar.
- Disparidad float32 en px de cómputo; GT con escala/signo/doffs explícitos. Profundidad float32
  en metros, máscara bool. NaN solo fuera de máscara válida; cero no significa distancia válida.
- b Laplace positiva/finita en px de disparidad, distinta de consistencia L-R. Validar shapes
  de depth, máscaras e incertidumbre; máscaras de detección coinciden con cantidad de objetos.
- SpatialObject informa Z axial de superficie visible típica. Inicial: mediana de disparidad
  válida en máscara interior, convertida con geometría. Cobertura/umbrales se fijan en desarrollo.
  Ángulo h positivo derecha, v arriba. No mezclar score detector y calidad de profundidad en una
  supuesta probabilidad conjunta sin definición/calibración.

## Tiempo y fallos

- Monotónico local para duraciones. Conservar captura si existe y distinguir recepción;
  timestamps estimados por backend se rotulan. Replay conserva tiempo original y de reproducción;
  TTL se evalúa con reloj de reproducción, no con monotónicos históricos.
- Request_id y deadline; cancelar invalida resultados/audio anteriores. Guía requiere observación
  reciente. Distancia congela el frame consultado. No restar monotónicos de PC y Pi.
- Consumidor rechaza schema incompatible, IDs/geometría distintos, shapes inválidas y TTL vencido.
  Mala alineación monocular: estado/motivo y fallback declarado, sin rellenar ceros.
- A04 prueba geometría/entradas adversas; B02 prueba orden/EOS; B05/B19 prueban TTL/cancelación.

## Entregas entre áreas

B->A: replay I00; pares y calibración I02; set ELP/GT I03; medidas finales I06.
A->B: FakeDepth I00; SpatialObject I01; SGBM I02; B4 I03; Fusion I04; políticas I05;
Lite I07 si corresponde. Cada entrega lleva manifiesto, config, versión y prueba de recepción.
