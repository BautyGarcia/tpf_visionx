"""Permite `python -m visionx ...`, equivalente al comando `visionx`.

En Windows con Smart App Control activado, los lanzadores `.exe` que genera uv para los
comandos de consola (`visionx.exe`, `pytest.exe`) pueden quedar bloqueados por no tener
reputación; `python -m` usa el intérprete, que sí está permitido.
"""

import sys

from visionx.cli import main

sys.exit(main())
