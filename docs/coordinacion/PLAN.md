# Plan operativo VisionX — versión 2

29/10/2026. Responsables A: Bauty; B: Tomás. Entrada: [tablero](TAREAS.md).

Reemplaza la planificación v1; conserva IDs y evidencia. No declara software implementado. Entrega **10/12/2026**:
cuatro modalidades funcionales por USB en PC/Mac, evaluación e informe/póster. Después se
completa portátil, Lite, alerta y Fusion-FFS; no se descartan por ser dos personas. Memoria/SLAM
siguen fuera. ELP disponible; Raspberry y batería se reciben tras USB funcional. Audio:
AirPods y otros Bluetooth. Mac M2 Max/32 GB y créditos VM disponibles; verificar GPU/backend
y presupuesto antes de gastar. A/B son responsables, no límite de agentes.

### Calendario objetivo (no evidencia)

| Periodo | Salida verificable |
|---|---|
| 29/10–5/11 | Saneamiento contratos, replay/fakes, captura/calibración inicial, datos/comparadores preparados |
| 6–12/11 | USB clásico, cuatro modos básicos, B0–B4 y protocolo congelado |
| 13–19/11 | Overfit/piloto y entrenamiento Fusion, paquete intercambiable, comparadores ejecutables |
| 20–26/11 | Integración Fusion, ablaciones, incertidumbre y regresiones |
| 27/11–3/12 | Test reservado, reproducción cruzada, tablas, informe/póster y candidato |
| 4–9/12 | Correcciones verificadas, tres ensayos, respaldo offline |
| 10/12 | Entrega académica |
| Posterior | Portátil, Lite, alerta y experimentos pendientes comprometidos |

Retrasos se registran y replanifican sin ocultar pendientes ni inventar mediciones.

### Ciencia

**Depth Anything V2 Small preentrenada y congelada**, alineada a estéreo, aporta la entrada
monocular de nuestra Fusion residual de diez canales junto con RGB y señales SGBM.
B0–B4 son controles. Comparadores comprometidos: A24.1 MonSter, A24.2 DEFOM-Stereo,
A24.3 FoundationStereo y A24.4 Fast-FoundationStereo. Los dos primeros comparan fusión
mono/estéreo. Cada reproducción entrega repo/versión/pesos/licencia, backend, config,
CSV precisión/cobertura/latencia en mismos frames y GT. Fallos requieren diagnóstico y
alternativa de backend; cifras de papers no reemplazan ejecución propia.
Fusion-FFS compara contra FFS solo. Lite compara con la misma red sin destilación.
Antes de entrenar: splits/hash, normalización/cámara, huecos/NaN, métrica principal,
checkpoint y presupuesto; overfit 8–16 recortes y piloto medidos. Precisión e incertidumbre
son hipótesis separadas. Publicar regresiones si existen, no inventar dos casos negativos.

### Cuatro modalidades

| Modo | Base funcional | Mejoras de entrega y pulido |
|---|---|---|
| Buscar/guiar | Clase, presencia, bip, dirección, cancelar | Instancias, tracking, pérdida/reaparición, voz, atributos/identidad |
| Distancia | Congelar par, máscara, metros o abstención | SGBM/B4/Fusion, política por objeto, rango/redondeo calibrados |
| Leer | Frame, OCR y lectura cancelable | Nitidez, bloques, encuadre, números y CER |
| Describir | Plantilla local y hechos medidos | VLM a pedido, hechos controlados, cancelar y fallback offline |

Números/unidades se componen desde mediciones estructuradas, no se confían al VLM.
Portátil inicial: Raspberry captura/transporte/control/audio; computadora procesa.

### Dependencias v2

Separar inicio (interfaz/fixture) de aceptación (consumidor real). A03 comienza sintético;
A01/A02 completan evaluación. B11 comienza con fakes antes de I02. B12 separa captura de
escenas de dashboard: captura no espera B4. A19 tiene política conservadora inicial y
calibración Fusion posterior. B16 usa FakeDepth/SGBM antes de B13; B17 usa teclado antes
de B15. B20 captura test reservado cuando geometría/protocolo estén fijados, sin esperar
I05; no usar ese test para desarrollo. I05 valida modos con proveedor clásico; I04 valida
Fusion aparte. I07 sigue alcance posterior comprometido y no bloquea I08 académico.
Ver [auditoría](AUDITORIA.md) para correcciones antes de consumidores afectados.

### Lectura de propuestas publicadas

HTML/PDF de entregas se preservan como propuesta académica anterior; PLAN v2 prevalece
para ejecución. Sus números nominales no son mediciones. B26 debe sincronizar HTML/PDF
antes de nueva publicación: rango 0,5–3 m (no prometer 30 cm sin medir), GT independiente,
cuatro comparadores y etapas Lite/portátil. No se regeneró PDF en C09.

## Caminos paralelos e integraciones

| Camino | Secuencia de aceptación |
|---|---|
| Base E0 | Contratos, fakes y replay → I00 |
| Aplicación E1/E2/E5 | Replay y audio I01; USB/geometría I02; cuatro modos I05 |
| Ciencia E3/E4/E6 | Datos/B4/protocolo I03; Fusion intercambiable I04; resultados I06 |
| Entrega E8 | I04 + I05 + I06 y artefactos académicos → I08 |
| Continuidad E7 | Lite, Fusion-FFS, portátil y alerta → I07 completo |

Los números identifican capacidades, no una fila de espera global. OCR/voz/controlador
avanzan con fakes, investigación con pares públicos y transporte con replay. Hardware se
reserva aparte. El estado de I07 continúa pendiente después de I08 si falta funcionalidad.
No se declara VisionX 100% por completar solo la entrega académica.

## Comunicación y aceptación

[A](A.md)/[B](B.md) contienen estados oficiales; [fichas](tareas/) especifican el trabajo.
Cada capacidad entrega comando real, fixture/artefacto/hash y salida esperada. Un
coordinador actualiza estados; cada agente modifica solo su ficha/rutas asignadas.
Contratos en [CONTRATOS](../CONTRATOS.md), métricas en [METRICAS](METRICAS.md),
artefactos en [ARTEFACTOS](ARTEFACTOS.md), recepción en [INTEGRACIONES](INTEGRACIONES.md).
La reserva de cómputo incluye presupuesto; crédito disponible no autoriza gasto ilimitado.
