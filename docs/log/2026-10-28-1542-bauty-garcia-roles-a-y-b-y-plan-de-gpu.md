---
fecha: 2026-10-28 15:42
autor: Bauty Garcia
agente: claude-code
rama: a/C02-roles
tarea: C02
---

# Roles A y B, y plan de GPU

## Qué se hizo
- A = Bauty (más cercano a lo programático): datos, red y evaluación.
- B = compañero (más cercano al hardware): cámara, aplicación y hardware.
- Nadie tiene GPU NVIDIA: lo que necesita CUDA va a una VM con GPU.

## Archivos cambiados
- `AGENTS.md`
- `GENTS.md`
- `docs/coordinacion/TAREAS.md`

## Decisiones tomadas (y por qué)
- Se mantiene la división de áreas del plan; solo se asignan nombres.
- Sin CUDA local: los modelos grandes quedan para entrenar y comparar en VM; la demo en vivo corre en la Mac con MPS.

## Cómo probarlo
No aplica: solo documentación.

## Pendiente / próximo paso
- Sumar a TomaasGonzalezzz como colaborador con permiso Write (si no, CODEOWNERS no lo reconoce).
- Activar "Require review from Code Owners" en el ruleset de main.
- Elegir proveedor de VM con GPU cuando haga falta (comparación con U1–U3 y entrenamiento si Kaggle/Colab no alcanza).

## Avisos para el otro
<!-- cambios en contratos, dependencias nuevas, cosas que rompen o que tiene que saber -->
- Sos B: tus tareas arrancan en la sección B de TAREAS.md (B01 a B03).
