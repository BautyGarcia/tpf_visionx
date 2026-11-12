"""Comandos de calibración: revisar sesiones, calibrar y comparar calibraciones.

    uv run python -m visionx.calibration revisar CARPETA... --tablero 9x6 --cuadrado-mm 28
    uv run python -m visionx.calibration calibrar --sesion CARPETA [--sesion ...] \\
        [--validacion CARPETA ...] --tablero 9x6 --cuadrado-mm 28 --salida archivo.yaml
    uv run python -m visionx.calibration comparar A.yaml B.pkl [--sesion CARPETA ...]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np

from visionx.calibration.board import Checkerboard
from visionx.calibration.calibrate import (
    CalibrationOptions,
    _robust_threshold,
    calibrate,
    rectified_errors,
    view_errors,
)
from visionx.calibration.models import LensModel
from visionx.calibration.report import coverage_text, summary, to_calibration, write_report
from visionx.calibration.sessions import PairView, Session, load_session
from visionx.calibration.storage import StereoCalibration, from_i308_pickle
from visionx.shared.errors import ContractError


def _board(args: argparse.Namespace) -> Checkerboard:
    return Checkerboard.parse(args.tablero, args.cuadrado_mm)


def _load(folders: list[str], board: Checkerboard, use_cache: bool) -> list[Session]:
    sessions = []
    for folder in folders:
        print(f"detectando esquinas en {folder} ...", flush=True)
        session = load_session(folder, board, use_cache=use_cache)
        print(f"  {len(session.views)} de {session.total_pairs} pares con el tablero en ambos ojos")
        for problem in session.problems:
            print(f"  - {problem}")
        sessions.append(session)
    return sessions


def _load_any(path: str) -> StereoCalibration:
    if path.endswith(".pkl"):
        return from_i308_pickle(path)
    return StereoCalibration.load(path)


def evaluate(calib: StereoCalibration, board: Checkerboard, views: list[PairView]) -> dict:
    """Mide una calibración ya hecha sobre fotos: mismas métricas que la validación."""
    objp = board.object_points()
    rows, vertical, scale, transfer_sq = [], [], [], []
    for view in views:
        if view.image_size != calib.image_size:
            raise ContractError(f"{view.key}: resolución distinta de la calibración")
        e = view_errors(calib.model, objp, view, calib.left, calib.right, calib.R, calib.T)
        v, s = rectified_errors(calib.model, board, view, calib.left, calib.right, calib.rect)
        rows.append((view.key, e, float(np.median(v)), s))
        vertical.append(v)
        scale.append(s)
        transfer_sq.append(e["transfer"] ** 2)
    allv = np.concatenate(vertical)
    return {
        "rows": rows,
        "transfer_rms_px": math.sqrt(float(np.mean(transfer_sq))),
        "vertical_median_px": float(np.median(allv)),
        "vertical_p95_px": float(np.percentile(allv, 95)),
        "scale_error_median": float(np.median(scale)),
    }


def cmd_revisar(args: argparse.Namespace) -> int:
    board = _board(args)
    reference = _load_any(args.referencia) if args.referencia else None
    for session in _load(args.carpetas, board, not args.sin_cache):
        print(f"\n=== {session.name} ===")
        print(coverage_text(session.views))
        if reference is None:
            print("  (con --referencia CALIBRACION.yaml se mide inclinación y error de cada foto)")
            continue
        result = evaluate(reference, board, session.views)
        tilts = np.array([e["tilt"] for _, e, _, _ in result["rows"]])
        dists = np.array([e["distance"] for _, e, _, _ in result["rows"]])
        print(
            f"inclinación: mediana {np.median(tilts):.0f}°, {int((tilts >= 20).sum())} de "
            f"{len(tilts)} fotos >= 20° | distancia {dists.min():.2f}-{dists.max():.2f} m"
        )
        # Mismos criterios que la limpieza del calibrador, relativos a esta sesión.
        opt = CalibrationOptions()
        thr = {
            k: _robust_threshold(
                np.array([e[k] for _, e, _, _ in result["rows"]]),
                opt.outlier_sigma,
                opt.outlier_floor_px,
            )
            for k in ("left", "right", "transfer")
        }
        print(f"{'par':>6s} {'incl.':>5s} {'dist m':>6s} {'izq':>6s} {'der':>6s} {'transf.':>7s}")
        for key, e, _, _ in result["rows"]:
            flag = []
            if e["left"] > thr["left"] or e["right"] > thr["right"]:
                flag.append("esquinas dudosas")
            elif e["transfer"] > thr["transfer"]:
                flag.append("movida")
            if e["tilt"] > opt.max_tilt_deg:
                flag.append("muy inclinada")
            print(
                f"{key.split('#')[-1]:>6s} {e['tilt']:5.0f} {e['distance']:6.2f} {e['left']:6.2f} "
                f"{e['right']:6.2f} {e['transfer']:7.2f}  {', '.join(flag)}"
            )
    return 0


def cmd_calibrar(args: argparse.Namespace) -> int:
    board = _board(args)
    models = tuple(LensModel(x.strip()) for x in args.modelos.split(","))
    opt = CalibrationOptions(models=models, alpha=args.alpha)
    fit = _load(args.sesion, board, not args.sin_cache)
    val = _load(args.validacion or [], board, not args.sin_cache)
    print(f"\ncalibrando con modelos {', '.join(x.value for x in models)} ...", flush=True)
    run = calibrate(fit, board, val, opt)
    calib = to_calibration(run, fit + val, opt)
    out = Path(args.salida)
    calib.save(out)
    report = write_report(run, out.with_suffix(".reporte.json"))
    print(summary(run, calib))
    print(f"\nguardado: {out}\ndetalle por foto: {report}")
    if args.muestra:
        _write_sample(calib, fit + val, out.with_suffix(".muestra.jpg"))
    return 0


def _write_sample(calib: StereoCalibration, sessions: list[Session], path: Path) -> None:
    """Par rectificado con líneas horizontales: los mismos puntos deben caer en la misma línea."""
    view = next((v for s in sessions for v in s.views), None)
    if view is None:
        return
    session = next(s for s in sessions if s.name == view.session)
    left = cv2.imread(str(session.folder / f"left_{view.index}.jpg"))
    right = cv2.imread(str(session.folder / f"right_{view.index}.jpg"))
    left_r, right_r = calib.rectify(left, right)
    both = np.hstack([left_r, right_r])
    for y in range(0, both.shape[0], 40):
        cv2.line(both, (0, y), (both.shape[1] - 1, y), (0, 255, 0), 1)
    cv2.imwrite(str(path), both)
    print(f"muestra rectificada: {path} (no subir: puede tener personas)")


def cmd_comparar(args: argparse.Namespace) -> int:
    calibs = [(path, _load_any(path)) for path in args.calibraciones]
    print(f"{'archivo':40s} {'modelo':9s} {'fx izq':>7s} {'fx der':>7s} {'B mm':>6s} {'id'}")
    for path, c in calibs:
        print(
            f"{Path(path).name[:40]:40s} {c.model.value:9s} {c.left.K[0, 0]:7.1f} "
            f"{c.right.K[0, 0]:7.1f} {1000 * c.baseline_m:6.2f} {c.calibration_id}"
        )
    if not args.sesion:
        print("\n(con --sesion CARPETA se miden todas sobre las mismas fotos)")
        return 0
    board = _board(args)
    views = [v for s in _load(args.sesion, board, not args.sin_cache) for v in s.views]
    print(f"\nsobre {len(views)} pares: transferencia | vertical mediana / P95 | escala")
    for path, c in calibs:
        r = evaluate(c, board, views)
        print(
            f"  {Path(path).name[:40]:40s} {r['transfer_rms_px']:.3f} px | "
            f"{r['vertical_median_px']:.3f} / {r['vertical_p95_px']:.3f} px | "
            f"{100 * r['scale_error_median']:+.2f}%"
        )
    print("Si alguna de esas fotos se usó para ajustar esa calibración, su número es optimista.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m visionx.calibration",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    def board_args(p: argparse.ArgumentParser, required: bool = True) -> None:
        p.add_argument(
            "--tablero",
            required=required,
            default="9x6",
            help="esquinas internas COLSxFILAS, p. ej. 9x6 (10x7 cuadrados)",
        )
        p.add_argument(
            "--cuadrado-mm",
            type=float,
            required=required,
            default=None,
            help="lado del cuadrado impreso medido con regla, en mm",
        )
        p.add_argument("--sin-cache", action="store_true", help="volver a detectar todo")

    p = sub.add_parser("revisar", help="controlar una sesión de fotos")
    p.add_argument("carpetas", nargs="+")
    p.add_argument("--referencia", help="calibración (.yaml o .pkl) para medir cada foto")
    board_args(p)
    p.set_defaults(func=cmd_revisar)

    p = sub.add_parser("calibrar", help="calibrar con una o más sesiones")
    p.add_argument("--sesion", action="append", required=True, help="carpeta de ajuste")
    p.add_argument("--validacion", action="append", help="carpeta solo para validar")
    p.add_argument("--salida", required=True, help="archivo .yaml de salida")
    p.add_argument("--modelos", default="pinhole5,rational,fisheye")
    p.add_argument("--alpha", type=float, default=0.0, help="0 recorta bordes, 1 conserva todo")
    p.add_argument("--muestra", action="store_true", help="guardar un par rectificado de prueba")
    board_args(p)
    p.set_defaults(func=cmd_calibrar)

    p = sub.add_parser("comparar", help="comparar calibraciones (.yaml o .pkl de la cátedra)")
    p.add_argument("calibraciones", nargs="+")
    p.add_argument("--sesion", action="append", help="medirlas sobre estas fotos")
    board_args(p, required=False)
    p.set_defaults(func=cmd_comparar)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "sesion", None) and args.comando == "comparar" and args.cuadrado_mm is None:
        print("error: --sesion necesita --tablero y --cuadrado-mm", file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
