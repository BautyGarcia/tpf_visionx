# VisionX — bitácora de trabajo y evidencia

Este archivo cuenta **lo que ocurrió realmente**. Es la base para escribir después método,
resultados, problemas y discusión del informe final. [ROADMAP](ROADMAP.md) dice qué falta;
[TECNICO](TECNICO.md) explica el método previsto. Ninguno convierte una intención en resultado.

## Como mantenerla

- Agregar una entrada después de un avance significativo, intento fallido, bloqueo, cambio
  de decisión o traspaso. No hace falta esperar a que una tarea esté terminada.
- Entradas nuevas primero; fecha real y autor/persona/agente. Si es retrospectiva, decirlo y
  enlazar evidencia. No inventar horas, mediciones ni ejecuciones que no quedaron registradas.
- Conservar lo anterior. Una corrección se agrega indicando qué dato anterior reemplaza y por qué;
  no borrar una dificultad para que el historial parezca perfecto.
- Diferenciar planificado, implementado localmente, publicado/integrado y recibido por consumidor.
  Registrar qué quedó pendiente y qué necesita hardware. «El test pasó» no prueba una demo.
- Un editor por vez en este archivo. Si dos ramas agregaron entradas, conservar ambas al integrar;
  no reemplazar toda la bitácora por la copia de una rama vieja.
- Antes de publicar/traspasar una implementación, actualizar también el estado del bloque Txx.
  No duplicar aquí un segundo tablero con estados de veinte tareas.
- El registro es manual por ahora: `visionx log/novedades` todavía usan archivos antiguos y no
  mantienen este documento. Su adaptación futura pertenece a T01.

### Plantilla para copiar dentro de este mismo archivo

```text
## AAAA-MM-DD — tema breve
Tarea: Txx. Persona/agente: ... Rama/PR/commit: ...
Objetivo: qué intentábamos conseguir.
Hecho: cambios concretos y estado real (local/publicado/recibido).
Motivo: por qué elegimos este camino; alternativa descartada si corresponde.
Evidencia/resultados: comando o revisión realmente hecha, resultado, n/unidad y enlaces.
Contexto de una medición: equipo, config/hash, datos/split, modelo/calibración, resolución/backend.
Problemas/cambios: qué falló, impacto y decisión; sin ocultar resultados negativos.
Límites: qué no se probó, qué sigue siendo hipótesis o requiere hardware.
Próximo paso: acción concreta, responsable y dependencia si existe.
```

En documentación puede escribirse «sin pruebas de software ni mediciones; revisión de enlaces
y diff». En una medición real, conservar CSV/JSONL/artefacto verificable; un texto sin datos
no reemplaza la evidencia. No pegar secretos, pesos ni videos en esta bitácora.

## 2026-11-11 — Sesión s5 con damero A3 y calibración preliminar

**Tarea:** T03. **Personas/agente:** Bauty / Claude Code. **Rama:** `a/T03-calibrador` (local).

**Hecho.** Damero nuevo: PDF vectorial generado por el agente, 10×7 cuadrados (9×6 esquinas)
de 38 mm nominales, impreso en A3 y pegado sobre cartón. Cámara apoyada sin cinta. Sesión
`nov2026-s5`: 67 pares en bloques (cerca con giro lateral, media con giro vertical, esquinas y
bordes, lejos, girado en el plano). La detección en vivo de `calib-stereo` llega a ~1,4 m con
este tablero (busca al 70 % de resolución). Validación `nov2026-s5-val` pendiente.

**Evidencia/resultados** (OpenCV 5.0.0; `calibrar` solo con s5, validación interna de 13 pares).
- `revisar`: 67/67 pares detectados; esquinas de la imagen con 7–10 fotos (s2/s3 no cubrían
  bordes); inclinación mediana 24°; 0,35–1,70 m.
- Elegido `rational+refinado` (`elp-1920x1080-rational-728d71fe72`): RMS de ajuste 0,311 px
  (objetivo < 0,3), vertical mediana 0,121 px y P95 0,416 px en validación, escala +0,37 %,
  baseline 59,62 mm, 4 fotos descartadas (2 muy inclinadas, 1 movida, 1 con esquinas dudosas).
  `fisheye` falló al inicializar; no afecta la elección.
- Cruce entre sesiones: la calibración del 04/11 sobre s5 da vertical mediana 0,328 px (P95
  0,952), escala −0,26 %; sobre los bordes rinde peor que la nueva (transferencia 0,90 vs
  0,57 px). La de s5 sobre s2+s3 da 0,296 px (P95 0,838), escala +0,69 %.
- Estabilidad M3: baseline 59,82 → 59,62 mm (0,33 %, cumple < 0,5 %); focal 590,4 → 600,4 px
  en K izquierda y 589,8 → 600,9 en la derecha (≈1,7 %, **no cumple** < 0,5 %).

**Problema/hipótesis.** La focal cambió en los dos ojos por igual. Posibles causas, sin
comprobar: el foco se movió al poner o quitar cinta/precinto; el modelo `rational` reparte
la focal con los coeficientes de distorsión de forma distinta según qué zonas cubren las fotos;
el lado real del cuadrado impreso difiere de 38 mm (afecta escala, no focal). Calibración
guardada solo en el scratchpad del agente; no reemplaza todavía a `configs/calib/`.

**Pruebas sobre la focal** (scripts locales en el scratchpad, sin código nuevo en el repo).
Bauty confirmó con regla que el cuadrado mide 38 mm y la regla de control 100 mm, y que no
tocó las lentes desde el chequeo del 09/11 (cámara apoyada sobre la laptop, sin cinta).
- Modelo: recalibrando s2+s3, `pinhole5` da fx 586–589 y `rational` 590–594; s5 da 597–601 con
  ambos. La diferencia no depende del modelo.
- Ángulo que cada calibración asigna al mismo píxel: s5 da ángulos 1,5–2,0 % menores que la del
  04/11, parejo del centro al borde y en ambos ojos. No es un efecto de cobertura de bordes.
- Planitud: triangulando las esquinas en fotos a < 0,8 m, el A3 se aparta del plano ≤ 1 mm
  por esquina, sin curvatura clara (centro−borde +0,42 mm, ruido ~0,3 mm); el tablero viejo da
  lo mismo (+0,38 mm). No hay evidencia de que el cartón esté curvado.
- Identificabilidad: error por ojo de cada calibración sobre las fotos de la otra sesión:
  en s3, 0,199 (propia) vs 0,227 px (s5); en s5, 0,235 (propia) vs 0,297 px (04/11), igual con
  fotos ≥ 30°. Las dos focales explican casi igual de bien ambas tandas: el tablero a ≤ 1,7 m
  deja la focal determinada con ~2 % de margen, porque la pose compensa con la distancia.
- La calibración del 04/11 tiene fy/fx = 0,9956 (píxeles no cuadrados, poco físico); la de s5,
  1,0013. s5 tiene más inclinación y cobertura; se toma como candidata principal.
Impacto práctico: la escala cruzada difiere ~1 % (−0,26 % vs +0,69 %), unos 3 cm a 3 m.

**Actualización: validación s5-val y deriva horizontal.** `nov2026-s5-val`: 21 pares
(16:28–16:35; s5 fue 15:51–16:13), herramienta cerrada y reabierta entre ambas. Calibración
`calibrar --sesion s5 --validacion s5-val` → `rational` (`elp-1920x1080-rational-31c267f96f`,
local en `docs/i308-calib-tp2-antiguo/data/calib-s5.yaml`, ignorado por Git): RMS de ajuste
0,323 px; en s5-val vertical mediana 0,158 px (P95 0,646) pero **escala −2,47 %** y
transferencia 1,20 px; marcó 15 de 21 pares como movidos. Los seis candidatos de modelo dan
−2,4 a −2,6 %: no depende del modelo.
- Chequeo de fondo con la calibración de s5: vertical s5 −0,05 a +0,14 px, s5-val −0,20 a
  +0,06 px. En vertical la cámara no cambió.
- Corrimiento horizontal entre ojos que anula el error de escala de cada foto (script local):
  s5 fotos 1–18 +0,57 px; 19–36 +0,30; 37–49 −0,35; 50–59 −0,32; 60–67 −0,47; s5-val −1,31 px
  (20 de 21 negativos; dispersión por foto ~0,7–0,8 px). Deriva progresiva de ~1,9 px en
  ~45 min, en la dirección de la disparidad. Explica también por qué la calibración del 04/11
  rendía peor en las últimas fotos de s5.
- Impacto: 1,5 px de disparidad equivalen a ~4 % a 1 m y ~12 % a 3 m (fx·B ≈ 36 px·m).

**Hipótesis (no comprobada).** Deriva térmica: la cámara se calienta mientras está encendida
(y estaba apoyada sobre la laptop) y la placa o los portalentes cambian el ángulo horizontal
entre ojos. Es compatible con la diferencia de baseline entre s1 y s3 y con la de focal entre
el 04/11 y el 11/11, pero eso no está probado. Alternativa: asentamiento mecánico lento.

**Próximo paso.** Prueba de deriva con cámara fría: desconectarla ≥ 30 min, apoyarla en la
mesa (no sobre la laptop) con el tablero fijo a ~0,8 m, y capturar un par cada 30 s durante
45 min con `deriva_captura.py` (scratchpad del agente). Medir el corrimiento horizontal en
función del tiempo. Si se estabiliza, calibrar y medir siempre después de ese calentamiento.
Las calibraciones de s5 no se copian a `configs/calib/` hasta resolver esto.

**Actualización: prueba de deriva térmica (`deriva-1`).** Cámara desconectada ≥ 30 min, sobre
la mesa (no sobre la laptop), tablero A3 fijo a ~0,93 m con ~20° de inclinación, sin tocar
nada. `deriva_captura.py` guardó 90 pares, uno cada 30 s, de 17:04:42 a 17:49:22; tablero
detectado en los 90. Corrimiento horizontal equivalente medido con `calib-s5.yaml`
(el valor absoluto depende de esa calibración; importa cómo cambia):

| Minutos desde encender | Corrimiento (mediana) | Z medida |
|---|---|---|
| 0–1 | −1,15 px | 0,930 m |
| 1–2 | −0,91 px | 0,935 m |
| 2–3 | −0,70 px | 0,940 m |
| 3–5 | −0,51 px | 0,950 m |
| 5–15 | −0,41 a −0,42 px | 0,950 m |
| 15–25 | −0,48 a −0,55 px | 0,94–0,95 m |
| 25–35 | −0,59 a −0,62 px | 0,940 m |
| 35–46 | −0,65 a −0,66 px | 0,940 m |

Dos fases: un calentamiento rápido de +0,75 px en ~5 min y una deriva lenta de −0,25 px entre
los minutos 10 y 40, que se aplana al final (−0,65 → −0,66 en los últimos 10 min). El ruido
entre pares consecutivos es ~0,02–0,05 px. Con el tablero quieto, la distancia calculada cambió
un 2 % solo por temperatura. Sobre la mesa la deriva es menor que en s5, que estaba sobre la
laptop (~1 px en 20 min). La validación s5-val se sacó en los primeros minutos tras reabrir la
herramienta, con la cámara sin transmitir 15 min: compatible con el calentamiento rápido.

**Conclusión.** La deriva es real y térmica en su mayor parte. Dentro de los 3 m útiles,
0,25 px son ~0,7 % a 1 m y ~2 % a 3 m; el transitorio inicial completo (~1 px) llega a ~8 %
a 3 m. s5 y s5-val se tomaron con la cámara cambiando: no sirven como calibración final.

**Próximo paso.** Sesión s6 en régimen estable: cámara sobre la mesa, transmitiendo ≥ 40 min
antes de la primera foto, y calibración y validación en una sola corrida de la herramienta
(sin cerrarla; separar las últimas ~20 fotos después). Para la aplicación: precalentar la
cámara antes de medir o hacer la demo, y evaluar en T05 un control de deriva en funcionamiento.

## 2026-11-09 — La calibración del 04/11 ya no describe la ELP

**Tarea:** T03. **Personas/agente:** Bauty / Claude Code. **Rama:** `a/T03-calibrador` (local).

**Objetivo.** Empezar la sesión s4 (tablero apoyado, bordes, validación aparte, cinta a 1/2/3 m).

**Hecho.** Con `calib-stereo` la detección en vivo solo funcionó entre ~0,4 y ~1 m; se guardaron
3 pares (`nov2026-s4`, 0,42–0,95 m, de frente). Se midieron contra `elp-2026-11-04.yaml` y se
compararon con s2/s3 (scripts locales en el scratchpad, sin código nuevo en el repo).

**Evidencia/resultados.**
- Nitidez del tablero en s4 igual a s3 a la misma distancia (gradiente/contraste en las esquinas
  ≈3,0–3,2 en ambas): el foco y las lentes no cambiaron de forma visible.
- Con la calibración del 04/11, s4 da vertical mediana 2,34 px (P95 3,24) y escala −4,8 %;
  s2/s3 daban ~0,1–0,2 px. Los 3 pares tienen la fila derecha desplazada hacia el mismo lado
  (+1,7 a +3,0 px).
- Control independiente del tablero: puntos SIFT del **fondo quieto**, tras rectificar. s4:
  +2,4 a +2,7 px de desvío vertical mediano (~450–500 puntos por par). s2/s3: −0,1 a 0,0 px.
  No es movimiento del tablero: cambió la posición relativa entre los dos ojos (~0,24° de giro
  equivalente, 2,5 px / 590 px).
- El rango de detección en vivo (≤ ~1 m) coincide con el de s3 (0,45–1,03 m); s2 llegó a 1,5 m
  de frente. La herramienta busca a 70 % de resolución con búsqueda rápida; no indica falla.

**Problema.** `configs/calib/elp-2026-11-04.yaml` (referenciada en `configs/default.yaml`) no
sirve para la cámara en su estado actual: rectificaría con ~2,5 px de error vertical y la escala
también parece corrida (solo 3 pares, uno movido). Causa probable: presión de la
sujeción. Bauty informó que entre sesiones probó una vez sujetar la cámara con un precinto y
que ahora está atada con cinta; la presión sobre la placa o una lente puede torcer un ojo
respecto del otro. Es la causa más probable, todavía no comprobada. Solo 3 pares: la escala
no es concluyente. Las fotos s1–s3 y `elp-2026-11-04` siguen siendo válidas como registro de
la cámara al 04/11, pero no calibran su estado actual ni se mezclan con s4. Ningún módulo usaba
esa calibración, así que no hay otros resultados afectados.

**Actualización: la causa era la sujeción.** Bauty soltó la cámara y sacó 6 pares de una escena
quieta (`nov2026-s4/captures`, 19:36). Chequeo de fondo con `elp-2026-11-04`: desvío vertical
mediano −0,11 a −0,24 px (≈480 puntos por par), contra +2,3 a +2,8 px con la cinta y −0,08 a
+0,07 px en s2/s3. La cámara volvió prácticamente a su estado del 04/11; puede quedar un resto
≤ 0,2 px que estas fotos no distinguen del ruido. La escala no se midió (no había tablero).
Conclusión: la presión de la cinta/precinto torcía un ojo; al soltarla, vuelve. `nov2026-s4`
queda como diagnóstico de la cinta y no se usa para calibrar; la sesión de calibración nueva
va en `nov2026-s5`. s1–s3 vuelven a ser comparables con la cámara actual.

**Próximo paso.** Fijar la cámara sin presionar la placa ni las lentes.
Recalibrar con una sesión completa (≈70 pares + 20 de validación) sin tocar el foco. Para la cinta métrica
a 1/2/3 m usar un marcador ArUco grande en vez del damero, que no se detecta lejos.
Proteger la cámara (foco trabado, estuche rígido) y repetir el chequeo de fondo antes de cada
sesión de medición para saber si vuelve a moverse.

## 2026-11-04 — Primeras sesiones de calibración ELP y calibrador propio

**Tarea:** T03. **Personas/agente:** Bauty y Tomás / Claude Code. **Rama:** `a/T03-calibrador`
(local, sin publicar al escribir esta entrada).

**Objetivo.** Calibrar la ELP en la Mac y bajar el error por debajo de 0,5 px.

**Hecho.**
- ELP en Mac por AVFoundation, 3840×1080 (1920×1080 por ojo). El índice de cámara cambió
  entre 0 y 1 al reconectar: elegirlo por la imagen, no por el número.
- Damero 10×7 cuadrados (9×6 esquinas internas), cuadrado de 28 mm medido con regla.
- Sesiones con `calib-stereo` de la cátedra, guardadas fuera de Git porque tienen personas:
  s1 (67 pares, tablero en la mano), s2 (29 pares, lejos y de frente), s3 (38 pares, quieto,
  inclinado, 0,45–1,06 m).
- Calibrador propio en `src/visionx/calibration/` (`python -m visionx.calibration`):
  detector preciso a resolución completa, limpieza con motivo por foto (ojo izquierdo/derecho,
  movimiento entre ojos, inclinación > 65°), modelos pinhole5/rational/fisheye elegidos por
  error vertical en validación, métricas M3, YAML en metros con hashes de las fotos y
  `StereoCalibration.geometry()` hacia la geometría compartida. 19 tests sintéticos nuevos.

**Evidencia/resultados** (OpenCV 5.0.0, Mac M2 Max; validación = pares no usados en el ajuste).
- Herramienta de la cátedra, s1 completa: RMS 2,70 px. Con 52 pares tras quitar 15 movidos o
  muy inclinados: 0,634 px.
- Calibrador propio sobre las 67 fotos de s1: descartó solo 16, con motivo, y marcó como movidas
  las 4 de validación que habíamos quitado a mano. Sobre los 52 pares: RMS 0,370 px,
  vertical mediana en validación 0,129 px.
- Calibrar cada ojo solo da 0,26 px: el error estéreo extra venía del movimiento del tablero.
- s3 sola: RMS 0,217 px; validación vertical mediana 0,191 px (0,142 sin 2 fotos movidas);
  escala −0,01 % sin movidas.
- s2 sola es degenerada (focal ~9000 px): sin inclinación la focal no queda determinada.
- Prueba cruzada justa (calibrar con s1, medir sobre s3): cátedra 0,185 px vertical y
  escala −1,72 %; propio 0,195 px y −1,58 %. **Fuera de su sesión los dos métodos rinden igual.**
- Entre sesiones: fx 593,1 vs 593,6 px (0,08 %, cumple <0,5 %); baseline 60,1 vs 59,3 mm
  (1,3 %, no cumple). La calibración de s3 mide s1 +2,2 %, y la de s1 mide s3 −1,6 %.

**Problemas/cambios.**
- La tecla `a` mantenida guarda varias fotos por segundo con el tablero en movimiento.
- La primera medida de escala (lado entre esquinas vecinas) tenía sesgo positivo por el ruido
  de profundidad: +0,56 % con datos sintéticos perfectos. Se reemplazó por ajuste de
  similitud del tablero completo (Umeyama). Las escalas anteriores a ese cambio no se usan.
- En OpenCV 5 las constantes fisheye pasaron de `cv2.fisheye` a `cv2`; el código busca ambas.

**Límites.** Sin cinta métrica todavía: la escala sobre el propio tablero no valida metros.
Hipótesis no comprobada: s1, con el tablero en la mano, tiene un desfasaje lento que sesga
la baseline; también podría haber cambiado el foco o el tablero entre sesiones.
Fotos y calibraciones solo locales; no subir imágenes con personas.

**Próximo paso.** Sesión s4 con el tablero apoyado e inclinado, cubriendo esquinas y bordes,
y 20 pares de validación aparte. Calibrar s3+s4, medir sobre una sesión no usada y medir
objetos a 1/2/3 m con cinta. Confirmar si s1 y s3 usaron el mismo tablero y el mismo foco.

**Actualización: calibración elegida con s1, s2 y s3.** Se calibraron todas las combinaciones
y cada calibración se midió sobre cada sesión (`comparar`). s2 sola no calibra (tablero casi
de frente: inclinación mediana 7°, ninguna foto ≥ 20°), pero sus fotos son limpias. s2 y s3
coinciden entre sí: la calibración de s3 mide s2 con escala −0,10 %. s1 se aparta: lo calibrado
con s1 mide s2/s3 entre −1,6 % y −2,4 %, y lo calibrado con s2+s3 mide s1 a +1,8 %. La
herramienta de la cátedra (ajustada con s1) hereda ese sesgo. La persona aclaró que entre
sesiones se movió la computadora/cámara; eso no afecta la calibración si no se tocó el foco.
Se eligió s2+s3 (`rational+refinado`, `elp-1920x1080-rational-cc425d4937`): RMS de ajuste
0,199 px (cumple < 0,3), validación interna de 14 pares con vertical mediana 0,159 px
(0,115 px sin 3 fotos movidas), escala +0,11 %, baseline 59,82 mm. Copiada a
`configs/calib/elp-2026-11-04.yaml` y referenciada en `configs/default.yaml`.
Límite: la elección entre s1 y s2+s3 se basa en que dos sesiones coinciden; solo la cinta
métrica confirma cuál mide bien. Todavía ningún módulo lee `camera.calibration`.

## 2026-11-02 — Planificación simplificada y registro único

**Tarea:** reorganización documental autorizada por Tomás, relacionada con T01/T16.
**Persona/agente:** Tomás / Codex. **Rama:** `b/docs-plan-simple`.

**Objetivo.** Cerrar la planificación técnica y hacer el repositorio comprensible para el equipo.
Tomás aclaró que ahora quiere qué hacer, por qué, entradas/salidas y qué pruebas realizar;
no quiere implementar etapas futuras ni ejecutar sus pruebas en esta tarea.

**Hecho en esta revisión.** Se redactaron ROADMAP con veinte bloques, TECNICO con el recorrido
de datos y explicaciones sencillas, y esta BITACORA. Se simplifican README/AGENTS/CLAUDE y
las instrucciones del PR. Se consolidan contratos, métricas, artefactos, integraciones,
auditorías y decisiones; se retiran sus fichas duplicadas de la navegación vigente.
Los originales siguen en Git y los IDs se relacionan al final de ROADMAP.

**Motivo.** Había setenta fichas A/B más tableros, índices e instrucciones separadas.
Eso obligaba a recorrer varios archivos para entender una capacidad y había estados desactualizados.
La complejidad del proyecto científico se mantiene; se reduce su representación administrativa.
Las novedades técnicas se integran dentro de los veinte bloques, sin crear otra colección de tareas.

**Decisiones.** Dos recorridos de ejecución, interactivo y comparación científica; DA V2 Small
congelada; CNN residual con F0/F1 y variantes experimentales; cuatro comparadores; cuatro modos
USB antes del portátil. Las elecciones de detector, backends y canales extra son candidatos a
validar, no mejoras medidas. Lite/Fusion-FFS/Pi/batería/alerta siguen comprometidos. Sin SLAM/memoria.

**Problema detectado.** Codex interpretó antes «Implement the plan» como autorización para
adelantar código de varias etapas, cuando Tomás buscaba planificación. Se escribieron módulos
y se iniciaron verificaciones en el worktree local `C10-base-tecnica`. Tomás detuvo ese alcance.
Ese código no fue commiteado ni publicado y no se toma como funcionalidad aceptada.
Se conserva aislado; esta publicación no lo mezcla ni lo elimina. Nueva regla: distinguir
planificación de implementación antes de actuar y registrar también los intentos detenidos.

**Estado de Git comprobado al comenzar.** Main local/remoto coinciden en `526facc`; PR #9,
#10 y #11 ya estaban integrados. Algunas notas antiguas aún los describían como pendientes:
esta revisión corrige esa lectura. No se recibieron mediciones nuevas de ELP, Mac, voz ni modelos.

**Verificación de esta revisión.** Nueve archivos Markdown vigentes revisados, 35 enlaces
locales válidos, veinte bloques/veinte filas de estado y los setenta IDs A/B previos cubiertos.
`docs/` pasa de 101 Markdown a cuatro: tres documentos principales y el enlace de compatibilidad
de contratos. Ningún cambio de código/config/tests/dependencias. `git diff --check` correcto.
El resultado y el estado de publicación se pueden consultar en el PR asociado al commit.
No se ejecutan tests locales, entrenamiento ni mediciones físicas para esta reorganización.
Las verificaciones automáticas que GitHub ejecute por su configuración se distinguirán de esas pruebas.

**Organización.** Se usó una copia temporal aislada porque el control automático rechazó
`git switch` en la carpeta habitual al requerir aprobación no disponible. No es un requisito
de leer cinco carpetas. Tras publicar, actualizar la carpeta habitual y abrir ROADMAP/TECNICO.
No retirar worktrees de otras tareas con cambios pendientes.

**Próximo paso.** El equipo lee el plan y elige qué bloque implementar. T01 recibe contratos/
artefactos; T02/T03 comprueban cámara; T04/T05/T14 avanzan con datos públicos. Ninguno se
declara iniciado por haber escrito este plan. Publicación se comprueba en el PR y el historial
de este archivo; no se presupone una recepción técnica de Bauty.

## 2026-10-30 — Correcciones publicadas y límite de la evidencia

**Registro retrospectivo consolidado el 02/11**, a partir de los registros originales y Git.
Tareas anteriores A04.1–A04.6 y B27.1; hoy T01 y preparación de T16. Tomás / Codex.

**Hecho.** PR [#10](https://github.com/BautyGarcia/tpf_visionx/pull/10), commit `d8a38bd`,
publica schema 3: d+doffs, recortes con centro fuera de imagen, P1/P2 canónicas verificadas,
IDs/enums, arrays estables y geometría de detecciones. También reloj manual sin truncamiento,
desbordamientos y comprobación de coherencia Z/disparidad.

PR [#11](https://github.com/BautyGarcia/tpf_visionx/pull/11), commit `526facc`, publica default
dentro del wheel, override explícito, doctor runtime, validación YAML y comportamiento fuera
del checkout. Corrige un problema del registro que truncaba el primer nombre de archivo al
quitar columnas iniciales de `git status`.

**Motivo y problema.** Contratos inconsistentes podían rechazar disparidades físicamente
válidas; un array congelado podía cambiar si el emisor reutilizaba memoria; una instalación
fuera del checkout no encontraba sus defaults. Se priorizó corrección/legibilidad sobre
optimización de copias. Los snapshots tienen un coste de memoria todavía pendiente de medir.

**Resultados históricos.** A04 registró 185 tests; instalación, 150 en su rama; conjunto, **197**
en Windows. Las cifras se solapan y no se suman. Formato/lint/doctor correctos en los registros.
Wheel conjunto: cinco verificaciones aisladas con retornos esperados; SHA-256 local registrado:
`9e5465142bb77e041d630771fc4dc101ecad95b5325efd6a442c222038d628f4`.
Este hash identifica un archivo local, no confirma publicación del wheel en Drive.

**Límites.** Pruebas de lógica/sintéticos/instalación; no son precisión Fusion ni FPS ELP.
Recepción de schema 3 y wheel en Mac física pendiente. No cambiar a hecha toda T01 por estos PR.

**Fuentes originales:** [A04](https://github.com/BautyGarcia/tpf_visionx/blob/526facc82abf803c94271a25a784de1377484617/docs/log/2026-10-30-1156-tomaasgonzalezzz-correcciones-de-geometria-y-contratos-schema-3.md),
[instalación y conjunto](https://github.com/BautyGarcia/tpf_visionx/blob/526facc82abf803c94271a25a784de1377484617/docs/log/2026-10-30-1157-tomaasgonzalezzz-instalacion-wheel-y-configuracion-explicita.md).

## 2026-10-29 — Alcance completo, entrega USB y almacén

**Registro retrospectivo consolidado el 02/11.** Anterior C05/C09; hoy T01 y roadmap.

Tomás confirmó ELP disponible y entrega el 10/12/2026. Se acordó primera versión USB con los
cuatro modos; portátil, Lite, Fusion-FFS y alerta continúan comprometidos después si faltan.
Se hizo explícita la entrada DA V2 Small y los cuatro comparadores. La reorganización C09
se publicó en PR [#9](https://github.com/BautyGarcia/tpf_visionx/pull/9), commit `3034f40`.

Esa revisión separó setenta fichas para paralelizar, pero resultó demasiado fragmentada para
la lectura del equipo. La decisión documental del 02/11 la reemplaza; no invalida los objetivos
ni borra su historial. La propuesta HTML/PDF no se regeneró entonces y sigue por sincronizar.

Drive `VisionX-artefactos`, Tomás dueño y Bauty editor, quedó documentado en PR
[#8](https://github.com/BautyGarcia/tpf_visionx/pull/8), `a55d7be`. Archivo `_prueba/C05-prueba.txt`
leído en Windows; SHA-256:
`9037805d44459f3aca6d40f880c4625c5cb01d694cb47f36069d79f4494c537c`.
**Pendiente:** que la Mac lea el mismo hash. No afirmar recepción por compartir solo un enlace.

**Fuente original:** [registro C09](https://github.com/BautyGarcia/tpf_visionx/blob/526facc82abf803c94271a25a784de1377484617/docs/log/2026-10-29-c09-plan-completo.md).

## 2026-10-28 — Base, responsabilidades, entornos y primeros contratos

**Registro retrospectivo consolidado el 02/11.** Resume siete notas originales de ese día;
sus detalles y comandos permanecen en [Git histórico](https://github.com/BautyGarcia/tpf_visionx/tree/526facc82abf803c94271a25a784de1377484617/docs/log).

- Bauty creó entorno/paquete, contratos iniciales, diagnóstico, hooks y registro. A se asignó
  datos/profundidad/CNN/evaluación; B, cámara/aplicación/hardware. Hoy eso define integración,
  no limita qué agente puede ejecutar una tarea delegada.
- La planificación C03 distribuyó 29 tareas A y 28 B más compartidas/integraciones. PR #2
  `ac66b96`. Se reemplazó la aprobación cruzada obligatoria por checks y recepción técnica.
- Windows: uv/Python 3.11.18, NumPy/OpenCV, ChArUco/WLS, hooks y 14 tests registrados.
  Hubo problema de PATH/selección de Python y se resolvió con versión exacta y configuración
  de usuario, sin borrar instalaciones. Doctor se corrigió para fallar si faltaban hooks.
- Bauty registró Mac física M2 Max/32 GB, macOS 15.7.3 arm64, Python 3.11.18 y MPS disponible;
  14 tests y doctor correctos. Esa prueba no incluye la futura aplicación concurrente.
- La inspección inicial de GitHub no tenía protección efectiva; luego Bauty habilitó ruleset
  `proteger-main`. Se registró PR obligatorio, cero aprobaciones, squash y checks Ubuntu/
  Windows/macOS requeridos. No confundir la primera limitación con el estado corregido.
- Contratos schema 2 se publicaron en PR #6 `22c956a`; el registro de Bauty informa 138 tests
  macOS, geometría sintética y casos adversos. Schema 3 del 30/10 los reemplaza semánticamente.

**Problemas que siguen pendientes:** calibración y captura ELP, modelos/voz/aplicación,
recepción de cambios recientes en Mac y aprobación/formato definitivos de la cátedra.
No se traslada una prueba histórica de entorno como si acreditara esas capacidades.

## Regla para el siguiente informe

Cada cifra del informe final debe remitir a una entrada/run/artefacto con condiciones de
medición. Si cambiamos una decisión, describir motivo y efecto. Si una capacidad no se
termina o una hipótesis falla, escribirlo junto con lo que sí se demostró. Así el informe
se construye desde la experiencia real y no desde lo que habíamos prometido hacer.
