# B27.1 — instalación sin checkout y configuración explícita

Rama `b/B27-instalacion`, base `3034f40`; responsable B, Tomás/Codex.
Reserva: config.py, cli.py, worklog.py, pyproject.toml, tests/test_installation.py,
scripts/verify_wheel.py y documentación asociada. Sin hardware ni cambios de schema.
Independiente de la rama A04-auditoria: no espera geometría para validar instalación.

## Cambios

- Hatch incluye el único configs/default.yaml del checkout como visionx/default.yaml.
- load_config usa ese recurso fuera del checkout; local.yaml sigue requiriendo carga explícita.
- YAML raíz debe ser mapping con claves de texto; vacío es override sin cambios.
- doctor --config aplica el mismo override a config y ChArUco; muestra cuál se usó.
- doctor --runtime-only omite hooks de desarrollo, no los controles de dependencias.
- log fuera del checkout falla con mensaje y código 1, sin escribir dentro del entorno Python.

## Verificación del consumidor

En la rama propia actualizada, ejecutar uv sync --locked, ruff y pytest. Para Windows:

```text
uv build --wheel --out-dir outputs/wheel
uv venv outputs/wheel-env
uv pip install --python outputs/wheel-env/Scripts/python.exe outputs/wheel/visionx-0.1.0-py3-none-any.whl
uv run python scripts/verify_wheel.py --python outputs/wheel-env/Scripts/python.exe
```

En Mac usar outputs/wheel-env/bin/python. El script crea un cwd temporal externo y usa
-I para impedir importar src por accidente. Requiere wheel instalado, no un editable.
No abre cámara ni descarga modelos. La instalación puede obtener dependencias de caché/red;
los tests automáticos de pytest no necesitan internet. No repetir uv venv sobre un entorno
con trabajo ajeno: elegir nombre propio si outputs/wheel-env ya existe.

Se corrigió también un fallo reproducido del registro: strip() eliminaba la primera columna
porcelain de Git y truncaba el primer nombre de archivo (README.md → EADME.md).
Ahora solo se quitan saltos finales y una regresión cubre el caso.

## Resultado local y límites

Windows: cinco casos aislados aprobados: import/defaults y doctor runtime retornan 0;
doctor desarrollo sin Git, log fuera de checkout y override inválido retornan 1 sin traceback.
No se midieron Mac, MPS ni hardware. Recepción física Mac pendiente I08.
Publicación autorizada por Tomás el 30/10/2026; recepción Mac pendiente.
