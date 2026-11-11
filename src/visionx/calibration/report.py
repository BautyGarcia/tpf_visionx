"""Resumen legible de una calibración y de la cobertura de una sesión."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from visionx.calibration.calibrate import CalibrationOptions, CalibrationRun
from visionx.calibration.sessions import PairView, Session
from visionx.calibration.storage import StereoCalibration, from_parameters, nan_to_none

# Grilla para medir qué zonas de la imagen cubrió el tablero (filas x columnas).
GRID = (3, 4)


def coverage(views: list[PairView]) -> np.ndarray:
    """Cuántas fotos tocan cada zona de la imagen del ojo izquierdo (3 x 4)."""
    rows, cols = GRID
    counts = np.zeros(GRID, int)
    if not views:
        return counts
    w, h = views[0].image_size
    for view in views:
        cells = set()
        for x, y in view.left:
            cells.add((min(int(y / h * rows), rows - 1), min(int(x / w * cols), cols - 1)))
        for r, c in cells:
            counts[r, c] += 1
    return counts


def coverage_text(views: list[PairView]) -> str:
    counts = coverage(views)
    names = ["arriba", "medio ", "abajo "]
    lines = ["fotos que tocan cada zona (ojo izquierdo, de izquierda a derecha):"]
    for name, row in zip(names, counts, strict=True):
        lines.append(f"  {name}  " + "  ".join(f"{n:3d}" for n in row))
    empty = int((counts == 0).sum())
    weak = int(((counts > 0) & (counts < 3)).sum())
    if empty or weak:
        lines.append(f"  -> {empty} zonas sin fotos y {weak} con menos de 3: cubrirlas")
    return "\n".join(lines)


def to_calibration(
    run: CalibrationRun, sessions: list[Session], opt: CalibrationOptions
) -> StereoCalibration:
    sel = run.selected
    images = {
        v.key: {"izquierda": v.left_sha256, "derecha": v.right_sha256}
        for s in sessions
        for v in s.views
    }
    info = {
        "creado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "opencv": cv2.__version__,
        "tablero": {
            "tipo": "damero",
            "esquinas_internas": [run.board.cols, run.board.rows],
            "cuadrado_m": run.board.square_m,
        },
        "candidato": sel.name,
        "metricas": {
            "rms_ajuste_px": sel.fit_rms_px,
            "pares_ajuste": len(run.fit_keys),
            "pares_validacion": len(run.validation_keys),
            "pares_descartados": len(sel.rejected),
            **{f"validacion_{k}": v for k, v in sel.validation.items() if k != "n"},
        },
        "sesiones": sorted({s.name for s in sessions}),
        "pares_ajuste": {k: images[k] for k in run.fit_keys},
        "pares_validacion": {k: images[k] for k in run.validation_keys},
        "descartados": sel.rejected,
        "avisos": run.warnings,
        "opciones": {k: (v if not isinstance(v, tuple) else [str(x) for x in v])
                     for k, v in asdict(opt).items()},
    }  # fmt: skip
    return from_parameters(
        sel.model,
        run.image_size,
        sel.left,
        sel.right,
        sel.R,
        sel.T,
        opt.alpha,
        nan_to_none(json.loads(json.dumps(info, default=float))),
    )


def summary(run: CalibrationRun, calib: StereoCalibration) -> str:
    sel = run.selected
    lines = ["", "=== Candidatos (validación = fotos que no participaron del ajuste) ==="]
    header = f"{'modelo':22s} {'ajuste':>7s} {'transf.':>8s} {'vert.med':>8s} {'vert.P95':>8s}"
    header = header.replace("transf.", "trf.med")
    header += f" {'escala':>7s} {'fx izq':>7s} {'B mm':>6s} {'desc.':>5s}"
    lines.append(header)
    for c in run.candidates:
        if c.error:
            lines.append(f"{c.name:22s} falló: {c.error}")
            continue
        v = c.validation
        mark = " <- elegido" if c is sel else ""
        lines.append(
            f"{c.name:22s} {c.fit_rms_px:7.3f} {v.get('transfer_median_px', math.nan):8.3f} "
            f"{v.get('vertical_median_px', math.nan):8.3f} "
            f"{v.get('vertical_p95_px', math.nan):8.3f} "
            f"{100 * v.get('scale_error_median', math.nan):+6.2f}% {c.left.K[0, 0]:7.1f} "
            f"{1000 * c.baseline_m:6.2f} {len(c.rejected):5d}{mark}"
        )
    lines += [
        "",
        "=== Calibración elegida ===",
        f"id: {calib.calibration_id}",
        f"modelo: {sel.name}   pares ajuste {len(run.fit_keys)}   validación "
        f"{len(run.validation_keys)}   descartados {len(sel.rejected)}",
        f"error de ajuste (RMS): {sel.fit_rms_px:.3f} px",
    ]
    if sel.validation:
        v = sel.validation
        lines.append(
            f"validación ({v['n']:.0f} pares): transferencia mediana "
            f"{v['transfer_median_px']:.3f} px | vertical mediana "
            f"{v['vertical_median_px']:.3f} px, P95 {v['vertical_p95_px']:.3f} px | escala "
            f"{100 * v['scale_error_median']:+.2f}%"
        )
        if v.get("n_moved"):
            lines.append(
                f"  sin {v['n_moved']:.0f} fotos que parecen movidas "
                f"({', '.join(sel.moved_validation)}): vertical mediana "
                f"{v['clean_vertical_median_px']:.3f} px, P95 {v['clean_vertical_p95_px']:.3f} px"
                f", escala {100 * v['clean_scale_error_median']:+.2f}%"
            )
    g = calib.geometry()
    lines.append(
        f"rectificado: fx {g.fx:.1f} px, centro ({g.cx:.1f}, {g.cy:.1f}), "
        f"baseline {1000 * g.baseline_m:.2f} mm"
    )
    if sel.rejected:
        lines += ["", "=== Fotos descartadas ==="]
        lines += [f"  {k}: {reason}" for k, reason in sorted(sel.rejected.items())]
    if run.stability:
        lines += ["", "=== Estabilidad entre sesiones (cada sesión calibrada sola) ==="]
        for row in run.stability:
            if "error" in row:
                lines.append(f"  {row['session']}: {row['error']} (n={row['n']})")
            else:
                lines.append(
                    f"  {row['session']}: n={row['n']} "
                    f"fx {row['fx_left']:.1f}/{row['fx_right']:.1f}"
                    f" px, B {1000 * row['baseline_m']:.2f} mm, RMS {row['rms_px']:.3f} px"
                )
    if run.warnings:
        lines += ["", "=== Avisos ==="] + [f"  - {w}" for w in run.warnings]
    lines.append(
        "\nRecordatorio: el error y la escala sobre el tablero no reemplazan medir con cinta "
        "métrica a 1, 2 y 3 m."
    )
    return "\n".join(lines)


def write_report(run: CalibrationRun, path: Path) -> Path:
    """Detalle por foto en JSON, para revisar qué fotos sirven y por qué."""
    data = {
        "seleccionado": run.selected.name,
        "candidatos": [
            {
                "nombre": c.name,
                "error": c.error,
                "rms_ajuste_px": c.fit_rms_px,
                "validacion": c.validation,
                "fx_izquierda": float(c.left.K[0, 0]) if c.left else None,
                "baseline_m": c.baseline_m,
                "descartados": c.rejected,
            }
            for c in run.candidates
        ],
        "fotos": [asdict(v) for v in run.views],
        "estabilidad": run.stability,
        "avisos": run.warnings,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nan_to_none(data), indent=1, ensure_ascii=False), encoding="utf-8")
    return path
