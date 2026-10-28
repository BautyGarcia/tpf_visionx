# Persona B: Tomás - cámara, aplicación y hardware

Consignas para ejecutar con IA. Leer [plan](PLAN.md), [contratos](../CONTRATOS.md),
[métricas](METRICAS.md) y [flujo](FLUJO.md). IDs originales conservados; elegir tarea por
dependencias/etapa. Una ficha puede originar varios PR pequeños.
**Rutas:** camera/, calibration/, detection/, speech/, modes/, gui/, transport/, cli.py y tests/configs/scripts asociados.
Rutas abreviadas dentro de src/visionx/. Lo compartido requiere reserva de editor, no aprobación.
Cada entrega registra comando ejecutado, run/commit, config, artefacto/hash, n/unidad y límites.
No tildar mediciones físicas no ejecutadas. M0-M12 se definen en METRICAS.md.

## B01 - Modos reales de la ELP

- [ ] B01 · estado: pendiente · rama: —
- **Etapa / depende:** E2 / C03.
- **Hacer:** Enumerar resolución/formato/FPS por backend Windows; comparar 1080p SBS y alternativa 720p. Puede adelantarse mientras A trabaja; si no hay ELP, no dar por medida otra cámara.
- **Entregar y medir:** CSV solicitado/observado, M2 en modos finalistas; elegir modo con evidencia y limitaciones de timestamp/sincronía.
- **Traspaso:** I02; A recibe modo/pares para geometría.

## B02 - Separación SBS y replay portable

- [ ] B02 · estado: pendiente · rama: —
- **Etapa / depende:** E0 / A04.
- **Hacer:** Implementar FrameSource/read/close, separar ojos sin invertirlos y replay con EOS/timing/IDs. Empezar con fixture sintética, no esperar B01; conservar futuro formato de grabación.
- **Entregar y medir:** 20 pares, tests M0 y manifiesto de replay; mismo input produce mismos eventos. Comando público de replay básico.
- **Traspaso:** I00; A ejecuta inferencia con tu ReplaySource.

## B03 - Prueba de audio y micrófono

- [ ] B03 · estado: pendiente · rama: —
- **Etapa / depende:** E0 / C03.
- **Hacer:** Probar AirPods/altavoz con reproducción, micrófono, simultaneidad, cancelación y reconexión. Windows temprano; repetir en Mac de demo. Si no hay AirPods, usar alternativa y dejar prueba específica pendiente.
- **Entregar y medir:** Matriz dispositivo/SO y n de pruebas, cortes/latencia/perfil y fallback elegido. No bloquea I01 si altavoz funciona.
- **Traspaso:** I05; acordar entrada/salida de demo antes de cuatro modos.

## B04 - FakeDetector y FakeAudio

- [ ] B04 · estado: pendiente · rama: —
- **Etapa / depende:** E0 / A04.
- **Hacer:** Implementar las mismas interfaces públicas que reales, detecciones guionadas y grabación de eventos de audio. Fixtures de ausencia, duplicado, pérdida y datos viejos.
- **Entregar y medir:** M0/M1 con resultado esperado en archivo; CI sin modelos, cámara ni red.
- **Traspaso:** I00; A usa detecciones sintéticas para SpatialEstimator.

## B05 - Controlador mínimo y audio real

- [ ] B05 · estado: pendiente · rama: —
- **Etapa / depende:** E1 / A06, B02, B04.
- **Hacer:** Conectar Espera/Buscar/Encontrado/Cancelar con orden teclado/JSON, FakeDepth y detector intercambiable; bip/TTS local o audio grabado. Rechazar request viejo.
- **Entregar y medir:** M1 24/24, cancelación e inicio audible contrastado; comando único replay-demo. Rotular distancia SIMULADA.
- **Traspaso:** I01; A prueba su SpatialObject dentro del pipeline.

## B06 - YOLO con segmentación

- [ ] B06 · estado: pendiente · rama: —
- **Etapa / depende:** E1 / B02, B04.
- **Hacer:** Integrar detector/segmentador como adaptador, verificar pesos/licencia/clases soportadas y transformaciones de masks. Mantener fake para CI.
- **Entregar y medir:** >=100 frames de 3 clips anotados, precisión/recall IoU0,5 y máscara IoU; latencia M9. Fallo de modelo distinto de objeto ausente.
- **Traspaso:** I01; A recibe máscaras y geometría, no dependencias internas de YOLO.

## B07 - Dashboard y primera demo

- [ ] B07 · estado: pendiente · rama: —
- **Etapa / depende:** E1 / B05, B06.
- **Hacer:** Mostrar imagen/máscara/estado/proveedor/edad/dirección/distancia y eventos. Capturar demo replay 60-120 s con audio; simulado claramente marcado.
- **Entregar y medir:** M1 y comando reproducible sin GPU usando fakes; segunda ejecución con YOLO real. Videos grandes al almacén.
- **Traspaso:** I01; la otra PC reproduce mismo escenario y transición.

## B08 - Captura USB y grabación de pares

- [ ] B08 · estado: pendiente · rama: —
- **Etapa / depende:** E2 / B01, B02.
- **Hacer:** Implementar fuente USB y grabación atómica SBS/par con timestamps/metadatos. Exposición/foco/modo documentados, cierre/reconexión sin mezclar ojos.
- **Entregar y medir:** M2; USB y replay del mismo frame conservan identidad/geometría. Comandos públicos capture/record/replay documentados.
- **Traspaso:** I02; A procesa grabación sin tener la ELP.

## B09 - ChArUco y primera calibración

- [ ] B09 · estado: pendiente · rama: —
- **Etapa / depende:** E2 / B08.
- **Hacer:** Generar tablero con versión OpenCV usada, medir tamaño físico y fijar foco. Capturar calibración/validación separados; resolver mono/estéreo y rectificar.
- **Entregar y medir:** YAML K/D/R/T/R1/R2/P1/P2/Q, modo/unidades y reproyección. M3 primera sesión; manifiesto del artefacto.
- **Traspaso:** I02; A07 incorpora YAML y fotos reservadas para validar.

## B10 - Validación y estabilidad de calibración

- [ ] B10 · estado: pendiente · rama: —
- **Etapa / depende:** E2 / B09, A07.
- **Hacer:** Repetir sesiones objetivo, cubrir bordes/poses y registrar descartes; usar evaluador A07 y distancias externas. Elegir con validación, no test final.
- **Entregar y medir:** M3 por sesión y M7 piloto; explicar desviaciones. Sin corrección de metros por factor manual.
- **Traspaso:** I02; fijar calibration_id y entregar pares rectificados 1080/720p.

## B11 - Servicios, reloj y observabilidad

- [ ] B11 · estado: pendiente · rama: —
- **Etapa / depende:** E3 / I02.
- **Hacer:** Separar captura/detección/depth/audio con colas acotadas y último frame; medir cada módulo y request. Distancia congela frame; resultados tardíos se descartan.
- **Entregar y medir:** JSONL con frame/request/timestamps/status; M9 y sobrecarga controlada de 10 min sin cola creciente.
- **Traspaso:** I03; A entrega resultados a su ritmo sin bloquear bip/captura.

## B12 - Dashboard comparativo y banco ELP

- [ ] B12 · estado: pendiente · rama: —
- **Etapa / depende:** E3 / A08, A11, B10, B11.
- **Hacer:** Comparar B0-B4 en mismo frame/escala; mostrar fallos, alineación, validez y nube 3D por frame. Capturar 30-50 escenas ELP con GT solo donde existe y split por sesión.
- **Entregar y medir:** M4/M9, manifiestos/GT/medidas externas; no afirmar profundidad densa del fondo por tener tablero.
- **Traspaso:** I03; A09/A19 reciben capturas y metadatos; B consume B4.

## B13 - Carga de Fusion y paridad de inferencia

- [ ] B13 · estado: pendiente · rama: —
- **Etapa / depende:** E4 / A18, B12.
- **Hacer:** Obtener paquete/hash, cargar con mismo preprocesamiento de A y elegir proveedor por config. Mostrar fallo de pesos/esquema y fallback B4 explícito.
- **Entregar y medir:** M5/M9, salida offline vs app con tolerancia declarada; sin notebook ni copia de privados. Checkpoint de prueba permite adelantar loader.
- **Traspaso:** I04; registrar recepción del modelo y demo real.

## B14 - Seguimiento e identidad

- [ ] B14 · estado: pendiente · rama: —
- **Etapa / depende:** E5 / B06, B11.
- **Hacer:** Añadir seguimiento y elección entre objetos iguales; al perder objetivo suspender guía. No asumir identidad tras reaparición sin evidencia; huella visual extra si las pruebas lo justifican.
- **Entregar y medir:** 10 pérdidas/reapariciones; ID switches, tiempo de recuperación y falsos objetivos, M8.
- **Traspaso:** I05; A recibe máscaras estables y track_id local a sesión.

## B15 - Voz, órdenes y cancelación

- [ ] B15 · estado: pendiente · rama: —
- **Etapa / depende:** E5 / B03, B05.
- **Hacer:** STT/intenciones con vocabulario acotado y cancelar prioritario; mantener teclado/JSON. Botón o alternativa explícita de activación.
- **Entregar y medir:** 50-100 frases, intención/objeto, recall cancelar, falsos disparos/latencia M10. Probar mientras suena TTS.
- **Traspaso:** I05; controlador recibe Command sin depender del STT concreto.

## B16 - Buscar, elegir, guiar y distancia

- [ ] B16 · estado: pendiente · rama: —
- **Etapa / depende:** E5 / A19, B13, B14, B15.
- **Hacer:** Completar modos y política de confianza. Usar mismo frame para máscara/depth; guía vence con TTL, distancia puntual congela par. No inventar dirección fuera de cuadro.
- **Entregar y medir:** M7/M8 piloto, casos de múltiples objetos, pérdida, cero profundidad y cancelación; mensajes/metadatos trazables.
- **Traspaso:** I05; consumidor de políticas A19 y productor de logs para A21.

## B17 - Lectura de texto

- [ ] B17 · estado: pendiente · rama: —
- **Etapa / depende:** E5 / B11, B15.
- **Hacer:** OCR en izquierda rectificada completa, escoger frame nítido y leer bloques cancelables; guiar encuadre sin números no medidos. Verificar modelo/licencia.
- **Entregar y medir:** >=30 carteles/etiquetas a 0,5/1 m con GT; CER, éxito de encuadre, primera palabra y cancelación, M10.
- **Traspaso:** I05; no bloquear captura/guía por OCR.

## B18 - Descripción con mediciones y fallback

- [ ] B18 · estado: pendiente · rama: —
- **Etapa / depende:** E5 / A19, B15.
- **Hacer:** Enviar al VLM solo a pedido imagen y objetos/distancias medidas; salida corta, sin distancias inventadas. Plantilla local cuando no hay red/API; claves en .env.
- **Entregar y medir:** >=30 escenas anotadas, afirmaciones sin respaldo, distancias contradichas, latencia/fallo de red, M10. Sin envío remoto silencioso.
- **Traspaso:** I05; consume SpatialObject de A, no estima metros con texto del VLM.

## B19 - Regresión de cuatro modos y fallos

- [ ] B19 · estado: pendiente · rama: —
- **Etapa / depende:** E5 / B16, B17, B18.
- **Hacer:** Ejecutar escenarios automatizados sin hardware: TTL, cancelar, pérdida, pesos ausentes, audio/cámara desconectados y red lenta. Añadir prueba física en Mac.
- **Entregar y medir:** M1/M8/M10; 0 audio cancelado/guía vencida; documentar fallback offline y límites de dispositivo.
- **Traspaso:** I05; A ejecuta replay de cuatro modos con sus resultados.

## B20 - Banco físico de test reservado

- [ ] B20 · estado: pendiente · rama: —
- **Etapa / depende:** E6 / A09, B10, I05, C07.
- **Hacer:** Capturar 10 objetos x1/2/3 m x3 con medida independiente y referencia Z/superficie; sumar 0,5 m si se afirma rango. No reutilizar sesiones de desarrollo para test.
- **Entregar y medir:** M7, 90 medidas por método sobre mismos frames, GT/incertidumbre de cinta/ROI manual; captura inmutable.
- **Traspaso:** I06; A21 recibe datos/GT, devuelve errores por método.

## B21 - Evaluación final de uso y latencia

- [ ] B21 · estado: pendiente · rama: —
- **Etapa / depende:** E6 / B19, B20.
- **Hacer:** Ejecutar búsquedas y escenas nuevas, latencia carga controlada/normal y contraste audible. No dar búsqueda por exitosa solo porque habló.
- **Entregar y medir:** M8/M9/M10: conteos, fallos, P50/P95, n y memoria. >=1000 frames para benchmark y >=30 pedidos por modo como mínimo.
- **Traspaso:** I06; A22 incorpora CSV para tablas comparables.

## B22 - Transporte prototipo (condicionado)

- [ ] B22 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / I06.
- **Hacer:** Si se prioriza wearable: Pi->PC con JPEG grabados, mensajes atómicos y cola acotada/reconexión. No cambiar StereoFrame ni mezclar ojos.
- **Entregar y medir:** M0/M11; verificar opciones ZeroMQ (CONFLATE no multipart) o protocolo equivalente. No atribuir latencia de reloj remoto sin sincronizar.
- **Traspaso:** I07; A recibe mismo replay por transporte.

## B23 - Pi, cámara y audio de ida/vuelta (condicionado)

- [ ] B23 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / B22, B08.
- **Hacer:** Reemplazar JPEG grabado por cámara; comprobar si backend entrega MJPEG original o decodificado. Reenviar control/audio y probar mic/auriculares.
- **Entregar y medir:** M2/M11: bytes/frame, Mbps, descarte por causa, uso CPU y eventos de audio; perfiles Bluetooth medidos en Pi.
- **Traspaso:** I07; no requiere Lite si Fusion sigue a pedido.

## B24 - Montaje, energía y estabilidad (condicionado)

- [ ] B24 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / B23.
- **Hacer:** Probar soporte, foco, alivio de cable, fuente/batería y temperatura. Verificar si montaje altera geometría antes de reutilizar calibración.
- **Entregar y medir:** >=30 min, cortes/reinicios, temperatura, consumo, peso y autonomía medida o extrapolación rotulada, M11.
- **Traspaso:** I07; no prometer movilidad segura ni ocultar inestabilidad.

## B25 - Comparar USB/Wi-Fi y proveedor (condicionado)

- [ ] B25 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / B24.
- **Hacer:** Medir con fuente controlada y luego en uso; probar reconexión y saturación. Evaluar Lite solo si A27 disponible; streaming no espera su entrenamiento.
- **Entregar y medir:** 3x10 min, M9/M11; degradación precisión si hay recompresión, edad y sobrecosto P95. Mantener preset USB.
- **Traspaso:** I07; A28 decide proveedor con mediciones reales.

## B26 - Informe de sistema, póster y reproducción A

- [ ] B26 · estado: pendiente · rama: —
- **Etapa / depende:** E8 / A22, B21.
- **Hacer:** Escribir captura/calibración/arquitectura/interacción/latencia; integrar informe y póster A0/A1 vertical según consigna. Reproducir reporte pequeño de A.
- **Entregar y medir:** M12: cifras y figuras trazables, fallos de instalación; total informe <=8 páginas. Revisar referencias y límites.
- **Traspaso:** I08; A23 ejecuta tu demo y ambos explican el TP completo.

## B27 - Release, demo y defensa

- [ ] B27 · estado: pendiente · rama: —
- **Etapa / depende:** E8 / A29, B26, I07.
- **Hacer:** Congelar aplicación/configs y paquete de respaldo offline; preparar doctor, USB, replay y simulación. Grabar demo real y ensayar fallos/preguntas.
- **Entregar y medir:** M12: 3 ensayos, 2/2 personas reproducen; commit/tag y hashes cuando se autorice publicar. No depender de API en vivo.
- **Traspaso:** I08; terminar solo con artefactos disponibles y documentación ejecutable.

## B28 - Alerta de cercanía (condicionada)

- [ ] B28 · estado: pendiente · rama: —
- **Etapa / depende:** E7 / A28, B16.
- **Hacer:** Si se elige esta extensión, implementar zona central, exclusión del piso, persistencia temporal y audio con prioridad/cooldown. Usar profundidad válida y reciente; suspender alerta ante datos vencidos. No depende de llevar Pi si la prueba es por USB.
- **Entregar y medir:** Recorrido controlado x10: obstáculos avisados, falsas alarmas, distancia/latencia de aviso y cobertura; M8/M11. No evaluar orientación personal confiando en el prototipo.
- **Traspaso:** I07; A verifica proveedor/política y B registra eventos audibles. No aplica si no se prioriza.

