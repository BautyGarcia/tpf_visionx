# VisionX — instrucciones para personas y agentes

## Leer antes de actuar

1. [ROADMAP](docs/ROADMAP.md): estado, tarea T01–T20, dependencias y entrega esperada.
2. [TECNICO](docs/TECNICO.md): sección del componente, entradas/salidas y pruebas previstas.
3. [BITACORA](docs/BITACORA.md): últimas entradas, bloqueos y cambios de decisión.
4. `git status` y `git diff`; leer `TRASPASO.md` si existe. No tocar cambios ajenos.

**Leer un plan no autoriza implementarlo.** Respetar el pedido concreto de la persona:
planificación = documentación; implementación = código del alcance solicitado.
Para documentación revisar enlaces, coherencia y diff; no ejecutar tests, modelos ni hardware
salvo pedido expreso. GitHub puede ejecutar su CI automáticamente al publicar un PR.

## Responsables y paralelismo

- **Bauty (A):** datos, `depth/`, CNN, evaluación y `depth/spatial/`.
- **Tomás (B):** cámara, calibración, detección, voz, modos, GUI, transporte y CLI.
- Tests/configs/scripts siguen al módulo. `shared/`, dependencias, CI y documentos son compartidos.
- A/B coordinan integración; no limitan el número de agentes ni obligan a repartir tareas por mitades.
- Antes de editar, registrar en el bloque del ROADMAP: ejecutor, rama, rutas y recursos reservados.
  Un agente comunica cambios de decisión/interfaz compartida al consumidor.
- Una carpeta habitual por persona. Solo si hay agentes editando en paralelo, usar un worktree
  separado por ejecución y rutas no superpuestas. Nunca cambiar de rama en el checkout ajeno.
  No crear ni mantener carpetas adicionales por rutina. Revisar cambios antes de retirar una.
- Reservar cámara, micrófono, GPU y outputs aparte: Git no aísla hardware.
- Para documentos compartidos, un editor a la vez; los demás entregan notas al coordinador.
  En BITACORA agregar entradas propias, conservar las ajenas y resolver conflictos sin borrarlas.

## Git y aceptación

- Rama propia desde `origin/main` actualizado: `a/Txx-tema` o `b/Txx-tema`.
- Sin commits/push directo a `main`, force push, reset destructivo, secretos, pesos ni datos grandes.
- Agentes commitean/pushean solo cuando la persona lo pide para la tarea. Publicar por PR;
  el autor puede integrar con checks correctos, sin aprobación obligatoria del compañero.
- Commits `tipo(área): descripción en español`; sin firmas ni coautoría de herramientas.
- Una tarea se termina con entrega verificable y evidencia. Distinguir código integrado de
  recepción pendiente; CI no prueba cámara, Mac física, MPS, micrófono ni latencia audible.
- Reutilizar contratos públicos existentes, hoy schema 3. Cambios semánticos requieren versión,
  fixture y migración. No inventar mensajes paralelos ni importar privados del otro módulo.

## Registro obligatorio

Después de un paso significativo y antes del traspaso, actualizar **BITACORA** con fecha,
persona/agente, tarea, qué cambió, por qué, evidencia/resultados y limitaciones, problema o
bloqueo y próximo paso. También se registran intentos fallidos, cambios de rumbo y pausas.
Si no hubo pruebas, escribirlo. No anunciar planes como hechos ni completar métricas supuestas.
ROADMAP conserva el estado actual; BITACORA explica cómo llegamos a él. Ver plantilla en ella.
Un `TRASPASO.md` local es opcional, corto e ignorado por Git; no reemplaza el registro compartido.

## Implementaciones futuras

Python 3.11, `uv` y lock versionado; parámetros en configs, overrides locales explícitos,
UTF-8/LF y rutas portables. Código didáctico, nombres claros y comentarios sobre razones,
unidades y transformaciones. Tests automáticos sin cámara, GPU, internet ni descarga de pesos.
Mediciones físicas con equipo, commit, config, hashes, n y unidades. Si falta hardware,
usar un fake rotulado y conservar la medición pendiente. Elegir verificaciones pertinentes
cuando se implemente; no ejecutarlas durante una tarea exclusivamente documental.

`visionx log` y `visionx novedades` son herramientas heredadas que todavía leen la estructura
anterior. No usarlas como fuente oficial: actualizar los tres documentos directamente.
Su adaptación está registrada dentro de T01; esta simplificación no cambia código funcional.
