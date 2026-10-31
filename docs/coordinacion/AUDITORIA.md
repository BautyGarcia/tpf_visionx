# Auditoría y tareas técnicas — 29/10/2026

Base a55d7be. Windows: 138 tests en 6,79 s; ruff/formato/doctor correctos.
Python 3.11.18, NumPy 2.4.6, OpenCV 5.0.0, sin torch. No hardware ni ML medidos.
Implementado: contratos/geometría/entorno; no pipeline de producción.

| ID | Hallazgo | Aceptación |
|---|---|---|
| A04.1 | Reproducido: fx=100 B=.06 doffs=10 Z=1 produce d=-4 válido en depth_at, rechazado en inversa/contrato | Ida/vuelta y contrato consistentes con d+doffs |
| A04.2 | Reproducido: crop esquina 20x20 de 100x100 rechaza cx=49.5 | Principal fuera del crop permitido; límites del recorte comprobados |
| A04.3 | Reproducido: P2 admite fy distinto y NaN | Finitud y forma soportada validadas |
| A04.4 | Reproducido: IDs vacíos y uncertainty_kind desconocido admitidos | Enums/IDs y entradas adversas cubiertos |
| A04.5 | Reproducido: mutar array cambia frame frozen | Propiedad de buffers y estabilidad antes de B11 |
| A04.6 | Riesgo: Detection sin referencia de transformación | Contexto público; rechazar máscara de otra geometría |
| B27.1 | Riesgo estático: defaults fuera del paquete y ROOT basado en checkout | Wheel aislado/config explícita probados |

Referencias fuente: geometry.py:54,83,118,178; contracts.py:80,118,176,195,229;
config.py:10 en src/visionx/shared/. Reproducciones sintéticas en memoria.
A integra shared con requisitos B. No se cambia código en C09. Pruebas nuevas deben
cubrir estos casos y la regresión existente. Mac C04 es evidencia histórica: repetir
pipeline actual/MPS; faltan ELP, calibración independiente, audio audible y modelos.

## Diagnóstico de arquitectura y proceso

Conservar monolito modular, Protocols, contratos, replay, fakes, PR/CI y artefactos con hash.
No hay evidencia que justifique microservicios, bus genérico o migración masiva de carpetas.
La complejidad evitable era de coordinación: dependencias por etapa completa, especificaciones
y estados mezclados en A/B, y recepción confundida con disponibilidad de API. C09 separa
fichas, preserva estados y permite múltiples agentes con responsabilidades/rutas claras.

Mantener ejecución secuencial determinista para replay/evaluación y adaptador vivo con colas
acotadas. Unir detección/depth por identidad y transformación, nunca por el último resultado
independiente de cada servicio. Captura prioriza actualidad; distancia congela par; controlador
invalida pedidos; una cola de audio gestiona prioridad/TTL/cancelación. GUI observa, no decide.

## Riesgos científicos pendientes de experimentación

No se ha demostrado complementariedad SGBM/monocular, robustez del alineamiento,
transferencia de normalización entre cámaras ni calibración de incertidumbre ELP.
Auditar canales/rangos/NaN, cantidad y distribución de anclas; overfit y piloto antes de
corridas largas. Intervalos por píxel no equivalen a confianza por objeto. Evitar ajuste sobre
test; comparar cobertura junto con error y tratar repeticiones por escena/objeto como grupos.
Tres ensayos y replay offline respaldan demo, no demuestran superioridad científica.

## Verificación documental C09

Enlaces Markdown locales y anclas: sin errores. IDs/estados anteriores preservados;
70 tareas indexadas con ficha, sin estados duplicados en fichas; una plantilla adicional.
Lector real de novedades compatible y git diff --check correcto. No se reejecutaron tests
científicos o físicos para documentación ni se modificó src/tests/configs/dependencias.

## Seguimiento técnico — 30/10/2026

A04.1–A04.6 tienen implementación y regresiones locales en `a/A04-auditoria` (base 3034f40).
No se cambió el estado oficial en A.md: falta integración y recepción I00.
[Guía de migración](RECEPCION-A04.md) y [mejoras preventivas](MEJORAS-PREVENTIVAS.md).
B27.1 se implementó y verificó aparte en `b/B27-instalacion`; recepción Mac/I08 pendiente.
Los resultados físicos/ML de esta auditoría siguen sin ejecutarse.
