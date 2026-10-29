---
fecha: 2026-10-28 20:52
autor: Bauty Garcia
agente: claude-code
rama: a/A04-contratos
tarea: A04
---

# A04 contratos schema 2, interfaces, errores y geometría

## Qué se hizo

- A04 completa: el contrato de `docs/CONTRATOS.md` implementado en `src/visionx/shared/`, con
  `SCHEMA_VERSION = 2`. Dos partes: A04.1 (mensajes, interfaces, errores, relojes) y A04.2
  (geometría).
- Todos los mensajes llevan identidad `(session_id, frame_id)` (FrameKey), son inmutables y se
  validan al crearse: dtype, forma, NaN/ceros dentro de la máscara, b > 0, rangos y esquema.
- StereoFrame: `received_ns` obligatorio; `capture_ns` opcional con su `capture_clock`;
  `replay_original_ns` para replay; un par rectificado exige `calibration_id` y `geometry_id`.
- DepthResult: `geometry_id`, `status` (valid/partial/unmeasurable) y `reason` obligatorio si no
  es valid. Máscara vacía <=> unmeasurable.
- Detection: `model_id`, `image_size` (ancho, alto) de la imagen de referencia, cajas float32
  xyxy, scores float32 en [0, 1], máscaras N x H x W bool; tuplas en vez de listas.
- SpatialObject: separa `detector_score` de la calidad de profundidad (`valid_fraction`,
  `z_spread_m`); `z_m` None si no se midió; no se puede elegir SPEAK_METERS sin `z_m`.
- Command y AudioEvent: `deadline_ns` y `frame` (FrameKey) opcionales.
- Chequeos del consumidor: `check_schema`, `check_same_frame`, `check_geometry`,
  `check_not_expired(msg, now)` con `now` del reloj en uso.
- Interfaces (Protocols): FrameSource, DepthEstimator, Detector, SpatialEstimator, AudioSink.
- Relojes: MonotonicClock para vivo y ManualClock para replay y tests.
- Geometría (`geometry.py`): StereoGeometry inmutable (fx, fy, cx, cy, baseline, doffs) con
  `geometry_id` derivado de los parámetros; `from_projections(P1, P2)` desde cv2.stereoRectify;
  `disparity_to_depth` / `depth_to_disparity` (mapas) y `depth_at` / `disparity_at` (valores);
  `pixel_to_angles`; `resized` y `cropped`; `resize_mask` y `resize_disparity`.

## Archivos cambiados

- src/visionx/shared/{contracts.py, interfaces.py, errors.py, clock.py, geometry.py, _validate.py}
- tests/{test_contracts.py, test_interfaces.py, test_geometry.py}
- docs/CONTRATOS.md (sección "Estado de la implementación"), docs/coordinacion/A.md (A04 en curso)

## Decisiones tomadas (y por qué)

- **Fallos como excepciones, no como estados.** Cámara rota: SourceError. Modelo roto:
  EstimatorError. Así "cero objetos" y "no medible" nunca se confunden con un fallo.
- **El esquema se valida al construir.** No hay datos guardados con schema 1, así que no hace
  falta migración; un mensaje de otra versión da SchemaMismatch.
- **Mensajes inmutables** (`frozen`): nadie modifica un frame que ya usó otro módulo. Los arrays
  internos no se congelan, para no tocar buffers de la cámara.
- **Sin probabilidad conjunta** en SpatialObject: `z_spread_m` (dispersión robusta de Z dentro de
  la máscara) es medible ya; la política de confianza se calibra en A19.
- `check_same_frame` compara sesión y frame; la geometría se verifica aparte con
  `check_geometry`, porque las máscaras (1080p) y la profundidad (720p) tienen geometrías distintas.
- **Z = fx·B / (d + doffs)** con doffs = cx_der - cx_izq, la misma convención que Middlebury; en la
  ELP rectificada con centros alineados doffs = 0. Disparidad <= 0 o NaN: no medible (NaN y máscara
  falsa), nunca 0 ni infinito metros.
- **Centros de píxel alineados al cambiar de tamaño**: x' = (x + 0.5)·s - 0.5, igual que
  cv2.resize. Escalar cx solo por s corre medio píxel y sesga los ángulos.
- **Mapas y máscaras por vecino más cercano** (`INTER_NEAREST_EXACT`, que respeta centros; el
  `INTER_NEAREST` común se corre medio píxel). Interpolar disparidad en el borde de un objeto
  inventa distancias intermedias que no existen.
- La disparidad escala solo con el ancho; doffs también. Recortar no cambia focal ni disparidad.

## Cómo probarlo

```text
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked pytest
```

138 tests aprobados en macOS. Entre ellos:
- M0: ida y vuelta d -> Z -> d con error relativo <= 1e-5 en 0,5-3 m (con y sin doffs);
- un punto 3D proyectado con el modelo pinhole recupera su Z, también desde P1/P2 de OpenCV;
- el mismo punto a 1080p y a 720p tiene la misma Z y los mismos ángulos (y lo mismo al recortar);
- un mapa con un borde nítido, achicado, solo tiene los dos valores originales escalados;
- más de 70 entradas adversas rechazadas y un pipeline de fakes hasta el fin de la grabación.

## Pendiente / próximo paso

- Integrar A04 a main y marcarla hecha en A.md.
- A05: FakeDepth sobre estas interfaces, usando StereoGeometry para pasar de metros a disparidad.
- Los valores reales de la ELP (fx, B) salen de la calibración de B09; acá solo hay valores
  sintéticos de prueba.

## Avisos para el otro

- **Rompe el schema 1** (no había otro código que lo usara). Para B02: `StereoFrame(session_id,
  frame_id, left, right, received_ns, ...)`; en replay, `received_ns` es el reloj de la
  reproducción y `replay_original_ns` el tiempo grabado.
- Para B04: FakeDetector implementa `Detector` (`model_id`, `predict`, `close`); cero objetos es
  `Detection` con N = 0; `classes` y `track_ids` son tuplas. FakeAudio implementa `AudioSink` y
  usa `check_not_expired(evento, clock.now_ns())` con un `ManualClock` en replay.
- Para B09/B10: con P1 y P2 de cv2.stereoRectify, `StereoGeometry.from_projections(P1, P2, w, h)`
  da la geometría y su `geometry_id`, que va en StereoFrame.geometry_id.
- Para pasar máscaras de detección de 1080p a 720p: `resize_mask(masks, 1280, 720)`.
- `shared/` queda libre al integrar A04.
