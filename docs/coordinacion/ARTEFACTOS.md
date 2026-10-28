# Traspaso de software, grabaciones y resultados

Código/configs/scripts por Git. Datasets, pares, calibraciones de sesión y pesos por un almacén
compartido elegido en **C05**. Hasta elegirlo, no afirmar que la entrega pesada está disponible.
Opciones: carpeta Drive compartida o almacenamiento equivalente accesible a ambos; no se instala
una herramienta adicional por defecto. No compartir claves ni una ruta C:/Users/... como ubicación.

## Manifiesto de entrega

Productor crea `docs/artefactos/<ID>-<nombre>.yaml` (directorio a crear con la primera entrega):

```yaml
artifact_id: A18-fusion-candidato-01
producer: A
task_id: A18
integration_id: I04
location: "POR_COMPLETAR: enlace/ruta compartida verificable"
sha256: "POR_COMPLETAR"
code_commit: "POR_COMPLETAR"
schema_version: 1  # versión real del artefacto, no copiar este ejemplo sin verificar
config_path: configs/experiments/fusion.yaml
dataset_split_hash: "POR_COMPLETAR"
calibration_id: null
format: "checkpoint + metadata; especificar archivos, shapes y unidades"
reproduce: "comando público implementado al cerrar A18"
expected: "IDs/shape/tolerancia y métrica de recepción"
```

Es una plantilla, no un artefacto publicado. Si son varios archivos, manifiesto de nombres/hash
por archivo, bytes y versión. Grabar la configuración completa y licencia/origen del modelo/datos.
Calibración añade modo físico, tamaño, foco, unidades, matrices y métricas de validación.
Replay añade sesión, frame_id, ruta de par, tiempo original y geometría; no mezclar archivos
independientes que puedan desincronizar ojos. Modelo añade orden/normalización de canales,
arquitectura, backend/precisión y preprocesamiento. Inmutable por versión; no reemplazar pesos
manteniendo el mismo ID. Paths de descarga se resuelven mediante config local.

## Recepción

Consumidor: obtener versión, verificar hash, correr fixture/comando y comparar salida/tolerancia.
Registrar en Ixx: consumidor, commit, artifact_id/hash, comando, resultado y fecha. Mensaje mínimo
por WhatsApp: **A18 -> B13 / I04 / commit / manifiesto / comando / resultado esperado**.
No adjuntar videos/pesos al commit. Resultados pequeños (CSV/figuras reproducibles) en experiments/;
grandes en almacén con referencia. Fixtures sintéticas <1 MB en tests/fixtures/.
