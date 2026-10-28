# Integraciones: cuándo y cómo combinar el trabajo

**Son verificaciones técnicas, no aprobaciones de PR del compañero.** El productor hace merge
de cambios compatibles cuando pasan checks. El consumidor actualiza main en su rama, obtiene
artefacto/hash y ejecuta recepción. Marcar la tarea productora por integrar hasta esa recepción.
Registrar una línea por entrega; el coordinador del hito mantiene este archivo para evitar choque.

Ficha de recepción mínima: `ID origen -> consumidor | commit | artifact_id/hash o fixture |
comando ejecutado | resultado/métrica | fecha`. Un vídeo bonito no reemplaza los datos del run.
No ejecutar comandos de ejemplo no implementados: las tareas entregan su CLI/instrucción real.

## I00 - Base compatible sin hardware

- [ ] I00 · estado: pendiente · coordinador: B
- **Requiere:** C03, C04, A04, A05, B02, B04 implementados e integrados.
- **B -> A:** ReplaySource, fixture y metadatos; A ejecuta FakeDepth sobre sus 20 pares.
- **A -> B:** API/validadores y FakeDepth; B los conecta a detector/audio falsos.
- **Recepción:** mismo resultado/IDs en Windows/Mac; M0 completo; EOS, datos inválidos y schema
  incompatible probados. Sin cámara, GPU, API ni dataset grande. A01/A02 pueden seguir en paralelo.
- **Orden de merge:** contrato A04; fuentes/fakes independientes; conexión y prueba en ambas PCs.
- **Cierre:** registrar salidas A/B y tag i00 cuando se autorice publicarlo.
- **Evidencia / recepción:** pendiente.

## I01 - Primera entrega: replay, objeto y audio

- [ ] I01 · estado: pendiente · coordinador: B
- **Requiere:** I00, A06, B05-B07.
  La prueba específica de AirPods no bloquea si altavoz/mic alternativo funcionan.
- **A -> B:** SpatialEstimator/política inicial con profundidad simulada.
- **B -> A:** detector real, controlador y preset de replay con objetos/escenarios.
- **Recepción:** A corre su módulo en aplicación; B verifica posiciones/distancia esperadas.
  M1: 24/24 escenarios y cero audio vencido. Ejecutar fakes en ambas PCs y YOLO/audio real en
  equipo disponible; no confundir prueba simulada con rendimiento de detección real.
- **Orden de merge:** A06; B05/B06; B07 conecta todo. No esperar cámara/calibración para integrar.
- **Cierre:** demo de 60-120 s y preset reproducible; etiqueta SIMULADO explícita.
- **Evidencia / recepción:** pendiente.

## I02 - Cámara/calibración y distancia clásica

- [ ] I02 · estado: pendiente · coordinador: B
- **Requiere:** I01, A03, A07, B01, B08-B10; C05 para artefactos reales.
- **B -> A:** par original, rectificado 1080/720p, YAML y sesiones de validación/medidas externas.
- **A -> B:** SGBM/DepthResult y evaluador geométrico, sin copiar notebooks.
- **Recepción:** A procesa grabación sin ELP; B ejecuta SGBM en USB y replay del mismo par.
  M2/M3 y piloto M7; frame/calibración/geometría iguales. Sesgo de escala inexplicado bloquea.
- **Orden de merge:** source B08 y YAML B09; A07 valida, B10 completa; A03 se conecta a aplicación.
- **Cierre:** calibration_id fijado por validación, preset e informe con metas no alcanzadas visibles.
- **Evidencia / recepción:** pendiente.

## I03 - B4 y datos listos para entrenar

- [ ] I03 · estado: pendiente · coordinador: B
- **Requiere:** I02, A01/A02, A08-A13, B11/B12, C05/C07.
- **A -> B:** B0-B4, monocular/alineación y CSV por escena; configuración de preprocesamiento.
- **B -> A:** 30-50 escenas ELP con GT delimitado, splits y metadatos/medidas externas.
- **Recepción:** B muestra comparativa mismo frame/color/unidad; A carga set ELP sin rutas privadas.
  M4/M9; 0 fuga/escala ambigua; protocolo/splits congelados antes de entrenamiento.
- **Orden de merge:** adaptadores/métricas, baselines, observabilidad y dashboard, freeze C07.
- **Cierre:** B4 funciona como demo independiente; config/manifest de entrenamiento reproducible.
- **Evidencia / recepción:** pendiente.

## I04 - Fusion dentro de la aplicación

- [ ] I04 · estado: pendiente · coordinador: B
- **Requiere:** I03, A14/A15/A18, B13.
- **En paralelo:** A16/A17 completan la evaluación científica para I06; no bloquean este hito.
- **A -> B:** checkpoint inmutable, config, model card, orden de canales, hash y adaptador.
- **B -> A:** logs de carga/inferencia en despliegue y fixture de discrepancia si falla.
- **Recepción:** cambiar B4 por Fusion mediante config, obtener misma salida que offline dentro
  de tolerancia declarada, M5/M9. Primero pesos de prueba, después candidato entrenado.
- **Orden de merge:** formato/loader; adaptador y entrenamiento; referencia a pesos; integración B13.
- **Cierre:** CNN funcional y trazable; NO exige todavía superioridad científica a B4.
- **Evidencia / recepción:** pendiente.

## I05 - Cuatro modos USB estables

- [ ] I05 · estado: pendiente · coordinador: B
- **Requiere:** I04, A19, B03, B14-B19. B03 puede cerrar con fallback validado si AirPods falla.
- **A -> B:** política por objeto, umbrales de desarrollo y motivos de abstención.
- **B -> A:** replay de buscar/guiar, distancia, leer y describir con eventos/mediciones.
- **Recepción:** A ejecuta replay sin hardware; B prueba audio/voz en Mac y casos de fallo.
  M8/M10; cero respuestas canceladas/guía vieja. Descripción funciona con plantilla sin internet;
  probar VLM real aparte. GT y política de test permanecen reservados.
- **Orden de merge:** A19; tracking/voz; modos; OCR/VLM independientes; regresión B19.
- **Cierre:** preset USB estable y logs por request; estas funciones no dependen de Pi/Lite.
- **Evidencia / recepción:** pendiente.

## I06 - Resultados finales conjuntos

- [ ] I06 · estado: pendiente · coordinador: A
- **Requiere:** I05, A16/A17/A20-A22/A24, B20/B21, protocolo C07.
- **B -> A:** banco físico reservado, anotaciones y métricas de interacción/latencia.
- **A -> B:** errores/intervalos/cobertura por método y figuras/scripts reproducibles.
- **Recepción:** ambos regeneran un subconjunto de tablas desde mismos inputs/hashes. M4/M6-M10,
  diferencias pareadas por escena y fallos; comparar tiempos solo con hardware controlado.
- **Orden de merge:** protocolo final ya integrado; capturas/GT; evaluaciones; reportes.
- **Cierre:** resultado positivo/negativo de hipótesis declarado; no ajustar contra test para ganar.
- **Evidencia / recepción:** pendiente.

## I07 - Extensiones o decisión de no hacerlas

- [ ] I07 · estado: pendiente · coordinador: B
- **Requiere:** I06; elegir por separado Lite, Fusion-FFS y wearable con presupuesto remanente.
- **A -> B:** Lite/config/hash o decisión de mantener Fusion a pedido. **B -> A:** stream medido y
  capturas de entrenamiento ELP fuera de test, si se necesitan pseudoetiquetas.
- **Recepción:** A25-A28/B22-B25/B28 solo para extensiones elegidas. M11 y regresión I05; presets
  experimentales separados. Streaming puede avanzar sin Lite; Lite puede existir sin wearable.
  Si se elige alerta, B28 implementa la política de A28 y se prueba también por USB.
- **Orden de merge:** contrato compatible; prototipos; modelos/hardware; benchmark USB/Wi-Fi.
- **Cierre:** lista explícita hecho/no aplica con razón. Si se omite todo, marcar I07 no aplica;
  no bloquear I08. No atribuir implementación a una extensión descartada.
- **Evidencia / recepción:** pendiente.

## I08 - Release y defensa

- [ ] I08 · estado: pendiente · coordinador: B
- **Requiere:** I06, I07 resuelto (hecho/no aplica), A23/A29, B26/B27, C06/C08.
- **A -> B:** pesos/splits/tablas definitivos. **B -> A:** ejecutable/configs/operación y respaldo.
- **Recepción:** A instala/demo B; B reproduce informe A. M12, 3 ensayos y 2/2 reproducciones;
  todas las cifras remiten a artefacto/config/commit. No depender de API en vivo para defensa.
- **Orden de merge:** release candidate, documentación, correcciones verificadas, release/tag
  v1.0-tpf cuando las personas autoricen publicación. Un cambio de predicción repite métricas afectadas.
- **Cierre:** código, datos referenciados, informe <=8 páginas, póster vertical A0/A1 y video;
  capacidad de ambos de explicar todo el sistema. Requisitos confirmados en C06.
- **Evidencia / recepción:** pendiente.
