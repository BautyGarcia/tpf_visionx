# VisionX — cómo funciona cada parte y cómo la vamos a comprobar

Actualizado: **2 de noviembre de 2026**. Manual interno: explica términos y motivos para que
podamos seguir el código cuando se implemente. No da por hecho que conozcamos las siglas.

[ROADMAP](ROADMAP.md) contiene tareas y estados. [BITACORA](BITACORA.md) contiene resultados
reales y problemas. Aquí viven las especificaciones: una prueba descrita **no fue ejecutada**
por estar escrita. En esta reorganización no se implementan modelos ni se hacen mediciones.

## Indice

- [Mapa y conceptos](#mapa-y-conceptos)
- [Cámara y calibración](#camara-y-calibracion) — T02/T03
- [Profundidad y alineación](#profundidad-y-alineacion) — T05
- [Entradas y CNN Fusion](#entradas-y-cnn-fusion) — T12
- [Incertidumbre y objetos](#incertidumbre-y-objetos) — T09/T13
- [Detección y cuatro modos](#deteccion-y-cuatro-modos) — T06/T09–T11
- [Ejecución y audio](#ejecucion-y-audio) — T07/T08/T19
- [Datos y comparación](#datos-y-comparacion) — T04/T14/T15/T17/T18
- [Contratos](#contratos) — API pública ya disponible
- [Pruebas previstas](#pruebas-previstas) — M0–M12, metas y criterios
- [Reproducibilidad](#reproducibilidad) — Windows/Mac, artefactos e instalación
- [Glosario](#glosario)

## Mapa y conceptos

**Estéreo** usa dos imágenes del mismo instante. Un punto aparece desplazado horizontalmente
entre ellas; ese desplazamiento se llama **disparidad**, se mide en píxeles y permite obtener
profundidad si conocemos la cámara. **Monocular** usa una sola imagen y aprende pistas visuales
de forma y posición; una predicción relativa no proporciona por sí sola la escala en metros.

**Depth Anything V2 Small** es la red preentrenada que aporta el mapa monocular. Congelada
significa que usamos sus pesos aprendidos sin modificarlos durante el entrenamiento de Fusion.
Nuestra **CNN**, red convolucional, recibe mapas/imágenes y aprende cómo combinarlos.
No estamos entrenando desde cero todo el conocimiento visual del sistema.

| Componente | Entrada | Salida | Si no puede resolverlo |
|---|---|---|---|
| Fuente | USB o grabación identificada | Par izquierdo/derecho y tiempos | Error de dispositivo; None solo fin normal de replay |
| Rectificación | Par y calibración del modo correcto | Par alineado, geometría y zona útil | Rechazar calibración incompatible |
| SGBM | Dos ojos rectificados | Disparidad, máscara válida y chequeos | Huecos explícitos, no cero metros |
| Monocular | Imagen izquierda | Mapa relativo float | Error de modelo distinto de escena sin objetos |
| Alineación | Monocular + anclas estéreo fiables | Monocular en unidades de disparidad + diagnóstico | No alineado y fallback estéreo |
| B4 | Estéreo aceptado + monocular alineado | Combinación fija y su validez | Abstenerse donde ninguna fuente es fiable |
| Fusion | Canales y B4 de ese par | Disparidad corregida y escala b | Estado/motivo y máscara, sin inventar valores |
| Detector | Imagen izquierda de referencia | Clases, cajas y máscaras | Detección vacía si no ve; error si falla el modelo |
| Ubicación espacial | Detección + profundidad compatibles | Dirección, Z y política por objeto | Dirección/reencuadre/abstención |
| Controlador | Orden y resultados de su pedido | Eventos de audio cancelables | Descartar vencidos o cancelados |
| OCR | Frame elegido | Texto y bloques | Pedir encuadre o informar que no pudo leer |
| Descripción | Imagen y hechos medidos | Plantilla o texto contextual | Plantilla local si falla VLM/red |

La salida de Fusion se combina con detecciones; no es necesario que las cuatro modalidades
esperen a que exista una CNN entrenada para desarrollar su recorrido básico.

## Camara y calibracion

### Capturar y grabar — T02

La ELP entrega un cuadro **SBS**, side by side: los dos ojos uno al lado del otro. El preset
actual pide 3840×1080, es decir, 1920×1080 por ojo, MJPEG y 30 FPS. Esto describe lo solicitado,
no demuestra lo recibido. El sufijo de lente, sensor, campo visual, sincronía efectiva y modos
soportados de nuestra unidad deben registrarse con hardware.

Mantener un par atómico: ambos ojos tienen la misma sesión/frame y viajan juntos. Separar
dos archivos o mensajes sin verificar su identidad puede producir una pareja falsa. Comprobar
orden izquierda/derecha con una escena conocida; no corregir una inversión negando metros.

Registrar modo solicitado y observado, backend, resolución, formato, exposición/foco si son
controlables, FPS efectivo y errores. Una imagen SBS no prueba por sí sola la sincronía de
exposición ni la robustez al movimiento; incluir objetos/cámara en movimiento y poca luz.

**Replay** es volver a procesar una grabación. Debe conservar imágenes, identidad, geometría
y tiempo original, y distinguir el tiempo de reproducción. Permite que Bauty y los agentes
trabajen sobre el mismo material sin tener físicamente la ELP.

Una grabación futura tendrá manifiesto con versión, sesión, frames, pares/rutas relativas,
hashes, tiempos originales, modo y calibración. Preservar el original comprimido si el backend
lo permite; no asumir que OpenCV entrega MJPEG sin decodificar. Evitar recompresiones repetidas.

### Calibrar y rectificar — T03

**Calibrar** estima cómo cada cámara proyecta el mundo y cómo se ubica respecto de la otra.
**Rectificar** transforma las imágenes para que las correspondencias estén en la misma fila.
Una red potente no reemplaza esa comprobación geométrica.

Usar tablero **ChArUco**, damero con marcadores identificables. Medir el tablero impreso:
una escala equivocada de impresión produce metros equivocados aunque el ajuste visual parezca bueno.
El YAML actual propone 11×8 cuadrados de 30 mm y marcadores de 22 mm; sustituir por medidas
reales y conservar versión de OpenCV/diccionario. Fijar foco cuando sea posible.

| Parámetro | Significado sencillo | Unidad |
|---|---|---|
| K, D | Cámara de cada ojo y distorsión de la lente | K en píxeles; D según modelo |
| R, T | Rotación y desplazamiento entre ojos | Rotación; T en metros |
| R1, R2 | Transformaciones de rectificación | Matrices |
| P1, P2 | Proyecciones de las imágenes rectificadas | Convención declarada |
| Q | Matriz usada para reconstruir puntos 3D desde disparidad | Convención declarada |
| fx, fy, cx, cy | Focal y centro óptico en la imagen utilizada | Píxeles |
| B | Separación entre centros de cámara, baseline | Metros |
| doffs | Diferencia cx derecha − cx izquierda rectificadas | Píxeles |

Capturar poses y zonas variadas, incluidos bordes; separar calibración, validación y test.
Reportar reproyección y error vertical, pero validar escala con distancia física externa.
El plano del tablero calculado desde la misma calibración no es una referencia independiente
para demostrar su propia escala. No aplicar un factor manual para que coincidan los metros.

**Corrección de disparidad (aceptada el 13/11).** Con la cámara caliente, la ELP mide la
disparidad δ px menor que la real. El error en metros crece con la distancia (+3 % a 1 m, +5 % a
3 m). Eso es la firma de un corrimiento fijo y no de un error de escala, así que un factor sobre
los metros no lo corregiría.
- **Dónde se guarda:** δ se ajusta con cinta y queda en el YAML de calibración
  (`correccion_disparidad`, versión 2 del archivo). Lleva su procedencia y una distancia de control
  que no entra en el ajuste.
- **Cómo se aplica:** `calib.geometry()` lo suma a doffs, así que todo lo que pasa de disparidad a
  metros lo usa sin código adicional. `geometry(disparity_offset=False)` solo sirve para comparar.
- **Valor actual:** `configs/calib/elp-2026-11-11-corregida.yaml`, δ = 0,5275 px a 1920×1080
  por ojo.
- **Para volver a medirlo:** `scripts/calibracion/cinta.py` y después
  `scripts/calibracion/offset_cinta.py`.
- **Límite:** no se mide si δ es estable entre días; se asume.

El núcleo publicado soporta proyecciones canónicas horizontales con origen en el ojo izquierdo
y baseline positivo. No interpreta estéreo vertical/invertido como horizontal. Si la lente real
exige otro modelo, comparar calibraciones sobre validación y planificar compatibilidad explícita;
no borrar matrices que el validador rechaza para forzar que entren.

### De disparidad a metros

Con nuestra convención `d = x_izquierda - x_derecha`:

```text
Z = fx * B / (d + doffs)
```

Z es profundidad **axial**, a lo largo del eje óptico, hacia la superficie visible. No es
automáticamente la distancia en línea recta al objeto ni a su centro físico. Si se incorpora
distancia radial, debe llamarse distinto y tener GT y evaluación propios.

La disparidad efectiva `d + doffs` debe ser positiva. La disparidad cruda d puede ser cero
o negativa y seguir representando un punto válido. Ejemplo sintético ya cubierto en schema 3:
fx=100 px, B=0,06 m, doffs=10 px y d=−4 px dan Z=1 m. No es calibración de la ELP.

Al duplicar distancia, un error fijo pequeño de disparidad produce aproximadamente cuatro
veces más error en metros: `|deltaZ| ≈ Z²/(fx*B) * |deltaD|`. No copiar los valores nominales
de la propuesta como una precisión medida. Rango inicial a validar: 0,5–3 m.
`num_disparities=96` no demuestra por sí solo distancia mínima: intervienen focal, baseline,
resolución, offset y comienzo de la búsqueda.

### Resize, recorte y máscaras

**Resize** cambia tamaño; **crop** recorta. Usar funciones públicas de geometría, una sola vez:

- Resize por sx/sy: fx y doffs escalan con sx; fy con sy; `cx'=(cx+0.5)*sx-0.5` y análogo cy.
  La disparidad se multiplica por sx para conservar Z.
- Crop del mismo origen en ambos ojos: desplazar cx/cy; no cambiar focal, baseline ni disparidad.
  Un recorte puede dejar el centro óptico fuera de la imagen y seguir siendo válido.
- Máscaras y mapas públicos de disparidad se remuestrean por vecino más cercano. No promediar
  profundidades de un borde como si existiera una superficie intermedia.
- Una red puede interpolar sus características internas; eso no autoriza interpolar mediciones
  públicas sin definición. Si se añade otro método de remuestreo, evaluarlo y versionarlo.
- Detector puede trabajar en izquierda rectificada de mayor resolución y depth en otra menor.
  Hay que conservar la transformación; mismo tamaño no garantiza mismas coordenadas.

## Profundidad y alineacion

### SGBM y controles B0–B4 — T05

**SGBM** es un algoritmo clásico de correspondencia estéreo de OpenCV. Busca qué píxel del
ojo derecho coincide con uno izquierdo. No necesita entrenamiento, pero falla en paredes sin
textura, patrones repetidos, reflejos, oclusiones y movimiento. Una oclusión es una superficie
que un ojo ve y el otro no.

**L/R** comprueba ida y vuelta entre los dos mapas. En OpenCV, el matcher derecho puede usar
disparidad de signo opuesto: definir y probar la convención, no restar mapas ciegamente.
El resultado entero de SGBM usa factor 16; convertir a píxeles antes de métricas/geometría.
Separar el valor reservado de inválido de una disparidad físicamente válida con offset.

**WLS**, weighted least squares, es un filtrado guiado por imagen para mejorar el mapa.
Puede suavizar ruido, pero no garantiza recuperar una superficie real. Contar su coste y
medir cobertura/error; conservar parámetros elegidos en desarrollo.

| Control | Definición para implementar y congelar en T05 |
|---|---|
| B0 | SGBM base, con invalidez física/formato correctamente tratada |
| B1 | SGBM con consistencia L/R y filtros de fiabilidad documentados |
| B2 | Variante con WLS, configuración y máscara aceptadas por validación |
| B3 | Monocular alineado mediante anclas estéreo; no presentarlo como monocular métrico independiente |
| B4 | Regla fija: estéreo donde es fiable, monocular alineado en el resto, sin valor donde fallan ambos |

Congelar cuál variante estéreo aporta B4 y sus umbrales con validación, antes del test.
**B4 es el control clave:** ya combina ambas fuentes; si Fusion mejora SGBM pero no B4,
no habremos demostrado que aprender la combinación agrega valor.

### Monocular preentrenada

Usar el mapa relativo flotante de **Depth Anything V2 Small**, no una imagen coloreada del
mapa. Mantener pesos congelados y preprocesamiento oficial registrado. El repositorio contempla
CPU/CUDA/MPS y advierte diferencias de remuestreo entre implementaciones: usar una ruta y
verificar paridad cuando cambie. [Fuente oficial](https://github.com/DepthAnything/Depth-Anything-V2).

La versión métrica es un experimento adicional, con su propio origen de pesos y evaluación
del dominio. No afirmar que metros emitidos por una red monocular eliminan la necesidad de
validación física. No descargar pesos al recibir la primera orden de la demo.

### Alineación robusta

El mapa relativo m se lleva a unidades de disparidad mediante `d ≈ s*m + t`. Ajustar s y t
solo con anclas estéreo fiables, sin usar GT. **RANSAC** prueba ajustes y conserva un consenso
para tolerar valores atípicos. Las anclas son los píxeles con medida estéreo elegidos como apoyo.

La regla anterior de quinientas anclas es insuficiente como único criterio: quinientos píxeles
de la misma pared aportan poca diversidad. Evaluar cantidad/proporción, distribución espacial,
variación de disparidad, consenso y residuos. Reservar anclas antes del ajuste para comprobar
si generaliza; no usarlas para refinar el mismo ajuste y luego presentarlas como validación.

**Salida adicional prevista:** aceptado/no alineado, motivo, número de anclas, cobertura de grilla,
ratio de inliers, parámetros s/t y residuo P50/P95. Definir umbrales en desarrollo y documentarlos
en config. Estos diagnósticos necesitan un resultado auxiliar propio del módulo; no reutilizar
`alignment_quality` como bolsa de campos ni cambiar silenciosamente DepthResult.

Anclas reservadas siguen siendo medidas de estéreo, no GT independiente. Si no hay soporte
métrico fiable, no anunciar que la escala monocular está validada. Fallback: conservar estéreo
válido y dejar huecos/abstención. No arrastrar escala del frame anterior sin comprobar movimiento
y vigencia. Registrar el coste total de estéreo + monocular + ajuste.

## Entradas y CNN Fusion

### Preprocesamiento compartido — T12

Debe existir una única función pública para preparar entradas en entrenamiento y aplicación.
**Canal** es una imagen numérica de una propiedad: RGB tiene tres, uno por color. La referencia
F0 recibe diez; el significado y orden forman parte del checkpoint, archivo con los pesos.

| Posición | Canal F0 | Qué aporta | Tratamiento |
|---|---|---|---|
| 1–3 | RGB izquierda | Apariencia, bordes y contexto local | Convertir BGR público a RGB; normalización registrada |
| 4 | Disparidad estéreo | Escala geométrica | Píxeles normalizados por ancho de referencia |
| 5 | Validez estéreo | Dónde existe medida utilizable | Máscara 0/1 |
| 6 | Error L/R | Evidencia de inconsistencia | Misma unidad normalizada; no confundir con b |
| 7 | Error fotométrico | Si el punto y su correspondencia se parecen | Muestrear derecha en x−d; excluir fuera de imagen |
| 8 | Gradiente izquierda | Bordes/cambios de intensidad | Escala y operador fijados |
| 9 | Disparidad monocular alineada | Estructura donde falla la correspondencia clásica | Misma referencia y unidad que el canal 4 |
| 10 | Diferencia estéreo−monocular | Desacuerdo entre fuentes | Solo donde ambas existen; signo registrado |

F1 agrega el canal 11, **máscara monocular válida y alineada**. Es la primera candidata
recomendada: un cero de relleno no comunica por sí solo que el monocular no tiene escala fiable.
F0 conserva utilidad como referencia; toda variante debe manejar validez correctamente.

Opciones posteriores, no agregados automáticos: F2 introduce calidad del ajuste, como ratio
de anclas y residuo; F3 introduce distancia a anclas fiables. Compararlas con igual protocolo
y registrar si no ayudan. Gradiente/diferencia pueden ser redundantes: ablarlos si el piloto
lo justifica antes de multiplicar entradas.

Imagen derecha o características del encoder podrían recuperar información que los mapas no
conservan, pero implican otro experimento y coste. No exigir máscaras YOLO para que depth exista.
No agregar profundidad anterior como otro canal sin compensar movimiento de cámara/escena.

**Reglas numéricas:**

- Para la primera comparación, normalizar disparidad por el ancho de referencia, con esa misma
  escala para GT, residual y b. Al recortar patches conservar la referencia del frame preparado;
  recortar no significa renormalizar por el ancho del patch. Al redimensionar sí transformar geometría.
- d/W ayuda frente a resolución, pero no hace a la red invariante a focal/baseline. Evaluar
  transferencia entre cámaras. Como alternativa calibrada, `1/Z=(d+doffs)/(fx*B)` requiere
  parámetros físicos disponibles y fiables; no inventarlos en datasets sin ellos.
- No mandar NaN a convoluciones ni usar `NaN*0` como máscara de pérdida. Preparar entradas
  finitas y máscaras explícitas; conservar NaN fuera de validez en los resultados públicos.
- Invalidar caché si cambia par, pesos, configuración, transformación, versión de canales o
  alineación. **Caché** significa reutilizar un cálculo guardado, no una verdad permanente.

### Arquitectura y pérdida

Una **U-Net** reduce la resolución para captar contexto y la recupera combinando información
de detalle de capas anteriores. Mantener la versión inicial compacta y medir parámetros,
operaciones/memoria y tiempo; dos millones de parámetros nominales no garantizan velocidad.

```text
d_final = d_B4 + delta_aprendida
b = salida positiva de escala Laplace
```

Inicializar solamente la cabeza delta a cero: sobre soporte válido, la primera salida debe
reproducir B4 con diferencia <=1e-5 px. No poner toda la red en cero ni declarar válidos huecos
porque la convolución produjo un número. Probar explícitamente el caso en que fallan ambas
fuentes. Validar positividad de d+doffs, sin recortar toda d negativa a cero.

Una **cabeza** es la capa final que produce una salida. La primera corrige disparidad; la
segunda estima b. Entrenar como referencia con **NLL Laplace**, una pérdida que penaliza error
y una incertidumbre que no explica ese error:

```text
NLL = |d_predicha - d_GT| / b + log(2*b), con b > 0
```

Comparar con error robusto + NLL solo como variante de validación, registrando pesos de cada
término. No añadir muchas pérdidas a la vez: impediría explicar qué produjo una mejora.
En una ablación sin monocular, quitarlo también de B4 y de canales derivados; dejarlo en la
base residual contaminaría el experimento.

Este enfoque es **fusión tardía de mapas**: no reconstruye un volumen completo de posibles
correspondencias entre ojos. Si ambos mapas perdieron una superficie, una corrección local
puede no recuperarla. Esa diferencia frente a comparadores forma parte de las limitaciones.

### Entrenar y entregar

Antes de una corrida larga: auditar canales y GT, fijar split/métrica/checkpoint/presupuesto;
overfit de 8–16 recortes y piloto con tiempo/memoria reales. **Overfit** aquí es una prueba
controlada: comprobar que la red puede memorizar ejemplos pequeños antes de exigir generalización.

Guardar curvas, semillas, configuración completa, pesos y reanudación. Una semilla fija la
aleatoriedad inicial; no promete identidad bit a bit entre todos los backends. Hacer tres seeds
del modelo principal si el presupuesto lo permite; informar si no. Seleccionar por validación,
con EPE media por escena como principal de disparidad; nunca escoger época con test final.

Entregar checkpoint local inmutable, hash, arquitectura, orden de canales, normalización,
versión de preprocesamiento, datos/split, backend/precisión y una **model card**, ficha que
explica uso, entrenamiento, resultados y límites. Recibirlo desde un proceso limpio, sin notebook.
El entrenamiento y la aplicación deben coincidir dentro de tolerancia declarada.

## Incertidumbre y objetos

### Qué significa b — T13

b es una escala de error en píxeles de disparidad, no un porcentaje de certeza ni detector
garantizado de escenas nuevas. Evaluar tres preguntas distintas: si ordena errores, si sus
intervalos se calibran y si mejora las decisiones sobre objetos.

Para una Laplace centrada en d, intervalo nominal de probabilidad p:

```text
[d - radio, d + radio], donde radio = -b * log(1-p)
```

Convertir extremos a Z solo si sus disparidades efectivas son positivas. El intervalo métrico
es asimétrico, y si atraviesa la singularidad no hay un intervalo finito bilateral fiable.
No resolverlo recortando el extremo y afirmando la misma cobertura nominal.

**Riesgo-cobertura** muestra cuánto error queda al responder solo en una fracción de los casos.
**AUSE** compara ese descarte con un orden ideal que conoce el error real; se fijan grilla y
normalización antes de comparar. Un intervalo del 90% debe contener el GT aproximadamente
ese porcentaje de veces en datos independientes; un número b positivo no demuestra calibración.

### Pasar de píxeles a un objeto — T09/T13

Entrada: frame, máscara y DepthResult de identidad/geometría compatibles. Transformar la máscara
explícitamente si depth tiene otro tamaño. Como referencia, mediana de disparidades válidas
dentro de máscara y conversión a Z con la geometría; dirección desde el centro representativo.

Medir contaminación de fondo. Una máscara interior puede ayudar, pero erosionar por un número
fijo de píxeles puede borrar llaves/cables: comparar una política adaptativa y registrar cobertura.
Una caja sin máscara no equivale a segmentación exacta del objeto.

La política considera fracción válida, dispersión de superficies, calidad de alineación,
rango, edad de la observación y estabilidad de selección. La dispersión robusta no se etiqueta
automáticamente como intervalo de confianza. Los píxeles vecinos están correlacionados;
no promediar b y asumir que tenemos la incertidumbre del objeto.

Salidas posibles ya previstas: decir metros, solo dirección, pedir reencuadre o abstenerse.
Conservar por separado score detector y calidad de depth: multiplicarlos no crea una probabilidad
conjunta calibrada. Calibrar umbrales/rango/redondeo en ELP de desarrollo y congelarlos antes de test.

## Deteccion y cuatro modos

### Detector y tracking — T06

**YOLO** detecta objetos; una versión **seg** también produce máscaras de instancia, una por
objeto. Probar YOLO26n-seg y referencia YOLO11n-seg; subir a small si mejora los objetos pequeños
con coste aceptable. Decidir con clips propios, no con FPS anunciados para otra GPU.
[YOLO26 oficial](https://docs.ultralytics.com/models/yolo26/).

Las clases dependen de pesos/entrenamiento. Un detector de vocabulario fijo COCO no recibe
automáticamente capacidad de encontrar llaves al pasarle ese texto. Evaluar **YOLOE-26**,
detección/segmentación de vocabulario abierto mediante texto o ejemplos, antes de encadenar
YOLO-World con otro segmentador. Los prompts y embeddings deben estar preparados; su primer
uso puede descargar un encoder. No se garantiza reconocer cualquier objeto nombrado.
[YOLOE oficial](https://docs.ultralytics.com/models/yoloe/).

Probar español y alias del catálogo; guardar qué categorías fueron aceptadas con evidencia.
Mantener un detector principal por configuración, sin correr todos en cada frame.
**ByteTrack** relaciona detecciones entre frames y da un ID temporal. No prueba identidad
personal. Añadir huella de apariencia, por ejemplo DINOv2, solo si mejora pérdidas/reapariciones
frente a su coste; mirar primero características visuales ya calculadas.

La regla anterior de presencia en tres de cinco frames es un candidato: cinco frames duran
distinto a 3 y a 30 FPS. Medir persistencia temporal, falsos avisos y tiempo al primer bip.
Con varios objetos iguales se pide elección. Si se pierde el elegido, suspender guía;
no asignar su identidad al primero parecido ni inventar posición fuera de cuadro.

### Buscar y distancia — T09

Buscar empieza con orden/clase y detecciones recientes: bip cuando corresponde, luego dirección
breve. No esperar metros para avisar presencia. La guía actualiza por cambio útil/intervalo,
no habla en cada frame. Registrar ausencia, recuperación y cambio de objetivo.

Distancia congela un par identificado y su selección: no aplicar la máscara más nueva a un
depth anterior. Responder Z axial con redondeo acorde a validación, o explicar abstención.
El usuario debe poder cancelar en captura, inferencia, preparación de frase y reproducción.

### Leer — T10

**OCR**, reconocimiento óptico de caracteres, convierte imagen en texto. Usar un motor
especializado, inicialmente RapidOCR/ONNX con modelo adecuado para español. Un **backend**
es el motor que ejecuta el modelo, no necesariamente otro modelo.
[RapidOCR oficial](https://github.com/RapidAI/RapidOCR).

Conservar imagen izquierda de suficiente resolución; elegir nitidez/encuadre y ordenar bloques
para lectura. Si rectificación deforma texto o elimina bordes, comparar una ruta original
con su contexto explícito, sin atribuirle la geometría rectificada. Leer bloques cancelables.
Evaluar números y etiquetas, no solo frases fáciles. **CER** es la tasa de caracteres editados
para llegar a la transcripción correcta; su definición está en métricas.

### Describir — T11

Primera salida: plantilla local con objetos/direcciones/medidas aceptadas. Después VLM a pedido
para contexto no métrico. No dejar que una distancia generada por el VLM pase por una medición.
Componer números/unidades desde SpatialObject y resolver contradicciones con la política.

Separar hechos medidos y contexto generado; revisar afirmaciones sin respaldo en escenas anotadas.
Proveedor/modelo de API todavía no elegido: comparar calidad, latencia, coste, límite de salida,
timeouts y funcionamiento sin red. Enviar imagen solo al pedirlo, con ruta remota explícita.
El VLM no controla directamente la máquina de estados ni la selección de un objeto.

## Ejecucion y audio

### Interactivo y científico — T07

Mantener una aplicación modular, con lógica pública compartida. **Interactivo:** captura sigue
avanzando; detector, profundidad y audio tienen ritmos propios. Una cola acotada mantiene
actualidad y evita esperar frames viejos. Coordinar uso de GPU; más hilos de inferencia no
garantizan más velocidad. **Científico:** pares fijados, métodos comparados sobre el mismo
contenido, sin descarte para aparentar más FPS.

Unir por `(session_id, frame_id)` y transformación, no por «última salida de cada módulo».
Conservar una caché acotada de frames para completar resultados compatibles. Mostrar edad,
estado, resolución, unidad y latencia de cada mapa. Usar escala de color común; una imagen
bonita autoescalada por método no demuestra precisión.

Calcular SGBM/DA una vez si B4 y Fusion comparten esos resultados en el panel. En el benchmark
de cada pipeline contabilizar su coste completo; reutilizar una caché ajena no cuenta como
aceleración propia. La nube de puntos se genera por frame, sin SLAM acumulado.

**request_id** identifica una orden. Una nueva invalida resultados de las anteriores.
**TTL/deadline** es el límite de vigencia: aunque el cálculo termine, puede ser demasiado viejo.
El reloj es monotónico local para duraciones; replay usa reloj de reproducción. No restar relojes
monotónicos de Pi y PC sin sincronización y error conocido.

### Audio USB y voz — T08

Ruta inicial: micrófono de computadora/USB → captura de muestras → VAD/botón → STT → reglas →
Command → controlador → AudioEvent → TTS/frase preparada → auriculares. **STT** transcribe voz;
**TTS** sintetiza voz. **VAD** detecta actividad vocal; no comprende la orden.

Evaluar sounddevice como adaptador de entrada/salida y Silero VAD. El callback de audio solo
mueve muestras: no ejecutar allí CNN, transcripción, red ni escritura pesada. **Callback** es
una función que el sistema llama cuando tiene que recibir o reproducir un bloque de audio.

En Mac evaluar MLX Whisper multilingüe; en Windows faster-whisper CPU, y CUDA si el equipo
dispone de ella. CTranslate2, usado por faster-whisper, no ofrece un backend MPS publicado:
tener PyTorch/MPS no lo acelera automáticamente. [CTranslate2](https://opennmt.net/CTranslate2/hardware_support.html),
[MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper).

Interpretar las órdenes con reglas/alias en español al comenzar. Pedir aclaración cuando no
se identifica modo/objeto. Intern-Decision o un LLM de intenciones quedan como alternativas
si las pruebas justifican su coste; un «70%» emitido por el modelo no es confianza calibrada.

Piper local y frases frecuentes precalculadas reducen dependencia de red. Verificar licencia
del motor y de cada voz. Probar cancelación lógica y audible, duración de bloque/cola y qué
ocurre si TTS vuelve a entrar al micrófono. El botón de cancelación no debe depender de que STT
reconozca una palabra mientras se reproduce voz. [Piper oficial](https://github.com/OHF-Voice/piper1-gpl).

Probar AirPods/Bluetooth como salida y después su micrófono; los perfiles/dispositivos pueden
cambiar calidad y latencia al usarlos simultáneamente. No dar full duplex por resuelto sin
medirlo. Si falla, usar micrófono separado y registrar límite; no bloquea desarrollar los modos.

### Audio y video portátil — T19

En la primera versión portátil, Pi captura cámara/mic y maneja reproducción/control. La Mac
ejecuta percepción/STT/TTS. Auriculares se conectan a Pi; el emparejamiento y el perfil elegido
requieren prueba en ese sistema, no se deducen de que funcionen en Mac.

Prototipo de red LAN: WebSockets binarios con canales separados para video, audio y control.
Incluir versión, sesión, secuencia, formato y request; colas acotadas y desconexión explícita.
PCM mono 16 kHz/16 bits consume 256 kbit/s antes de transporte; la salida puede usar otra tasa
según voz/dispositivo. Medir tiempos con recepción/RTT o sincronización documentada.

Cancelar localmente corta la reproducción de Pi sin esperar ida y vuelta. Un par visual viaja
como mensaje atómico. Si se usa ZeroMQ, verificar su semántica: CONFLATE no admite multipart;
no usarlo para dos ojos en partes independientes. WebRTC/Opus será alternativa si jitter,
bloqueo del transporte o ancho de banda medidos lo justifican; no agregar dos protocolos por rutina.

Montaje: revisar sujeción/lentes, calor, consumo, tensión estable, cortes y autonomía con batería.
Medir los bytes y CPU reales; «USB 2» o «Wi-Fi» en una ficha no es un benchmark del montaje.

### Alerta — T20

Analizar zona central y excluir piso con método declarado; exigir persistencia y profundidad
reciente, priorizar audio y espaciar avisos. Suspender ante mapas viejos o sin cobertura. Probar
por USB antes de wearable si ayuda. Elegir B4/Fusion/Lite según medidas, no exigir Lite de antemano.
Evaluar obstáculos/falsas alarmas en recorridos controlados; no declarar navegación autónoma.

## Datos y comparacion

### Datos y GT — T04

**GT**, ground truth, es la referencia con la que medimos error, no la salida de otro modelo
por ser más grande. InStereo2K es la base prevista de entrenamiento; verificar distribución,
licencia y descarga. Su PNG de disparidad almacena valores multiplicados por 100 y cero
representa inválido: dividir por 100 y excluir esos píxeles. Esta regla no se aplica ciegamente
a otros datasets ni al contrato general con doffs. [Formato oficial](https://github.com/YuhuaXu/StereoDataset).

Separar **train** (aprender), **validación** (elegir arquitectura/umbrales/checkpoint) y **test**
(evaluación congelada). Las imágenes casi iguales de una misma escena/sesión no deben terminar
en grupos distintos. Mantener el test oficial separado; del entrenamiento se obtiene validación.
Auditar diez muestras/adaptador: imagen, rango, escala, máscara y transformaciones.

Middlebury/ETH3D y ELP aportan evaluación; fijar versiones/subconjuntos según acceso a GT.
No anunciar conteos definitivos copiados de propuestas: verificarlos en el manifiesto descargado.
En Middlebury leer focal/baseline/doffs/unidades de su calibración; no suponer centros iguales.
[Convenciones de Middlebury](https://vision.middlebury.edu/stereo/data/scenes2014/).

**Test público (decidido 13/11).** Middlebury 2014 es el principal. ETH3D two-view es
secundario: sus imágenes están en escala de grises y DA V2/Fusion trabajan en color. Se replica
el canal y se informa como limitación.

**Banco ELP (decidido 13/11).** 40 escenas en 5 sesiones de 8, en lugares, días o iluminación
distintos. Se divide **por sesión**: 2 sesiones de desarrollo (≈16 escenas: umbrales, política y
abstención) y 3 de test (≈24 escenas). El test se graba, se registra su hash y no se miran
resultados sobre él hasta la evaluación final. Las escenas ELP **no entrenan Fusion**, porque no
tienen GT densa. Las grabaciones sin GT para pseudoetiquetas de T17 son sesiones aparte.
Cada escena cubre 0,5–3 m (el rango validado en T03) y mezcla superficies con y sin textura,
reflejos y objetos de clases de la app. Sin personas.

**GT de la ELP.**
- **Principal.** 6–8 puntos por escena marcados con stickers chicos (~1 cm), para no regalarle
  textura al estéreo. Se mide la profundidad axial con cinta: la distancia perpendicular desde
  una línea del piso alineada con el plano de las lentes hasta la vertical del punto. La cámara
  va nivelada y su inclinación se verifica con el damero. Cada punto se ubica a mano en la imagen
  izquierda rectificada y se evalúa en una ventana chica alrededor. Se espera una precisión de
  ±1 cm: con fx ≈ 601 px y B ≈ 60 mm, 1 px de disparidad a 3 m equivale a ~25 cm (`Z²/(fx·B)`).
  El centro óptico queda ~13 mm detrás del vidrio de la lente (ajuste del 13/11). Si la línea de
  referencia se apoya en el vidrio, sumar 13 mm a la lectura de la cinta.
- **Secundaria.** 1–2 escenas por sesión con el damero, para evaluar densidad sobre ese plano.
- **Exploratoria.** El LiDAR del iPhone 16 Pro sirve como referencia densa aproximada, pero no
  es GT: tiene baja resolución, error propio y hay que alinearlo con la ELP. No entra en las
  métricas principales.

Una cinta mide puntos/superficies concretas; un tablero da plano donde está el tablero, no GT
denso del fondo. Separar ROI manual, máscara predicha y superficie realmente referenciada.

Usar aumentos que simulen compresión/iluminación de ELP si la validación muestra utilidad;
guardar parámetros y comparar sin ese aumento. No deformar geometría, GT o máscaras por separado.

### Comparadores — T14

| Modelo | Qué nos permite estudiar | Ruta de trabajo |
|---|---|---|
| [MonSter](https://github.com/Junda24/MonSter) | Integración monocular/estéreo más profunda que nuestra fusión de mapas | Reproducir código/pesos y verificar backend |
| [DEFOM-Stereo](https://github.com/antigravity-tech/DEFOM-Stereo) | Estéreo apoyado en un modelo fundacional de profundidad | Auditar inicialización, escala e inferencia |
| [FoundationStereo](https://github.com/NVlabs/FoundationStereo) | Referencia fuerte de generalización y calidad, con priors monoculares | Entorno compatible, preferentemente NVIDIA para la ruta publicada |
| [Fast-FoundationStereo](https://github.com/NVlabs/Fast-FoundationStereo) | Compromiso calidad/velocidad y proveedor de Fusion-FFS | Registrar checkpoint/iteraciones/backend; tiempos oficiales no son tiempos Mac |

Cada reproducción entrega repo/commit, pesos/hash/licencia, dependencias, resolución, precisión,
iteraciones, máscaras/fallos, comando y CSV por escena. Si falla instalación, registrar error,
diagnóstico y siguiente alternativa; no reemplazar una ejecución propia por la tabla del paper.

Separar **comparación de calidad** (mismos pares/GT) y **comparación de despliegue** (mismo
hardware/condiciones para tiempos). No afirmar un speedup entre Mac y NVIDIA. Los preentrenados
tienen historias de datos distintas: auditar solapamientos conocidos y declarar lo desconocido.
Sin información suficiente, no afirmar que una prueba es completamente libre de solapamiento.

**Pesos a usar (investigación del 13/11, leyendo los repositorios; nada se ejecutó).**
- **MonSter y DEFOM:** usar los checkpoints entrenados solo con SceneFlow. `mix_all` y los
  afinados incluyen Middlebury, ETH3D o InStereo2K. El README de MonSter avisa un error en
  `sceneflow.pth`, pendiente de que lo vuelvan a subir.
- **FoundationStereo:** el modelo base no usa Middlebury ni ETH3D, pero hay una variante afinada
  con ETH3D. Confirmar a cuál corresponde cada checkpoint publicado.
- **FoundationStereo y Fast-FoundationStereo** entrenan con InStereo2K. Para nosotros InStereo2K
  es solo train/val; declararlo en el informe.
- **Licencias:** MonSter y FoundationStereo permiten solo uso no comercial/académico.
- **Hardware:** ninguno de los cuatro documenta CPU ni MPS. Se ejecutan en GPU NVIDIA.

### Ablaciones y evaluación final — T12/T15

Una **ablación** quita una pieza para comprobar su aporte. Mantener presupuesto comparable,
mismos splits, reglas de validez y semillas registradas. Mínimas: sin monocular también en B4;
sin confianza clásica; sin incertidumbre/pérdida NLL. Agregar sin RGB, F0/F1, canales extra,
compuerta residual y compresión si el piloto justifica esos experimentos. No usar test para elegirlos.

Medir error y cobertura propios de cada método y error en soporte común. **Cobertura** es
qué parte del GT válido recibió respuesta; un método no gana borrando sus píxeles difíciles.
Reportar también fallos completos de modelo/frame. Bordes, oclusiones y baja textura requieren
reglas/GT de regiones definidos; un mapa L/R es un indicador, no verdad de oclusión independiente.

Congelar modelo/config/umbrales/commit antes del test reservado. Comparar diferencias pareadas
por escena y registrar casos que empeoran si aparecen. La hipótesis puede fallar sin que eso
invalide la evaluación. Después del test, nuevos cambios se etiquetan como exploratorios;
no presentar el mismo test reutilizado como una segunda confirmación independiente.

### Lite y Fusion-FFS — T17/T18

**Destilación** entrena un alumno usando salidas de un teacher. Lite omitirá DA en inferencia;
no asumir que eso elimina el coste de SGBM. Pseudoetiquetas de Fusion en escenas ELP de
entrenamiento no son GT independiente. Medir aceptación por escena y qué casos desaparecen
al filtrar incertidumbre: podrían ser justo los difíciles que necesitamos aprender.

Priorizar diversidad y sesiones separadas antes que muchos frames consecutivos. Evaluar Lite
contra la misma red sin destilación y calibrar su propia incertidumbre; no hereda la del teacher.

Fusion-FFS sustituye el proveedor estéreo por FFS, con canales/confianza adecuados a ese método.
Comparar contra **FFS solo**, contando FFS + monocular + ajuste + CNN. No es una mejora de
SGBM ni un cambio gratuito de pesos. Mantener paquete/versión propios y registrar resultados.

## Contratos

### Lo ya implementado

La API pública existe en `src/visionx/shared/`: `contracts.py`, `interfaces.py`, `geometry.py`,
`errors.py` y `clock.py`. **API** es la forma acordada de llamar a una parte sin conocer sus
funciones internas. La versión actual de mensajes es **schema 3**. Las nuevas explicaciones
de este manual no cambian por sí mismas esos tipos.

| Tipo público | Datos principales y significado |
|---|---|
| FrameKey | `session_id` + `frame_id`: identifica una imagen dentro de una sesión |
| StereoFrame | Ojos BGR uint8 H×W×3, recepción/captura/origen de reloj, replay original, rectificación, calibración/geometría y fuente |
| StereoGeometry | Tamaño, fx/fy/cx/cy, baseline en m, doffs en px e ID derivado de valores exactos |
| DepthResult | Identidad, modelo/geometría, disparidad float32 H×W, máscara bool, status/motivo, tiempo, Z opcional y tipo de incertidumbre |
| Detection | Identidad/modelo, geometría obligatoria, calibración, tamaño, cajas xyxy float32 N×4, clases/scores, máscaras bool N×H×W y tracks opcionales |
| SpatialObject | Objeto seleccionado: índice/track/clase, modelo depth, ángulos, Z axial, dispersión, fracción válida, score detector y política |
| Command | request, modo, texto/objetivo, emisión/deadline y frame congelado opcional |
| AudioEvent | request, prioridad, texto/sonido, creación/deadline, cancelabilidad y frame opcional |

H=alto, W=ancho y N=cantidad de objetos. BGR es el orden de colores de OpenCV; RGB el de
muchas redes. float32 es un formato numérico flotante; bool solo contiene verdadero/falso.
None significa que no hay dato; no equivale a cero ni a fallo del dispositivo.

Los arrays se copian al construir mensajes para que reutilizar buffers de cámara no modifique
resultados anteriores. No modificarlos durante esa construcción; copiar explícitamente si una
librería necesita escribir. Eso cuesta memoria/tiempo: medir antes de diseñar zero-copy,
una optimización que comparte buffers y exige controlar su vida útil.

| Interfaz existente | Operaciones públicas |
|---|---|
| FrameSource | `read() -> StereoFrame o None`; `close()` |
| DepthEstimator | `model_id`; `predict(frame) -> DepthResult`; `close()` |
| Detector | `model_id`; `predict(frame) -> Detection`; `close()` |
| SpatialEstimator | `locate(frame, depth, detections) -> Sequence[SpatialObject]` |
| AudioSink | `submit(event)`; `cancel(request_id)`; `close()` |

Son **Protocols** de Python: un objeto cumple la interfaz si ofrece esas operaciones; no
necesita heredar una clase base. Fakes y reales comparten la firma; fake significa sustituto
controlado para comprobar lógica, no una predicción real. Los adaptadores concretos siguen pendientes.

### Validación y fallos

- `check_schema`: versión compatible. Cambiar solo el número no migra datos externos.
- `check_same_frame`: sesión/frame compatibles; no compara transformaciones ni hace resize.
- `check_geometry`: ID esperado; `check_detection_frame`: además identidad, tamaño/calibración.
- `check_depth_geometry`: tamaño/doffs/ID y coherencia entre Z y disparidad si se entrega Z.
- `check_not_expired`: vigencia con el reloj elegido. La comprobación actual vence cuando
  `now > deadline`; no cambiar esa semántica sin prueba/migración.

Un consumidor necesita las verificaciones pertinentes juntas: no cambiar un geometry_id
para que una máscara ajena pase. Depth no lleva todos los campos de calibración de Detection;
resolver su contexto con frame/geometría inmutables en lugar de inventar campos existentes.

`DepthStatus`: valid, partial o unmeasurable; los dos últimos necesitan motivo. Z debe ser
positiva/finita en validez; d+doffs positiva/finita. Fuera de máscara puede haber NaN, valor
que representa ausencia de número. La salida pública no reemplaza huecos con cero metros.

`UncertaintyKind` distingue none, laplace_b y lr_consistency. b positiva/finita en px; error
L/R no negativo en px, distinto de una distribución calibrada. `alignment_quality` no define
por sí solo todo el diagnóstico de RANSAC; cualquier ampliación requiere API pública documentada.

`DistancePolicy`: speak_meters, direction_only, ask_reframe y abstain. Metros exige Z disponible.
`Priority`: LONG, SHORT, SEARCH, ALERT, en orden creciente; cancelación invalida el pedido.
`CaptureClock`: none, device o estimated; no llamar timestamp de sensor a una estimación del backend.

Errores: InvalidInput, SchemaMismatch, IdentityMismatch y Expired para datos incompatibles;
SourceError para fuente y EstimatorError para modelo. Cero detecciones es resultado válido;
cámara rota o pesos ausentes no se ocultan devolviendo una detección vacía.

### Recepción de schema 3

Publicada en PR #10 `d8a38bd`: geometría con offsets, recortes válidos, P1/P2 verificadas,
arrays estables y Detection con contexto geométrico. El ID geométrico ahora conserva floats
exactos; regenerarlo desde parámetros, no desde un redondeo anterior.

Al construir Detection indicar `geometry_id` y propagar `calibration_id` del frame. Al construir
DepthResult pasar `doffs=geometry.doffs`, aunque el default sea cero. Transformar explícitamente
máscaras si hay distintas resoluciones y verificar ambas geometrías.

Recrear mensajes schema 2 desde imágenes/metadatos conocidos, no renombrar su schema. Rechazar
contexto ambiguo. La fixture `tests/fixtures/schema3-negative-disparity.yaml` documenta el
ejemplo virtual d=−4/doffs=10. Su recepción en Mac por el consumidor sigue pendiente.

## Pruebas previstas

**Esta sección es el plan de verificación futura, no un informe de pruebas ejecutadas.**
Conservar códigos M0–M12 para entender registros anteriores. **C**=corrección obligatoria;
**P**=meta de ingeniería que se confirma con desarrollo; **H**=hipótesis científica que puede fallar.
Metas incumplidas exigen explicación/decisión, no números inventados ni descarte del alcance.

| Código / tareas | Qué comprobar | Criterio o muestra prevista |
|---|---|---|
| M0 T01–T03 | Contrato, geometría y replay | C: veinte pares, cero cruces; d→Z→d error relativo <=1e-5; dtype/shape/EOS/esquema y datos adversos |
| M1 T07–T09 | Primera interacción y fallos | C: ocho casos ×3, 24/24 eventos correctos, cero audio viejo. P: cancelación lógica P95 <=200 ms; detección lista→bip <=500 ms |
| M2 T02/T19 | Captura efectiva | Diez minutos/modo, resolución/formato observado, FPS, intervalos, descartes, RAM. C: pares íntegros. P: >=15 FPS útiles, colas/memoria estables |
| M3 T03 | Calibración y estabilidad | 60–80 pares para ajustar, veinte separados para validar, cinco vistas a 1/2/3 m, tres sesiones. P: RMS <0,3 px, vertical mediana <0,3 px más P95; escala <0,5%, tablero 1 m <1%, variación f/B <0,5%; explicar desvíos |
| M4 T04/T05/T14/T15 | GT, baselines y cobertura | Diez muestras/adaptador, cero fuga; EPE/bad-2 por escena/región, soporte común y cobertura propia. C: unidades/GT auditados |
| M5 T12 | Entrenamiento y paquete | C: residual inicial B4 <=1e-5 px, sin NaN/Inf, b>0. P: overfit 8–16 recortes reduce EPE >=80%; piloto antes de corrida larga |
| M6 T13 | Incertidumbre | NLL, AUSE, riesgo-cobertura 100/90/75/50%, intervalos 50/80/90% por rango. H: mejor orden/abstención que L/R. P: cobertura nominal 90% dentro de ±5 puntos en val; test sin reajuste |
| M7 T09/T13/T15 | Medición de objetos | Diez objetos ×1/2/3 m ×3=90/método; agregar 0,5 m si se afirma ese rango. MAE, sesgo, P95, cobertura y abstención; referencia Z común |
| M8 T06/T09/T15/T20 | Uso, pérdida y falsos avisos | Treinta búsquedas en tres ambientes, >=10 min ausente, veinte cancelar y diez pérdidas. P: >=80% éxito <=60 s, <=1 falso bip/min; C: cero guía vencida/respuesta cancelada |
| M9 T05/T07/T12/T14/T15 | Latencia completa | 50 warmup +>=300 frames piloto; >=1000 final, ideal tres corridas. P50/P95, memoria/edad/FPS útil; P99 exploratorio con n visible; GPU sincronizada |
| M10 T08/T10/T11 | Voz/OCR/descripción | 50–100 frases, >=30 textos a 0,5/1 m, >=30 escenas anotadas. P: voz >=90% intención/objeto; CER y errores numéricos. C: cero metros inventados y fallback sin red |
| M11 T17–T20 | Continuidad | P: Lite >=1,5× velocidad pipeline y <=10% degradación EPE a igual cobertura. USB/Wi-Fi 3×10 min; sobrecosto P95 <=100 ms, reconexión <=3 s. Wearable >=30 min con calor/energía/autonomía. Alerta: diez recorridos controlados |
| M12 T01/T16 | Reproducción y entrega | Ambos instalan/reproducen subconjunto; tres ensayos sin tocar código. C: cifras trazables a artefactos; pendientes declarados y respaldo offline |

Casos de M1: presente, ausente, duplicado, perdido, cancelado, vencido, máscara vacía y depth
inválida. Añadir modelo/peso ausente, cámara/audio desconectados, error de red, salida fuera de
orden y cancelación durante OCR/inferencia/TTS. Los fakes no validan precisión del detector.

### Entender las métricas

- **EPE:** media del error absoluto de disparidad, en px. **bad-2:** porcentaje con error >2 px
  a resolución declarada. Reporte principal: media de métricas por escena; el promedio por píxel
  se informa aparte para no hacer que una imagen grande domine el resultado.
- **MAE_Z:** media del error absoluto en metros; **sesgo:** media predicción−GT, con signo.
  P95 del error muestra qué pasa en los casos difíciles, no solo el promedio.
- **P50/P95:** percentiles; P95 es el valor que no supera el 95% de las muestras. Indicar n,
  unidad y condición. **Warmup:** primeras ejecuciones para preparar el motor; separarlo del arranque frío.
- **CER:** distancia de edición de caracteres / cantidad de caracteres de referencia, con
  reglas de espacios/acentos fijadas. Reportar errores de números también por separado.
- **IoU:** intersección/unión de cajas o máscaras; coincidencia a IoU 0,5 no equivale a máscara
  perfecta para medir. Detector piloto: >=100 frames de tres clips anotados, precisión/recall y máscara IoU.
- **Recall de cancelar:** qué fracción de órdenes de cancelar reconoció; informar además
  cancelación física y si efectivamente se cortó el sonido.

**Métricas principales de profundidad (fijadas el 13/11, antes de entrenar):**
- **Middlebury 2014:** AbsRel = |Z−Z_GT|/Z_GT y bad-2, sobre los píxeles con GT válida.
- **Banco ELP:** porcentaje de puntos con error relativo ≤ 5 %, más la mediana y el P90 del error
  relativo.
- **Siempre:** cobertura, es decir la fracción con respuesta, junto al error.
- **Comparación que define el resultado:** Fusion contra B4 con esas dos métricas, a igual
  cobertura.
- **Para T13:** AUSE y riesgo-cobertura.
- No cambiar esta elección después de ver resultados de validación o test.

No mezclar GT válido y predicción válida. Un fallo tiene cobertura/fallo explícitos, no EPE cero.
IC95%, intervalo estadístico de comparación, por bootstrap de escenas/grupos; no remuestrear
millones de píxeles correlacionados como si fueran independientes. Las 90 medidas se agrupan por
objeto/escena/sesión. Mantener comparaciones pareadas y n efectivo.

Latencia: registrar captura, recepción, inicio/fin de cada componente, pedido, evento y audio
audible. Un callback iniciado no prueba que el usuario ya oyó el sonido. Sincronizar CUDA/MPS
para medir kernels y contrastar audio con grabación externa. Contar pipeline completo.

### Lo que requiere hardware

No verificable solo leyendo código: modos/sincronía/exposición de ELP, escala/calibración real,
movimiento, distancias físicas, inferencia concurrente M2 Max, micrófono/auriculares y latencia
audible, Pi/Wi-Fi/reconexión, batería/consumo/calor. Registrar equipo, commit, configuración,
hashes, resolución, backend, n y unidades cuando se mida. La CI de macOS no reemplaza esa prueba.

## Reproducibilidad

### Windows, Mac y cómputo — T01/T07/T12/T14

Python 3.11.18, uv y lock versionado. Base: NumPy, OpenCV contrib y YAML; extra ml: PyTorch y
torchvision. Mantener UTF-8/LF y pathlib; no rutas personales como interfaz compartida.
Cambiar dependencias con uv y versionar lock. Documentación sola no modifica dependencias.

Mac M2 Max/32 GB es objetivo de demo USB. MPS permite ejecutar operaciones de PyTorch en GPU
Apple; 32 GB es memoria unificada compartida con el sistema, no 32 GB exclusivos para redes.
Probar CPU/MPS, modelos residentes y modo evaluación/inferencia; precisión reducida solo tras
paridad. Core ML puede ser una optimización posterior, con recepción y medición propias.
Medir competencia entre visión y STT y no ocultar fallback a CPU como rendimiento GPU.

Windows CPU conserva núcleo/replay y pruebas. Una **VM** es una computadora virtual; solo
acelera estos modelos si tiene GPU/backend disponibles. Para entrenamientos/comparadores con
dependencias CUDA usar entorno NVIDIA separado cuando haga falta. FFS publica una ruta CUDA
con Python/dependencias diferentes; no forzarlas en el entorno base de la aplicación.
Créditos disponibles no confirman GPU ni autorizan gasto ilimitado: fijar presupuesto/coste
y tiempo máximo antes de corridas, apagar recursos y registrar consumo. No llevar el bucle
de interacción a nube por rutina.

**Decisión del 13/11.**
- **Fusion:** se entrena primero en la Mac (MPS), con overfit y un piloto que mida el tiempo por
  época. Si las semillas y ablaciones no entran en el calendario, pasar a Kaggle (2×T4,
  ~30 h/semana, checkpoints frecuentes) o a un proveedor pago.
- **Comparadores:** RunPod, RTX 4090 de 24 GB (≈USD 0,34/h en Community, cobro por segundo), con
  un entorno por modelo. Tope de USD 30 cargado por adelantado.
- **Por qué no T4 para FoundationStereo:** midió 10,5 GB a media resolución de Middlebury y usa
  flash-attn, que probablemente no soporta esa generación de GPU. Está sin verificar.
- Registrar horas y gasto de cada corrida.

### Artefactos compartidos

Código/configs/scripts por Git. Grabaciones, pesos y calibraciones de sesión por Drive
[VisionX-artefactos](https://drive.google.com/drive/folders/15dn-tT0PJ6tPDkqIhRCJdac5zugIf2Wp),
dueño Tomás y Bauty editor según registro. Falta lectura del hash de prueba desde Mac para
afirmar recepción en ambos equipos. Config local `artifacts.root`, carga explícita.

Subcarpetas existentes previstas: grabaciones, calibraciones, pesos, datasets, demos y _prueba.
Cada entrega tiene ID inmutable; si cambia, nueva versión. No reemplazar pesos/calibración
conservando el mismo ID. Esperar sincronización y verificar SHA-256, huella del contenido.
Evitar duplicar videos largos y vigilar cuota; no subir modelos/datos al repositorio.

Manifiesto futuro versionado junto a su tarea/config: ID, productor, tarea Txx, ubicación
compartida relativa, archivos con bytes/hash, commit, config, dataset/split y licencia, formato,
calibración/geometría, modelo/preprocesamiento, comando y salida/tolerancia esperada. Puede
guardarse en `configs/artefactos/<id>.yaml` cuando exista una entrega real; no crear plantillas
vacías repartidas ahora. El consumidor comprueba hash y registra recepción en BITACORA.

### Comandos disponibles y comprobaciones futuras

Hoy la CLI publicada ofrece doctor, log y novedades. Los dos últimos aún apuntan al esquema
documental viejo: no usarlos como bitácora/tablero vigentes. No hay CLI de cámara/modelos/modos
terminada; cualquier comando nuevo se documentará al implementarlo, no se inventa aquí.

Para preparar o comprobar una futura implementación (no ejecutar por leer este manual):

```text
uv sync --locked
uv sync --locked --extra ml
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run visionx doctor
```

Elegir base o ml según tarea. Los tests automáticos no requieren hardware/red/pesos. Un fallo
de modelo no se tapa omitiendo el test o presentando simulación como medición.

**Wheel** es el paquete instalable. La corrección PR #11 incluye default.yaml dentro del paquete;
fuera del checkout, `visionx doctor --runtime-only`. `--config archivo.yaml` permite elegir
override donde el comando lo ofrece; local.yaml nunca se busca automáticamente.

Recepción futura de instalación desde repositorio limpio y nombres de outputs propios:

```text
uv build --wheel --out-dir outputs/wheel
uv venv outputs/wheel-env
uv pip install --python outputs/wheel-env/Scripts/python.exe outputs/wheel/visionx-0.1.0-py3-none-any.whl
uv run python scripts/verify_wheel.py --python outputs/wheel-env/Scripts/python.exe
```

En Mac sustituir `Scripts/python.exe` por `bin/python`. No recrear un entorno ocupado ni
asumir el nombre de versión si el paquete cambió. El script usa cwd externo y modo aislado,
para no importar accidentalmente el checkout. Cinco comprobaciones históricas Windows:
import/defaults y doctor runtime retornan 0; doctor desarrollo sin Git, log sin checkout y
config inválida retornan 1 sin traceback/escritura externa. Repetición física Mac pendiente.

### Publicación y referencias

PR como registro de cambio, squash con checks técnicos y sin aprobación obligatoria del compañero.
No cambiar reglas remotas por editar documentos. Los hooks actuales incluyen tests antes de push;
una tarea documental sin ejecución local de tests debe publicar por una ruta que respete su alcance
y mantenga la validación documental, sin desactivar protección de main ni CI requerida.
Las referencias antiguas a `docs/CONTRATOS.md` llegan aquí mediante un enlace de compatibilidad.

La guía histórica externa de calibración es [i308-calib](https://github.com/udesa-vision/i308-calib).
Sirve como referencia; no implica que sus comandos estén implementados en VisionX.
Las propuestas originales de `entregas/` y PDF de materia se conservan sin regenerar; T16 debe
sincronizar alcance/números con evidencia antes de presentarlos de nuevo.

## Glosario

| Término | En nuestras palabras |
|---|---|
| CNN / U-Net | Red de convoluciones / arquitectura que reduce y recupera resolución |
| Preentrenado / congelado | Ya aprendió en otros datos / no actualizamos esos pesos |
| Residual | Corrección añadida a una solución base |
| Ancla / inlier | Medida de apoyo / medida que concuerda con el ajuste robusto |
| Máscara / cobertura | Píxeles elegidos / fracción con respuesta válida |
| Baseline | Puede significar referencia de comparación; B geométrica es separación física de cámaras |
| GT / pseudoetiqueta | Referencia de medida / salida de otro modelo usada para enseñar |
| Ablación / destilación | Quitar una pieza para evaluar su aporte / enseñar a un alumno con un teacher |
| Backend / CUDA / MPS / MLX | Motor de ejecución / plataforma NVIDIA / GPU Apple vía PyTorch / framework Apple |
| Checkpoint / hash | Archivo con estado/pesos / huella para verificar contenido |
| Inferencia / entrenamiento | Usar pesos para predecir / modificarlos con datos y una pérdida |
| Latencia / FPS / edad | Tiempo de respuesta / imágenes por segundo / tiempo desde la observación |
| API / Protocol / adaptador | Acuerdo de llamadas / interfaz estructural de Python / implementación que lo cumple |
| Replay / fake / fixture | Reprocesar grabación / sustituto controlado / ejemplo fijo para verificar |
| TTS / STT / VAD / OCR | Generar voz / transcribir voz / detectar actividad vocal / reconocer texto en imagen |
| VLM / LLM | Modelo de visión y lenguaje / modelo de lenguaje |
| Request / TTL / timeout | Pedido identificado / vigencia / límite de espera |
| CI / PR / worktree | Verificación automática / propuesta de cambio / copia de trabajo aislada del mismo Git |

Al introducir otro término o decisión, explicarlo aquí o en su sección antes de usarlo como
conocimiento supuesto. Actualizar BITACORA si cambian motivos, resultados o bloqueos.
