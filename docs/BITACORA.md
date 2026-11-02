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
