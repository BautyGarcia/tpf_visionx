# Tablero de ejecución VisionX

Plan completo: [PLAN.md](PLAN.md). **A = Bauty; B = Tomás. Sin aprobación cruzada obligatoria.**
Las decisiones se coordinan por WhatsApp/en persona; el repo registra versiones, tareas y entregas.

## Dónde marcar el avance

| Responsable | Checklist con consignas | Rutas | Integraciones |
|---|---|---|---|
| A | [A01-A29](A.md) | datos, depth/, experimentos | entrega profundidad/modelos, recibe pares/GT |
| B | [B01-B28](B.md) | cámara, aplicación, hardware | entrega pares/app, recibe estimadores/políticas |
| Coordinador del hito | [I00-I08](INTEGRACIONES.md) | solo su ficha Ixx | código + artefacto + recepción |

Estado de A/B solo en sus índices; fichas individuales sin estado duplicado. Agentes de implementación no editan tableros
a la vez: el coordinador de cada persona registra cambios. [Flujo y estados](FLUJO.md).
ID identifica tarea; etapa/dependencias definen orden. [Métricas M0-M12](METRICAS.md).

## Etapas de punta a punta

- [E0 / I00](INTEGRACIONES.md#i00---base-compatible-sin-hardware): APIs + replay + fakes.
- [E1 / I01](INTEGRACIONES.md#i01---primera-entrega-replay-objeto-y-audio): primera demo con audio y profundidad simulada.
- [E2 / I02](INTEGRACIONES.md#i02---cámaracalibración-y-distancia-clásica): USB/calibración + SGBM y metros.
- [E3 / I03](INTEGRACIONES.md#i03---b4-y-datos-listos-para-entrenar): B4 + banco ELP + protocolo.
- [E4 / I04](INTEGRACIONES.md#i04---fusion-dentro-de-la-aplicación): Fusion entrenada en aplicación.
- [E5 / I05](INTEGRACIONES.md#i05---cuatro-modos-usb-estables): búsqueda, distancia, OCR y descripción.
- [E6 / I06](INTEGRACIONES.md#i06---resultados-finales-conjuntos): evaluación final y tablas.
- [E7 / I07](INTEGRACIONES.md#i07---portátil-lite-fusion-ffs-y-alerta-completos): portátil, Lite, Fusion-FFS y alerta comprometidos; continuidad tras entrega.
- [E8 / I08](INTEGRACIONES.md#i08---release-y-defensa): release, informe, póster y respaldo.

## Compartidas: un ejecutor, no dos aprobadores

### C01 - Esqueleto del repositorio
- [x] C01 · estado: hecha · rama: main
- Evidencia: e60f43e; estructura/entorno/protocolo inicial. No implica módulos funcionales.

### C02 - Roles y plataforma
- [x] C02 · estado: hecha · rama: main
- Evidencia: bf9d43a, PR #1. A=Bauty, B=Tomás; Mac MPS/Windows CPU y nube cuando corresponda.
  Política de aprobación anterior reemplazada por C03.

### C03 - Planificación e integración completas
- [x] C03 · estado: hecha · rama: main
- Ejecuta B. Entrega A/B completas, I00-I08, contratos objetivo, métricas y flujo sin aprobación.
  Aceptación: IDs/dependencias/enlaces consistentes y cambios verificables; luego integrar a main.
  Evidencia: ac66b96, PR #2 integrado; CI Windows/macOS/Linux aprobada y planificación publicada.

### C04 - Entornos y reglas remotas
- [x] C04 · estado: hecha · rama: main
- Ejecuta B; A aporta comprobación de su Mac. Instalar uv/Python3.11, base/ml según tarea,
  activar hooks, doctor y tests en ambas PCs. Registrar resultado y límites.
- Verificar GitHub: PR con 0 aprobaciones, sin code-owner review, squash y checks de CI.
  Si solo Bauty administra, él aplica el ajuste; es configuración, no aprobación de contenido.
  Salida: evidencia de dos entornos y política remota; I00 no declara preparación sin prueba.
- Cierre: **Windows y Mac física verificados**, 14 tests en ambos. Bauty registró Mac y
  protección en 1e7adf6 (PR #4); ruleset activo comprobado por API: PR con 0 aprobaciones,
  squash y tres checks requeridos. Evidencia y comandos: [C04.md](C04.md).

### C05 - Almacén compartido de artefactos
- [ ] C05 · estado: en curso · rama: b/C05-almacen
- Ejecuta B con acceso aportado por A. Elegir ubicación compartida, registrar acceso por config
  local y publicar fixture/archivo pequeño para prueba de descarga/hash en ambas PCs.
  Salida: [protocolo](ARTEFACTOS.md) aplicado con ubicación real; requerido antes de I02.
- Avance: Drive `VisionX-artefactos` (dueño Tomás, Bauty editor), subcarpetas y reglas de
  subida en ARTEFACTOS.md; clave `artifacts.root` en configs. Reserva de ARTEFACTOS.md,
  TAREAS.md y default.yaml avisada a A. Prueba: `_prueba/C05-prueba.txt`, SHA-256
  9037805d44459f3aca6d40f880c4625c5cb01d694cb47f36069d79f4494c537c (Windows, 2026-10-29).
  Falta: mismo hash leído en la Mac de A.

### C06 - Alcance académico y disponibilidad
- [ ] C06 · estado: pendiente · rama: —
- Ejecuta A, coordina directo con B/cátedra. Registrar tema/equipo de 2 aprobado (consigna general
  menciona 3/4), fecha de entrega 10/12/2026 confirmada por Tomás; faltan horas disponibles y aprobación académica.
  Confirmar informe <=8 páginas y póster A0/A1 vertical. Sin inventar autorización ni cronograma.
  Entrega: decisión fechada y ajuste de capacidad; antes de comprometer extensión/cierre.

### C07 - Congelar protocolo antes de entrenar/testear
- [ ] C07 · estado: pendiente · rama: —
- Ejecuta A; B aporta GT/latencia objetivo. Con A09/A11/B12 disponibles, fijar splits/hashes,
  regiones, máscaras, fallos, métrica principal/checkpoint y presupuesto.
  Registrar metas P ratificadas con desarrollo. Salida: config/decisión versionada en I03.

### C08 - Congelamiento y publicación
- [ ] C08 · estado: pendiente · rama: —
- Ejecuta B con artefactos A. Enumerar entregables, commit final/hashes, estado de extensiones,
  incidencias conocidas, ensayo cruzado y respaldo. M12; publicar release cuando se autorice.
  I08 no se marca hecho por un PR de documentación sin reproducción real.

## Arranque recomendado

1. C03/C04 ya tienen evidencia; C05 espera lectura de hash en Mac. C06 fecha 10/12 confirmada, resto pendiente.
2. A04 está en main con recepción pendiente: iniciar A05/B02/B04 y fixes auditados en tareas separadas.
3. A01/A02, captura/calibración B01/B08/B09 y preparación A24.1–A24.4 avanzan en paralelo.
4. A06 + B05/B06/B07 -> I01; OCR/voz/modos empiezan con fixtures sin esperar Fusion.

Las tareas de software restantes están preparadas pero **pendientes**; un hito es recepción técnica,
no un nuevo trámite de aprobación del compañero.

## Coordinación de fichas — 29/10/2026

Aplicar [PLAN v2](PLAN.md). Entrega USB 10/12/2026 y alcance posterior comprometido.
A/B conservan el único estado oficial; fichas individuales contienen especificaciones sin
estados duplicados. Coordinador actualiza índices; agentes editan su ficha y TRASPASO.
Varios agentes por área, un worktree por tarea y reserva de archivos/hardware. Integrado
significa código en main; recepción pendiente se registra separada en Ixx. Una tarea con
recepción pendiente no bloquea inicio contra APIs/fakes; hecha exige aceptación completa.
I07 posterior no bloquea I08 académico. Sin commits/push salvo pedido explícito.

## C09 - Plan completo y coordinación v2

- [ ] C09 · estado: por integrar · rama: b/C09-plan-completo
- Responsable B por pedido del usuario; reserva documental de esta tarea. Sin hardware.
- Entrega: fichas/índices, calendario, auditoría y decisión; validar enlaces/IDs/diff.
- C06: fecha confirmada por Tomás 10/12/2026; aprobación académica y disponibilidad siguen pendientes.

Lectura para el otro equipo/agente: [traspaso C09 a Bauty](LECTURA-BAUTY.md).
