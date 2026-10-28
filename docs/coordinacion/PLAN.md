# Plan operativo VisionX

Versión 1, 28/10/2026. A: Bauty; B: Tomás. Fija el orden de trabajo, no declara software
implementado ni resultados obtenidos. Entrada común: [tablero](TAREAS.md).

## Objetivo y alcance

Investigar si **Fusion**, U-Net residual propia de **10 canales**, mejora profundidad y/o utilidad
de incertidumbre frente a métodos clásicos y B4. Integrarla en demo USB con buscar/guiar,
distancia, lectura y descripción de escena. Demo en Mac; núcleo/replay también en Windows.
CUDA/VM se usa para cómputo que lo requiera, no como dependencia de la interacción local.

**Núcleo:** datos/geometría auditados; B0-B4; Fusion entrenada y evaluada; ablaciones;
cuatro modos USB; dashboard/replay; informe, póster y reproducción cruzada.
**Condicionado:** Fusion-FFS, Lite, Pi/Wi-Fi, wearable y alerta de cercanía.
**Fuera de entrega:** SLAM, mapa persistente, memoria de objetos y guía de mano.
Una red funcional no demuestra superioridad; también se reporta un resultado negativo.

La propuesta visual v7 de `docs/` (Lite principal de 7 canales) es antecedente histórico.
La propuesta vigente es `entregas/propuesta_visionx.html`/PDF más este plan. La revisión externa
es consulta. Un cambio solicitado por la cátedra se registra en decisiones y actualiza tareas.
No se mezclan ambas arquitecturas ni se afirma aprobación académica que no esté registrada.

## Etapas y puntos de merge

| Etapa | Resultado integrado | Trabajo A | Trabajo B | Hito |
|---|---|---|---|---|
| E0 | Interfaces + replay y fakes portables | A01, A02, A04, A05 | B02, B04; adelantar B01/B03 si hay equipo | I00 |
| E1 | Replay detecta y responde con profundidad simulada | A06 | B05-B07 | I01 |
| E2 | Cámara/calibración + distancia clásica real | A03, A07 | B01, B08-B10 | I02 |
| E3 | Baselines fuertes; datos/protocolo congelados | A08-A13 | B11-B12 | I03 |
| E4 | Fusion entrenada e intercambiable con B4 | A14-A18 | B13 | I04 |
| E5 | Cuatro modos USB; pérdida, cancelación y confianza | A19 | B03, B14-B19 | I05 |
| E6 | Evaluación final y evidencia reproducible | A20-A22, A24 | B20-B21 | I06 |
| E7 | Extensiones elegidas por mediciones | A25-A28 | B22-B25, B28 | I07 |
| E8 | Release, informe, póster y defensa | A23, A29 | B26-B27 | I08 |

Los IDs originales A01-A03/B01-B03 se conservan: **el orden lo dan etapa y dependencias, no
el número**. No esperar todo A01 para replay ni terminar Fusion para audio. Cada PR compatible
se integra cuando está listo; los Ixx comprueban el sistema completo.

## Ejecución y capacidad

- Fichas en [A.md](A.md)/[B.md](B.md). Tarea de una capacidad; si supera dos sesiones, dividir
  en Axx.1/Bxx.1 sin renumerar. Cada persona actualiza su fichero, no todos sus agentes a la vez.
- Entrada: dependencia integrada o fake indicado, fixture/config y rutas reservadas. Si falta,
  marcar bloqueada y avanzar en lo independiente. Salida: evidencia y, si aplica, recepción.
- Antes de etapa: acordar por WhatsApp/en persona objetivo, equipo disponible y presupuesto de
  tiempo/cómputo. Registrar solo decisiones que alteren interfaces, alcance o experimentos.
- C06 registra fecha real y horas disponibles. Propuesta inicial: I01 dentro del primer 20%
  del tiempo, USB funcional antes del 60%; reservar al menos 20% para E6/E8. No son fechas
  comprometidas. E7 no consume esa reserva; se decide no aplica si no aporta o no hay tiempo.
- A13 mide un piloto antes de contratar/consumir GPU. Ninguna consigna promete horas o FPS sin
  medir. Los umbrales de ingeniería son propuestos hasta congelarlos en C07 con datos de desarrollo.

## Coordinadores y fuente de verdad

B registra I00-I05/I07; A registra I06; B registra I08 con artefactos científicos de A.
Registrar no significa aprobar el contenido ajeno. El productor es responsable de su módulo y
el consumidor verifica que puede usarlo. Pasa todo por main; no copiar archivos entre ramas.

Documentos operativos: [flujo](FLUJO.md), [contratos](../CONTRATOS.md), [métricas](METRICAS.md),
[artefactos](ARTEFACTOS.md), [integraciones](INTEGRACIONES.md). Tareas/decisiones deben apuntar
a esta versión. Los documentos históricos no son instrucciones nuevas para las IAs.
