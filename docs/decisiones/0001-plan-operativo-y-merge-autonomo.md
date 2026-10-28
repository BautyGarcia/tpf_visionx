# 0001. Plan completo y merge autónomo con recepción técnica

- Fecha: 2026-10-28
- Responsable: Tomás (B), por indicación directa del usuario.
- Estado: aceptada como criterio de planificación; aplicación remota pendiente de C04.

## Problema y decisión

El tablero inicial solo enumeraba seis tareas y exigía revisión cruzada. Se completa A01-A29,
B01-B28 e I00-I08, conservando IDs iniciales. Cada ficha define dependencia, salida y métricas.
Se elimina aprobación obligatoria del compañero: el autor integra por PR con checks. WhatsApp/en
persona sirven para coordinar; los documentos conservan decisiones e información de interfaces.

No se confunde recepción con aprobación: el consumidor ejecuta un caso del módulo recibido.
Una tarea implementada queda por integrar hasta cumplir ese traspaso. Archivo compartido se
reserva a un editor. Cada agente simultáneo tiene rama y worktree propios.

## Diseño vigente y alcance

Fusion residual de 10 canales es principal; Lite de 7 canales como red principal pertenece a
la propuesta visual anterior. Se mantiene la aplicación USB de cuatro modos. Lite, Fusion-FFS
y wearable se deciden por presupuesto/evidencia; no se declaran implementados. C06 confirma
alcance académico, equipo y fecha; C07 congela protocolo antes de entrenar/evaluar.

## Evidencia y límites

Base inspeccionada: bf9d43a (C02 ya integrado). No se afirma que GitHub haya cambiado reglas
remotas ni que las tareas planificadas estén terminadas. Contratos objetivo se implementan en
A04; esta decisión no cambia schema de datos ni modelos existentes. CI amplía núcleo a tres SO.

## Reversibilidad

Cambiar alcance/contrato requiere nueva decisión y tareas afectadas, sin renumerar IDs ni borrar
resultados negativos. Puede restablecerse revisión humana por acuerdo, pero no es requisito de
este flujo. Los agentes conservan la regla de no commitear/pushear sin pedido explícito.
