# Flujo Git: autonomía e integración

## Empezar sin interferir

Un clon por PC; un worktree por agente simultáneo. Con árbol limpio, desde el clon coordinador:

```text
git fetch origin
git worktree add ../visionx-b-B02 -b b/B02-replay origin/main
```

Trabajar en esa carpeta con su entorno/outputs; A usa a/Axx-tema. Nunca cambiar la rama del
checkout ajeno. Antes de integrar: `git fetch origin` y `git merge origin/main` en rama propia;
preservar ambos cambios al resolver conflictos. No rebase de ramas compartidas ni force push.
Para actualizar el clon en main limpio: `git pull --ff-only`.

## Estados

En la ficha A/B: checkbox y `estado: pendiente | en curso | por integrar | bloqueada | hecha |
no aplica`. `[x]` solo hecha/no aplica (con motivo). ID y enlaces no se renombran. La persona o
coordinador actualiza su fichero; agentes de implementación no editan el mismo tablero a la vez.
Los pedidos se hablan por WhatsApp/en persona; solo se registran dependencias/decisiones duraderas.

## Merge y traspaso

1. Productor implementa, verifica y registra config, métricas y artefacto/hash.
2. PR con diff y checks. Autor hace **squash merge sin aprobación del compañero**. Main solo
   recibe cambios compatibles; contrato primero, adaptadores después.
3. Productor comunica: ID + commit integrado + artefacto/hash + comando + salida esperada + Ixx.
4. Consumidor incorpora main a su rama, obtiene artefactos y ejecuta recepción.
5. Registrar recepción Ixx. Si pasa, tarea hecha; si falla, corrección con input reproducible.
   Mientras el consumidor no está listo, tarea por integrar y resto del sistema usa fake.

Ejemplo: A18 publica modelo; B13 lo carga y registra I04. B no tiene que aprobar el entrenamiento.
Con B09/A07 se hace lo mismo para calibración. **No hacer merges cruzados A->B/B->A: pasar por main**.

## Compartidos y cambios incompatibles

Reservar editor de shared/, cli.py, lock, CI y documentos comunes. Configs específicas en archivos
separados. Cambiar semántica: incrementar schema, fixture/migración y aviso al consumidor.
Una versión nueva no convierte datos viejos sola. Retener lectura compatible hasta cerrar el hito
si es viable. Mantener main ejecutable con fakes cuando faltan pesos o cámara.

## Ajustes remotos objetivo (C04)

- PR requerido en main; **0 aprobaciones**, sin code-owner review obligatorio.
- Checks requeridos: core-ubuntu-latest, core-windows-latest, core-macos-latest cuando existan.
- Squash permitido; bloquear force push/borrado de main. No usar revisión humana como gate técnico.
- Administrador verifica Settings/Rulesets/Branches. CODEOWNERS/hooks locales no cambian eso.
  Verificado el 28/10/2026: main **sin protección**; CI ejecutada pero no requerida. Rulesets
  no habilitados en el plan privado actual. Evidencia y pendientes: [C04.md](C04.md).

Agentes no commitean/pushean salvo pedido explícito para su tarea. Esa regla no obliga a pedir
aprobación al compañero. No saltarse checks para integrar un cambio.
