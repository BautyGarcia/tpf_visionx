"""Punto de entrada: `visionx doctor` revisa que el entorno esté listo."""

from __future__ import annotations

import argparse
import platform
import sys


def _check(name: str, fn) -> bool:
    try:
        detail = fn()
        print(f"  ok   {name}: {detail}")
        return True
    except Exception as exc:  # noqa: BLE001 - el diagnóstico tiene que seguir
        print(f"  FALLA {name}: {exc}")
        return False


def doctor() -> int:
    import cv2
    import numpy as np

    from visionx import __version__
    from visionx.shared.config import load_config

    print(f"VisionX {__version__} · Python {platform.python_version()} · {platform.machine()}")
    results = [
        _check("numpy", lambda: np.__version__),
        _check("opencv", lambda: cv2.__version__),
        _check("ChArUco (aruco)", _charuco),
        _check("filtro WLS (ximgproc)", _wls),
        _check("config", lambda: f"{len(load_config())} secciones"),
    ]
    _check("torch / MPS (opcional, extra 'ml')", _torch)
    _check("hooks de git", _hooks)
    return 0 if all(results) else 1


def _charuco() -> str:
    import cv2

    from visionx.shared.config import load_config

    c = load_config()["calibration"]
    dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, c["dictionary"]))
    board = cv2.aruco.CharucoBoard(tuple(c["squares"]), c["square_m"], c["marker_m"], dic)
    cv2.aruco.CharucoDetector(board)
    return f"tablero {c['squares'][0]}x{c['squares'][1]} creado"


def _wls() -> str:
    import cv2

    cv2.ximgproc.createDisparityWLSFilterGeneric(False)
    return "disponible"


def _hooks() -> str:
    import subprocess

    out = subprocess.run(
        ["git", "config", "core.hooksPath"], capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()
    if out != ".githooks":
        raise RuntimeError("inactivos: correr `git config core.hooksPath .githooks`")
    return "activos"


def _torch() -> str:
    try:
        import torch
    except ImportError:
        return "no instalado (uv sync --extra ml)"
    mps = torch.backends.mps.is_available()
    cuda = torch.cuda.is_available()
    return f"torch {torch.__version__}, MPS={'sí' if mps else 'no'}, CUDA={'sí' if cuda else 'no'}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="visionx")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="revisa dependencias y configuración")
    log = sub.add_parser("log", help="crea una entrada del registro en docs/log/")
    log.add_argument("tema", help="tema corto de la entrada")
    log.add_argument("--agente", default="", help="ej. claude-code, codex")
    log.add_argument("--tarea", default="", help="ID de TAREAS.md, ej. B02")
    nov = sub.add_parser("novedades", help="últimas entradas del registro y tareas en curso")
    nov.add_argument("-n", type=int, default=5, help="cantidad de entradas")
    args = parser.parse_args(argv)
    if args.cmd == "doctor":
        return doctor()
    if args.cmd == "novedades":
        from visionx.devtools.worklog import recent, tasks_in_progress

        print("Últimas entradas del registro (docs/log/):")
        for e in recent(args.n):
            fecha, autor, tarea = e.get("fecha", "?"), e.get("autor", "?"), e.get("tarea", "-")
            print(f"  {fecha}  {autor:<14} [{tarea}] {e['tema']}")
            print(f"      {e['archivo']}")
        print("\nTareas en curso, por integrar o bloqueadas (docs/coordinacion/):")
        for t in tasks_in_progress() or ["  (ninguna)"]:
            print(f"  {t}")
        return 0
    if args.cmd == "log":
        from visionx.devtools.worklog import new_entry

        path = new_entry(args.tema, agente=args.agente, tarea=args.tarea)
        print(f"Entrada creada: {path.relative_to(path.parents[2])}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
