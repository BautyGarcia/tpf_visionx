# Tablero de ejecución VisionX

Plan completo: [PLAN.md](PLAN.md). **A = Bauty; B = Tomás. Sin aprobación cruzada obligatoria.**
Las decisiones se coordinan por WhatsApp/en persona; el repo registra versiones, tareas y entregas.

## Dónde marcar el avance

| Responsable | Checklist con consignas | Rutas | Integraciones |
|---|---|---|---|
| A | [A01-A29](A.md) | datos, depth/, experimentos | entrega profundidad/modelos, recibe pares/GT |
| B | [B01-B28](B.md) | cámara, aplicación, hardware | entrega pares/app, recibe estimadores/políticas |
| Coordinador del hito | [I00-I08](INTEGRACIONES.md) | solo su ficha Ixx | código + artefacto + recepción |

Se tilda en cada ficha; no duplicar estado aquí. Agentes de implementación no editan tableros
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
- [E7 / I07](INTEGRACIONES.md#i07---extensiones-o-decisión-de-no-hacerlas): extensiones seleccionadas o no aplica.
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
- [ ] C03 · estado: por integrar · rama: b/C03-planificacion-integracion
- Ejecuta B. Entrega A/B completas, I00-I08, contratos objetivo, métricas y flujo sin aprobación.
  Aceptación: IDs/dependencias/enlaces consistentes y cambios verificables; luego integrar a main.
  Avisar a A la fuente vigente. Sin marcar hecha antes de publicación/incorporación de esta rama.

### C04 - Entornos y reglas remotas
- [ ] C04 · estado: pendiente · rama: —
- Ejecuta B; A aporta comprobación de su Mac. Instalar uv/Python3.11, base/ml según tarea,
  activar hooks, doctor y tests en ambas PCs. Registrar resultado y límites.
- Verificar GitHub: PR con 0 aprobaciones, sin code-owner review, squash y checks de CI.
  Si solo Bauty administra, él aplica el ajuste; es configuración, no aprobación de contenido.
  Salida: evidencia de dos entornos y política remota; I00 no declara preparación sin prueba.

### C05 - Almacén compartido de artefactos
- [ ] C05 · estado: pendiente · rama: —
- Ejecuta B con acceso aportado por A. Elegir ubicación compartida, registrar acceso por config
  local y publicar fixture/archivo pequeño para prueba de descarga/hash en ambas PCs.
  Salida: [protocolo](ARTEFACTOS.md) aplicado con ubicación real; requerido antes de I02.

### C06 - Alcance académico y disponibilidad
- [ ] C06 · estado: pendiente · rama: —
- Ejecuta A, coordina directo con B/cátedra. Registrar tema/equipo de 2 aprobado (consigna general
  menciona 3/4), fecha real, horas disponibles y alcance de cuatro modos vs extensiones.
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

1. Integrar C03; preparar C04/C05 y confirmar C06.
2. A empieza A04 y puede adelantar A01/A02; B hace B01/B03 mientras llega la API.
3. Con A04 en main: A05 y B02/B04 en paralelo -> I00.
4. A06 + B05/B06/B07 -> I01, sin esperar CNN ni calibración final.

Las tareas de software restantes están preparadas pero **pendientes**; un hito es recepción técnica,
no un nuevo trámite de aprobación del compañero.
