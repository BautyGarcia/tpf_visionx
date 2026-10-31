# Contratos técnicos objetivo

Especificación a implementar en **A04/B02/B04**. A04 prepara cambio compartido, tests y
migración; B aporta requisitos de replay. No crear una segunda familia de mensajes. Cambios
semánticos se versionan.

## Estado de la implementación

**A04 (schema 3)**: mensajes, interfaces, errores, relojes y geometría en `src/visionx/shared/`.

| Archivo | Contenido |
|---|---|
| `contracts.py` | FrameKey, StereoFrame, DepthResult (+DepthStatus), Detection, SpatialObject, Command, AudioEvent; `check_schema`, `check_same_frame`, `check_geometry`, `check_detection_frame`, `check_depth_geometry`, `check_not_expired` |
| `interfaces.py` | Protocols FrameSource, DepthEstimator, Detector, SpatialEstimator, AudioSink |
| `errors.py` | InvalidInput, SchemaMismatch, IdentityMismatch, Expired (ValueError); SourceError, EstimatorError (RuntimeError) |
| `clock.py` | `now_ns`, Clock, MonotonicClock (vivo), ManualClock (replay y tests) |
| `geometry.py` | StereoGeometry (fx, fy, cx, cy, B, doffs, `geometry_id`), `from_projections` (P1/P2 de OpenCV), d <-> Z, `pixel_to_angles`, `resized`, `cropped`; `resize_mask` y `resize_disparity` por vecino más cercano |

- Los mensajes se validan al crearse y guardan copias de solo lectura de sus arrays: el emisor
  conserva su buffer y el mensaje no cambia. Un esquema distinto da SchemaMismatch.
- Migración de schema 2 a 3 (sin fixtures persistidas de schema 2 en Git): `Detection` exige `geometry_id` y admite
  `calibration_id`; `DepthResult` admite `doffs` (default 0) y debe coincidir con su geometría.
  Solo `d + doffs` debe ser positiva: d puede ser cero o negativa. Cambian los `geometry_id`, ahora
  derivados del valor exacto de los floats. `cx`/`cy` pueden caer fuera de la imagen tras un recorte.
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
  en metros, máscara bool. NaN solo fuera de máscara válida; Z=0 es inválida, pero d=0 puede
  ser válida si doffs>0. El productor debe usar el doffs de su geometría, no inferirlo del mapa.
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
Lite I07 como continuidad comprometida. Cada entrega lleva manifiesto, config, versión y prueba de recepción.

## Migración y recepción del schema 3

A04.1–A04.6 se integraron mediante PR #10, commit `d8a38bd`; recepción I00 por Bauty
pendiente. B27.1 se entrega en rama independiente `b/B27-instalacion` (PR #11).
La guía ejecutable de recepción está en [RECEPCION-A04](coordinacion/RECEPCION-A04.md).

- `Detection`: pasar `geometry_id` por nombre y propagar `calibration_id` desde el frame.
- `DepthResult`: pasar `doffs=geometry.doffs`; verificar con `check_depth_geometry` al recibir.
- Antes de aplicar máscaras, usar `check_detection_frame` sobre su imagen de referencia.
- Si detector y depth tienen resoluciones diferentes, transformar la máscara explícitamente;
  los validadores no hacen resize ni warp silencioso. La geometría del depth se valida aparte.
- Regenerar geometry_id a partir de los parámetros: se eliminó el redondeo a 1e-6 que podía
  asignar igual ID a valores diferentes. El hash no sustituye calibration_id ni es una métrica.
- Datos schema 2 no se convierten cambiando solo el número: reconstruir desde parámetros e
  imágenes originales, completar contexto y volver a validar. Fallar ante datos ambiguos.

Los arrays se copian a almacenamiento de solo lectura al construir el mensaje. El emisor no
debe modificarlos concurrentemente durante esa construcción; después puede reutilizar su
buffer. El consumidor debe hacer una copia explícita si una librería necesita modificar datos.
Esto tiene coste de memoria/copia: medir en B11/B21 antes de optimizar con buffers compartidos.
No se promete rendimiento ni seguridad frente a código nativo que ignore flags de NumPy.

`from_projections` soporta proyecciones canónicas rectificadas horizontales, origen en cámara
izquierda y baseline positivo. Rechaza estéreo vertical, ojos invertidos y matrices no canónicas;
no las interpreta como si cumplieran ese convenio. A07 debe validar la calibración física aparte.
