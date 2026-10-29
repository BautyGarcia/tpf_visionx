# Persona A: Bauty - datos, profundidad y evaluación

Consignas para ejecutar con IA. Leer [plan](PLAN.md), [contratos](../CONTRATOS.md),
[métricas](METRICAS.md) y [flujo](FLUJO.md). IDs originales conservados; elegir tarea por
dependencias/etapa. Una ficha puede originar varios PR pequeños.
**Rutas:** depth/, datasets/, experiments/ y tests/configs/scripts asociados; A04 reserva shared/.
depth/ está en src/visionx/; datasets/ y experiments/ en la raíz. Lo compartido requiere reserva de editor, no aprobación.
Cada entrega registra comando ejecutado, run/commit, config, artefacto/hash, n/unidad y límites.
No tildar mediciones físicas no ejecutadas. M0-M12 se definen en METRICAS.md.

## A01 - Dataset de entrenamiento y manifiesto

- [ ] A01 · estado: pendiente · rama: —
- **Etapa / depende:** E0 / C03.
- **Hacer:** Descargar InStereo2K desde origen verificable; auditar formato/escala GT y crear splits por escena sin alterar el test oficial para ajustar hiperparámetros.
- **Entregar y medir:** Manifiesto con hashes/licencia, 10 muestras visualizadas y lector de muestra. Reportar tamaños, escenas, inválidos y escala; M4.
- **Traspaso:** I03; A03/A09 consumen; entregar fixture pequeña a B.

## A02 - Métricas base y regiones

- [ ] A02 · estado: pendiente · rama: —
- **Etapa / depende:** E0 / C03.
- **Hacer:** Implementar EPE/bad-2/validez y MAE métrico donde haya calibración. Fijar soporte, agregación y definición de regiones; no inventar máscaras de oclusión.
- **Entregar y medir:** Tests sintéticos con error conocido; CSV por escena y zona, n/unidad/exclusiones. M0/M4. AUSE se completa en A16.
- **Traspaso:** I03; B12/B20 consumen el formato de reporte.

## A03 - SGBM público y chequeo izquierda-derecha

- [ ] A03 · estado: pendiente · rama: —
- **Etapa / depende:** E2 / A01, A02, A04.
- **Hacer:** Implementar DepthEstimator SGBM para pares rectificados; escala OpenCV, signo L/R, inválidos y parámetros en YAML. No incluir WLS aquí.
- **Entregar y medir:** Salida DepthResult más ejemplo de inferencia; EPE/bad-2/validez y latencia piloto, M4/M9. Sin cámara obligatoria.
- **Traspaso:** I02; B08/B12 incorporan el proveedor mediante config.

## A04 - Interfaces y geometría compartidas

- [ ] A04 · estado: por integrar · rama: a/A04-contratos
- **Etapa / depende:** E0 / C03.
- **Hacer:** Implementar especificación de docs/CONTRATOS.md en shared/ con reserva de edición. Tipos/IDs/relojes, APIs públicas, errores y migración de schema; B aporta requisitos por comunicación directa.
- **Entregar y medir:** Tests de dtype/shapes/positividad, mezcla de frames y resize/doffs. M0; rechazo de entradas adversas. No crear un contrato paralelo.
- **Traspaso:** I00; B02/B04 consumen contrato integrado antes de escribir adaptadores.

## A05 - FakeDepth y fixtures deterministas

- [ ] A05 · estado: pendiente · rama: —
- **Etapa / depende:** E0 / A04.
- **Hacer:** Construir planos a 1/2 m, zonas inválidas e incertidumbre conocida; mismos mensajes/API que estimadores reales. Señalar origen simulado.
- **Entregar y medir:** 20 frames reproducibles; prueba d->Z->d y estado no medible, M0. Config mínima sin GPU/datasets grandes.
- **Traspaso:** I00; B conecta FakeDepth a replay y audio.

## A06 - Ubicación por máscara con profundidad simulada

- [ ] A06 · estado: pendiente · rama: —
- **Etapa / depende:** E1 / A05.
- **Hacer:** Implementar SpatialEstimator en depth/spatial/: transformación de máscara, profundidad robusta, ángulos y no medición. Usar cámara virtual documentada para fixtures.
- **Entregar y medir:** Casos izquierda/centro/derecha, duplicados, vacíos y mezcla de geometrías. M0/M1; ninguna distancia falsa con datos inválidos.
- **Traspaso:** I01; B05/B07 consumen SpatialObject.

## A07 - Evaluador independiente de calibración

- [ ] A07 · estado: pendiente · rama: —
- **Etapa / depende:** E2 / A04, B09.
- **Hacer:** Validar YAML/rectificación sin reutilizar solo el error del solver. Medir error vertical, escala y distancia al tablero con referencia externa; probar resize a 720p.
- **Entregar y medir:** Reporte por ojo/sesión, mediana/P95 y sesgo, M3/M7. Identificar qué GT depende del mismo calibrado.
- **Traspaso:** I02; B10 usa el evaluador sobre sesiones reservadas.

## A08 - Baselines B1 y B2/WLS

- [ ] A08 · estado: pendiente · rama: —
- **Etapa / depende:** E3 / A03.
- **Hacer:** Añadir filtros/consistencia y WLS con misma API de SGBM. Fijar parámetros usando desarrollo, no test.
- **Entregar y medir:** Tabla B0/B1/B2 EPE, bad-2, cobertura y tiempo; misma resolución/máscaras, M4/M9.
- **Traspaso:** I03; B12 muestra los métodos mediante configuración.

## A09 - Adaptadores externos y splits congelados

- [ ] A09 · estado: pendiente · rama: —
- **Etapa / depende:** E3 / A01, A02.
- **Hacer:** Preparar Middlebury/ETH3D y ELP recibido; verificar focal/baseline/doffs, GT y particiones por escena/sesión. Reservar test externo y físico.
- **Entregar y medir:** Manifiestos/hash, auditoría de 10 muestras/adaptador y 0 fuga, M4. Sin usar test para elegir modelo.
- **Traspaso:** I03; B20 aplica las mismas convenciones y GT.

## A10 - Monocular congelado y alineación B3

- [ ] A10 · estado: pendiente · rama: —
- **Etapa / depende:** E3 / A03, A04.
- **Hacer:** Integrar Depth Anything V2 Small relativo con pesos/origen/licencia; alinear con anclas fiables SGBM sin GT. Fallo de ajuste produce status/fallback explícito.
- **Entregar y medir:** Config/pesos referenciados; n anclas, inliers, residuo P50/P95, EPE/cobertura y tiempo M4/M9. Probar pocas anclas y ajuste degenerado.
- **Traspaso:** I03; B12 consume mapas original/alineado y calidad.

## A11 - Regla fija B4

- [ ] A11 · estado: pendiente · rama: —
- **Etapa / depende:** E3 / A08, A10.
- **Hacer:** Usar estéreo donde cumple criterio fijo y monocular alineado en resto; definir comportamiento si falla B3. Congelar umbrales en desarrollo.
- **Entregar y medir:** B0-B4 sobre mismos frames, EPE/bad-2/cobertura por zona y latencia, M4/M9; sin selección manual de escenas ganadoras.
- **Traspaso:** I03; B puede ejecutar demo real antes de Fusion.

## A12 - Preprocesamiento y caché de 10 canales

- [ ] A12 · estado: pendiente · rama: —
- **Etapa / depende:** E3 / A09, A11.
- **Hacer:** Construir RGB(3), dSGBM, validez, L/R, fotométrico, gradiente, dMono y diferencia. Definir normalización, recortes y hashes que invalidan cache.
- **Entregar y medir:** 10 muestras con canales visualizados, rangos/shapes/unidades; probar resize/crop y exclusión GT inválido. M0/M4.
- **Traspaso:** I03; A14/A15 consumen; B13 debe reutilizar preprocesamiento público.

## A13 - Presupuesto y piloto de cómputo

- [ ] A13 · estado: pendiente · rama: —
- **Etapa / depende:** E3 / A10.
- **Hacer:** Probar imports/inferencia MPS/CPU y disponibilidad de nube; fijar backend, almacenamiento, checkpoints y límite de gasto/tiempo. No contratar recursos sin decisión de los humanos.
- **Entregar y medir:** Benchmark piloto M9 y plan de corridas/configuración. Estimar entrenamiento con piloto real de A15 antes de lanzar corrida completa.
- **Traspaso:** I03; B conoce hardware objetivo y presupuesto de inferencia.

## A14 - Fusion F0 y smoke de entrenamiento

- [ ] A14 · estado: pendiente · rama: —
- **Etapa / depende:** E4 / A12, A13.
- **Hacer:** Implementar U-Net residual con cabezas delta/b, NLL Laplace y máscara GT. Inicializar solo cabeza residual a cero; prueba de overfit antes de entrenamiento largo.
- **Entregar y medir:** Parámetros reales, RAM/VRAM, gradientes/pérdida finitos, igualdad inicial B4 y overfit 8-16 recortes, M5.
- **Traspaso:** I04; checkpoint de prueba permite avanzar B13.

## A15 - Entrenamiento y selección por validación

- [ ] A15 · estado: pendiente · rama: —
- **Etapa / depende:** E4 / A14, C07.
- **Hacer:** Correr piloto y luego entrenamiento presupuestado, guardar/reanudar checkpoints y curvas; seleccionar por criterio congelado en val. Test no elige época.
- **Entregar y medir:** Config, seed, split/hash, curvas train/val por época y métricas M5/M6; coste/tiempo real. Tres seeds principal si alcanza, documentar si no.
- **Traspaso:** I04; entregar candidato a A18/B13 sin esperar todas las ablaciones.

## A16 - Evaluación de incertidumbre

- [ ] A16 · estado: pendiente · rama: —
- **Etapa / depende:** E4 / A02, A15.
- **Hacer:** Implementar NLL, AUSE, riesgo-cobertura e intervalos con definición fija; comparar con L/R y fotométrico. Separar ordenar errores de calibrar intervalos.
- **Entregar y medir:** Tests numéricos de intervalos/oracle, curvas por rango y soporte, M6. Umbrales se eligen en val.
- **Traspaso:** I06; A19 usa resultados para política de objeto.

## A17 - Ablaciones mínimas

- [ ] A17 · estado: pendiente · rama: —
- **Etapa / depende:** E4 / A15.
- **Hacer:** Comparar sin monocular, sin canales clásicos de confianza y sin incertidumbre/pérdida NLL. Sin monocular implica quitarlo de canales y base para evitar fuga residual.
- **Entregar y medir:** Mismo split/presupuesto; EPE/bad-2/validez/latencia y seeds, M4-M6/M9. Registrar variantes negativas.
- **Traspaso:** I06; A22 incorpora tabla reproducible.

## A18 - Paquete de modelo y adaptador de inferencia

- [ ] A18 · estado: pendiente · rama: —
- **Etapa / depende:** E4 / A15.
- **Hacer:** Publicar versión inmutable de checkpoint + model card + preprocesamiento + config y hash. Mantener misma API que B4 y cargar sin notebook.
- **Entregar y medir:** Recepción offline reproducible, comparación de salida con tolerancia por backend/precisión; M5/M9. Manifiesto ARTEFACTOS.
- **Traspaso:** I04; B13 descarga, verifica hash y ejecuta el modelo.

## A19 - Confianza y abstención por objeto

- [ ] A19 · estado: pendiente · rama: —
- **Etapa / depende:** E5 / A06, A16, I04.
- **Hacer:** Calibrar política de metros/dirección/reencuadre/abstención en ELP de desarrollo; definir cobertura mínima, rango y redondeo. Intervalos de píxel no se transfieren automáticamente a objeto.
- **Entregar y medir:** MAE/sesgo/cobertura por rango y curva riesgo-cobertura, M6/M7. Congelar thresholds antes del test físico.
- **Traspaso:** I05; B16/B18 consumen política y objetos medidos.

## A20 - Test final y generalización

- [ ] A20 · estado: pendiente · rama: —
- **Etapa / depende:** E6 / A09, A16, A17, A24, I05.
- **Hacer:** Congelar commit/modelo/protocolo y ejecutar tests reservados para B0-B4/Fusion/ablaciones y comparador. No elegir arquitectura ni thresholds con resultados finales.
- **Entregar y medir:** M4/M6/M9 por escena/zona; diferencias pareadas e IC95% por escenas; al menos 2 casos donde Fusion empeora.
- **Traspaso:** I06; A22 y B26 usan CSV con limitaciones, no números de papers.

## A21 - Evaluación física y abstención

- [ ] A21 · estado: pendiente · rama: —
- **Etapa / depende:** E6 / A19, B20.
- **Hacer:** Procesar capturas físicas reservadas con todos los métodos y misma definición Z. Comparar error con y sin abstención a igual cobertura.
- **Entregar y medir:** M7: 90 medidas/método, MAE/sesgo/P95 por rango, cobertura/abstención; separar error detector y depth con ROI manual.
- **Traspaso:** I06; B recibe análisis de sus capturas y casos fallidos.

## A22 - Tablas y figuras reproducibles

- [ ] A22 · estado: pendiente · rama: —
- **Etapa / depende:** E6 / A20, A21, B21.
- **Hacer:** Generar reportes desde CSV/manifiestos; mapa/escala coherente y selecciones de ejemplos documentadas. Distinguir medias por escena y por píxel.
- **Entregar y medir:** Un comando reproduce tablas; cifras trazables a run/config/commit. M12; tabla precisión/cobertura/latencia y fallos.
- **Traspaso:** I06; B26 consume figuras sin copiar valores a mano.

## A23 - Informe científico y reproducción de B

- [ ] A23 · estado: pendiente · rama: —
- **Etapa / depende:** E8 / A22, I06.
- **Hacer:** Escribir método/datos/entrenamiento/resultados/discusión y bibliografía verificada; ejecutar instalación/demo de B desde instrucciones. Confirmar formato con C06.
- **Entregar y medir:** Texto para informe <=8 páginas total, figuras y lista de fallos de reproducción, M12. Explicar resultados negativos si existen.
- **Traspaso:** I08; B26 integra informe y devuelve correcciones prácticas.

## A24 - Comparador neuronal externo prioritario

- [ ] A24 · estado: pendiente · rama: —
- **Etapa / depende:** E6 / A09, A13.
- **Hacer:** Reproducir al menos un modelo externo viable en nube/backend compatible, verificando repo/pesos/licencia. Limitar instalación; si no es viable, documentar intento y decisión antes del test.
- **Entregar y medir:** M4/M9 en mismos frames y hardware cuando se comparan tiempos; versión/config/coste y límites. Más modelos son opcionales.
- **Traspaso:** I06; no sustituir baseline B4 ni usar tablas de papers como medición propia.

## A25 - Variante Fusion-FFS (condicionada)

- [ ] A25 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / A24, I06.
- **Hacer:** Solo si el comparador es viable y queda presupuesto: sustituir entrada estéreo por FFS, recalcular confianza y entrenar/evaluar sin alterar test previo.
- **Entregar y medir:** M4-M6/M9 frente a FFS solo; hipótesis, presupuesto y resultado. Si se omite: estado no aplica con motivo.
- **Traspaso:** I07; no cambia el proveedor de demo sin recepción B13.

## A26 - Pseudoetiquetas teacher (condicionada)

- [ ] A26 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / A19, I06.
- **Hacer:** Si teacher demuestra utilidad y la latencia lo exige, generar pseudoetiquetas en escenas ELP de entrenamiento; filtrar por incertidumbre congelada y evitar test.
- **Entregar y medir:** Manifiesto/hash, tasa de aceptación por escena y muestras visuales. No declarar las pseudoetiquetas GT independiente.
- **Traspaso:** I07; A27 consume; B proporciona grabaciones fuera de test.

## A27 - Lite destilada (condicionada)

- [ ] A27 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / A26.
- **Hacer:** Entrenar Lite sin monocular en inferencia; comparar con la misma red sin destilar. Calibrar incertidumbre aparte y mantener API.
- **Entregar y medir:** M4-M6/M9/M11 a misma cobertura. Contar pipeline completo incluido SGBM; publicar paquete como A18.
- **Traspaso:** I07; B13/B25 prueban si mejora demo. No aplica si no aporta.

## A28 - Decisión de proveedor y alerta (condicionada)

- [ ] A28 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / I06; A27 si se elige Lite, B25 si se elige Wi-Fi.
- **Hacer:** Elegir B4/Fusion/Lite por precisión-cobertura-latencia de B21 por USB y B25 si hay Wi-Fi; si se incluye alerta central, especificar criterio de obstáculo/piso e incertidumbre con B. No exigir Lite ni Pi para probar alerta por USB.
- **Entregar y medir:** Tabla M11 y política de proveedor; alerta: obstáculos detectados, falsas alarmas y distancia de aviso en recorrido controlado x10. Sin promesa de navegación.
- **Traspaso:** I07; B configura proveedor; alerta solo tras prueba conjunta.

## A29 - Congelar artefactos científicos

- [ ] A29 · estado: pendiente · rama: —
- **Etapa / depende:** E8 / A23, I07.
- **Hacer:** Publicar pesos/configs/splits/reportes finales, hashes y model card; resolver reproducción por B y preparar defensa de geometría/modelo/incertidumbre.
- **Entregar y medir:** M12, 100% cifras del resumen trazables; paquete de respaldo disponible offline. I07 puede cerrar como no aplica.
- **Traspaso:** I08; B empaqueta release sin depender de rutas privadas.

