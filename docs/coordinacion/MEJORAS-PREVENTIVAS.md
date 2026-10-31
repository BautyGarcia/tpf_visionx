# Mejoras preventivas y próximos pasos — 30/10/2026

El objetivo sigue siendo el TP funcional y evaluado, no crear infraestructura adicional.
Esta revisión cubre el código actual (shared, CLI/config, registro y tests) y contrasta el plan
para los módulos futuros. No hay mediciones nuevas de modelos ni hardware.

## Corregido localmente

A04.1–A04.6: geometría/doffs, recortes, P1/P2, validación, snapshots y contexto de detección;
schema 3 y fixture de recepción. Se añadió protección ante desbordamientos y reloj manual
sin truncamiento de fracciones. B27.1 (rama independiente) resuelve defaults del wheel,
overrides explícitos, diagnóstico runtime y registro fuera del checkout.
No están en main hasta que se autorice su publicación. Mac/I00/I08 siguen pendientes.

## Próximo trabajo con más retorno

| Prioridad / tarea existente | Acción concreta | Aceptación |
|---|---|---|
| 1 · A05/A06 y B02/B04/B05 | Completar un recorrido replay determinista: objeto, profundidad, ubicación, evento y cancelación | M0/M1; mismo input produce mismos eventos; cubrir resultados fuera de orden, EOS y datos viejos |
| 1 · B01/B08/B09/B10/A07 | Capturar ELP real, validar ojos/modos y calibrar con tablero medido | M2/M3/M7; referencia externa de Z y sesiones separadas; no usar FPS ni focal nominal como medición |
| 1 · A12/A18/B13 | Una implementación pública de preprocesamiento para entrenamiento y aplicación | Fixture de paridad por canal y salida; hash de config/datos/calibración invalida cache |
| 1 · B05/B11/B19 | Controlador único para request/TTL/cancelación; unir detección/depth por frame y contexto | 0 cruces de frames ni audio cancelado/vencido en escenarios; colas acotadas bajo carga |
| 2 · B11/B21 | Medir coste de snapshots, memoria y edad antes de diseñar zero-copy | M9: resolución, bytes, P50/P95 y carga; buffers compartidos solo con propiedad/lifetime probados |
| 2 · B06/B13/B15/B17/B18 | Arranque comprueba pesos/hash/modelo/backend; distinguir ausencia de objeto de fallo | Error explícito/fallback medido; fakes y tests sin descargas; no fallar durante la demo por peso ausente |
| 2 · B18/B19 | Componer números/unidades con mediciones estructuradas; VLM solo aporta descripción | Casos con contradicción, timeout y sin red usan fallback; ninguna distancia inventada |
| 2 · B27.1/I08 | Repetir wheel aislado en Mac y luego automatizar su smoke en CI | scripts/verify_wheel.py (rama B27) y resultado registrado; base sin cámara/GPU/modelos |

Los parámetros geométricos y num_disparities de default.yaml son presets iniciales: revisar
con la unidad ELP antes de afirmar rango mínimo/máximo. Si la distorsión de los bordes no
se explica con el modelo elegido, comparar modelos de calibración usando validación.

## Decisiones que conviene conservar

Monolito modular local con Protocols, fakes y contratos claros. Núcleo secuencial para replay;
concurrencia solo en el adaptador vivo. No microservicios, bus genérico ni framework de plugins.
Código con nombres claros y comentarios de razones/unidades; no optimizar copiando menos
antes de medir. Una función responsable de transformar geometría evita ajustes manuales.

## Límites de los resultados

Los tests comprueban lógica y sintéticos; no demuestran calidad de Fusion, calibración ELP,
latencia audible ni compatibilidad física Mac/MPS. No ajustar thresholds con el test reservado.
La continuidad portátil/Lite/alerta sigue comprometida después de la entrega USB.
