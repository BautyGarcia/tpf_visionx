"""Comprueba un wheel ya instalado, fuera del checkout y sin acceder a hardware.

Ejemplo Windows:
    uv run python scripts/verify_wheel.py --python outputs/wheel-env/Scripts/python.exe
En macOS/Linux, el intérprete equivalente está en outputs/wheel-env/bin/python.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

# -I ignora PYTHONPATH y el directorio actual. Además verificamos que visionx provenga
# de site-packages: un entorno editable NO sirve para probar una instalación distribuida.
VERIFY_INSTALL = """
from pathlib import Path
import sysconfig
import visionx
from visionx.shared.config import load_config

module_path = Path(visionx.__file__).resolve()
installed_packages = Path(sysconfig.get_path("purelib")).resolve()
assert module_path.is_relative_to(installed_packages), module_path
assert load_config()["camera"]["device"] == 0
print("Paquete cargado desde:", module_path)
"""


def check_case(
    python_path: Path,
    working_directory: Path,
    name: str,
    arguments: list[str],
    expected_code: int,
) -> None:
    """Ejecuta un caso y comprueba tanto el código de salida como el error legible."""
    process = subprocess.run(
        [str(python_path), "-I", *arguments],
        cwd=working_directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = process.stdout + process.stderr
    if process.returncode != expected_code or "Traceback" in output:
        raise RuntimeError(
            f"{name}: código {process.returncode}, esperado {expected_code}\n{output}"
        )
    print(f"ok: {name} (código {process.returncode})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python", type=Path, required=True, help="intérprete del entorno con wheel"
    )
    args = parser.parse_args()
    python_path = args.python.resolve()
    if not python_path.is_file():
        parser.error("el intérprete indicado no existe")

    # El temporal queda fuera del checkout. Al terminar solo se borra este directorio
    # creado por TemporaryDirectory; no se toca el entorno ni archivos del proyecto.
    with tempfile.TemporaryDirectory(prefix="visionx-wheel-") as directory:
        external_directory = Path(directory)
        invalid_config = external_directory / "invalid.yaml"
        invalid_config.write_text(
            "calibration:\n  dictionary: DICT_INEXISTENTE\n", encoding="utf-8"
        )
        cases = [
            ("import y defaults instalados", ["-c", VERIFY_INSTALL], 0),
            ("doctor runtime", ["-m", "visionx.cli", "doctor", "--runtime-only"], 0),
            ("doctor desarrollo sin Git", ["-m", "visionx.cli", "doctor"], 1),
            ("log fuera del checkout", ["-m", "visionx.cli", "log", "prueba aislada"], 1),
            (
                "override inválido",
                ["-m", "visionx.cli", "doctor", "--runtime-only", "--config", str(invalid_config)],
                1,
            ),
        ]
        for name, arguments, expected_code in cases:
            check_case(python_path, external_directory, name, arguments, expected_code)

        if (external_directory / "docs").exists():
            raise RuntimeError("visionx log escribió fuera del checkout")
        print("Cinco casos correctos; sin escritura de logs fuera del checkout.")


if __name__ == "__main__":
    main()
