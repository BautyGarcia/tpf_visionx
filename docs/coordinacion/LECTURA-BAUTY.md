# Traspaso de C09 a Bauty

Leer PLAN.md v2, decisión 0002 y AUDITORIA.md; luego A.md para elegir ficha.
C09 solo cambia documentación; no completó módulos ni pruebas físicas.
La ELP está disponible; coordinar quién la usa y grabar pares para agentes sin acceso.

## Arranque paralelo

- A05/A06 con contratos integrados, y fixes A04.1–A04.6 en tareas separadas.
- A01/A02 para datos/métricas; A24.1–A24.4 para comparadores desde una fixture.
- B02/B04/B05 para replay/controlador; B01/B08/B09 para cámara y calibración.
- B12.1 entrega capturas sin esperar B4; B12.2 trabaja con fakes.
- OCR/voz/descripción no esperan Fusion; aceptar integración real más adelante.

## Qué sigue sin evidencia

C05 espera mismo hash en Mac; C06 confirma fecha pero no aprobación académica ni horas.
A04 conserva su estado de recepción anterior aunque hay código en main. No marcarlo hecho
por esta reorganización. Repetir pipeline completo/MPS en Mac cuando exista.

## Después de publicar los cambios

Solo cuando C09 esté integrado: actualizar checkout limpio con `git pull --ff-only` y correr
`uv run visionx novedades`. No ejecutar pull sobre cambios ajenos. Tomar tareas desde
origin/main actualizado según FLUJO; no copiar archivos entre ramas.
Estado único en índices A/B; detalle en tareas/<ID>.md; TRASPASO local sin versionar.
