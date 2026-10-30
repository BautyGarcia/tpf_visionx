# Métricas y criterios de aceptación

Las fichas remiten a estos códigos. **C**: corrección obligatoria. **P**: meta de ingeniería
propuesta, ajustar con desarrollo y congelar en C07. **H**: hipótesis científica; si falla,
reportar resultado negativo, no cambiar el test. Nunca tratar una meta como medición obtenida.

| Código | Qué reportar y cómo medir | Criterio |
|---|---|---|
| M0 Contrato/replay | 20 pares/fixture; IDs, geometría, dtype, shapes, EOS, invalidación y repetibilidad | C: 0 cruces/errores; d->Z->d sintético error relativo <=1e-5; entradas adversas rechazadas |
| M1 Primera demo | 8 casos x3: presente, ausente, duplicado, perdido, cancelado, viejo, máscara vacía, depth inválida | C: 24/24 eventos esperados, 0 audio viejo; P: cancelación lógica P95 <=200 ms; detección lista->bip <=500 ms |
| M2 Captura | 10 min/modo finalista; resolución/formato recibido, FPS efectivo, intervalo P50/P95, fallos/descarte, RAM | C: pares íntegros; P: >=15 FPS útiles, sin crecimiento sostenido de cola/memoria; no asumir FPS nominal |
| M3 Calibración | 60-80 pares calibrar, 20 aparte validar, 5 vistas a 1/2/3 m; 3 sesiones | P: RMS reproyección <0,3 px; error vertical mediano <0,3 px + P95; escala <0,5%; error tablero a 1 m <1%; variación f/B <0,5%. Metas exigentes, explicar desvíos |
| M4 Datos/baselines | Split por escena; 10 muestras manuales/adaptador; EPE, bad-2, validez por escena/zona y tiempo | C: 0 fuga entre splits, GT/unidades auditados. Comparación soporte común + cobertura de cada método; no favorecer invalidar píxeles difíciles |
| M5 Modelo | Curvas train/val, EPE/bad-2/NLL, memoria, parámetros, seeds y criterio de checkpoint | C: residual inicial reproduce B4 <=1e-5 px; sin NaN/Inf; b>0 válida. P: overfit 8-16 recortes reduce EPE >=80% antes de corrida larga |
| M6 Incertidumbre | AUSE, riesgo-cobertura 100/90/75/50%; cobertura intervalos 50/80/90%; por rango | H: AUSE mejor que L-R y menor error al abstenerse; informar cobertura. P: intervalo nominal 90% dentro de ±5 puntos en validación; confirmar test sin reajuste |
| M7 Objetos | 10 objetos x 3 distancias (1/2/3 m) x3 =90 medidas/método, misma referencia Z; sumar 0,5 m si se afirma ese rango | MAE/sesgo/P95 absoluto, error relativo, cobertura/abstención por rango; reportar precisión condicional y objetos sin respuesta |
| M8 Interacción | 30 búsquedas (10 objetos/3 ambientes), >=10 min objetivo ausente, 20 cancelar y 10 pérdidas | P: >=80% éxito <=60 s, <=1 falso bip/min; C: 0 guía vencida ni respuestas canceladas. Medir orden->bip/primera palabra y recuperación |
| M9 Latencia | Por configuración 50 warmup +>=300 frames piloto; final >=1000 frames, ideal 3 corridas | P50/P95, n, resolución, backend, RAM/VRAM, edad y FPS útil. P99 exploratorio con n visible. Sincronizar GPU; no mezclar equipos como speedup |
| M10 Voz/OCR/VLM | Voz 50-100 frases: intención/objeto y recall cancelar. OCR >=30 textos a 0,5/1 m: CER. VLM >=30 escenas anotadas: afirmaciones sin respaldo | P: voz >=90% exactitud en vocabulario. C: VLM no inventa distancias; desconexión usa plantilla. Reportar latencia y fallos de cada modo |
| M11 Extensiones | Lite vs sin destilar/Fusion; USB/Wi-Fi 3x10 min controlados; wearable >=30 min | P: Lite >=1,5x pipeline y <=10% degradación EPE a misma cobertura; Wi-Fi sobrecosto P95 <=100 ms, reconexión <=3 s. Registrar consumo, calor, cortes y autonomía real |
| M12 Release | Instalación/replay y subconjunto de reporte por las 2 personas; 3 ensayos demo | C: cifras trazables; P: 3 ensayos sin tocar código. Reportar tiempo/errores, artefactos y tolerancias entre backends |

## Definiciones que deben quedar iguales

EPE=media |d-dGT| en px; bad-2=porcentaje error >2 px a resolución declarada. MAE_Z en m;
sesgo=media Z-ZGT. Principal: media por escena; agregado por píxel rotulado aparte.
NLL Laplace=|d-dGT|/b+log(2b). Intervalo nominal p: d ±[-b log(1-p)]; transformar extremos
a Z solo si disparidad efectiva positiva. El intervalo métrico es asimétrico.
AUSE: área entre sparsification predicha y oracle, fijando grilla/normalización en A02/A16.
Un intervalo por píxel no es automáticamente un intervalo por objeto: A19 lo valida aparte.

Separar GT válido de predicción válida. Publicar porcentaje de fallos y cobertura; no excluir
métodos distintos con reglas distintas. Z=fB/d solo con convención compatible, incluidos doffs.
El plano ChArUco derivado de la misma calibración no valida por sí solo escala: cinta/medida externa.

## Muestreo, tiempo y evidencia

- Cada resultado: commit, config/hash, dataset/split, calibración, modelo/hash, seed, hardware,
  software, resolución, precisión, warmup, n, unidad y script/comando. CSV/JSONL, no texto inventado.
- Validación elige hiperparámetros/checkpoint; test final solo para evaluación congelada. Ablaciones
  con presupuesto comparable; 3 seeds del principal si alcanza. IC 95% por bootstrap de escenas,
  no de píxeles correlacionados. Identificar variantes exploratorias posteriores al test.
- Reloj común en una PC; en Pi usar sincronización/error documentado, RTT o medición externa.
  Inicio lógico del reproductor no equivale a sonido audible; contrastar con audio/video de referencia.
- Detección piloto: >=100 frames de 3 clips anotados; precisión/recall con IoU 0,5 y máscara IoU.
  Un test simulado no valida YOLO; un benchmark final no elige thresholds.
- Metas no alcanzadas: decisión registrada (corregir, reducir alcance, aceptar límite). Geometría
  errónea, fuga de test y respuestas canceladas se corrigen; no se dispensan como rendimiento bajo.

## Aclaración v2

Conservar métricas y separar hipótesis de precisión e incertidumbre. Publicar regresiones
si existen, sin exigir inventar dos casos negativos. Las 90 mediciones se agrupan por
objeto/escena/sesión; no asumir independencia. GT de tablero no es GT denso del fondo.
