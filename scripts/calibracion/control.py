"""Control de una calibración fija con fotos nuevas: error vertical y escala del tablero por par.

Uso (desde la raíz del repo):
    uv run python scripts/calibracion/control.py CALIBRACION.yaml CARPETA [CARPETA ...]
        [--tablero 9x6] [--cuadrado-mm 38]

Sirve para ver si una calibración sigue valiendo otro día (estabilidad entre sesiones):
- error vertical: diferencia de fila entre ojos después de rectificar; si crece, los ojos
  se movieron entre sí y hay que recalibrar.
- escala: tamaño del tablero triangulado / tamaño real (Umeyama). Un corrimiento en la
  disparidad aparece como escala > 0 que crece con la distancia.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

from visionx.calibration.board import Checkerboard
from visionx.calibration.calibrate import similarity_scale
from visionx.calibration.detection import detect_corners, match_order
from visionx.calibration.models import undistort_points
from visionx.calibration.storage import StereoCalibration

p = argparse.ArgumentParser()
p.add_argument("calibracion")
p.add_argument("carpetas", nargs="+")
p.add_argument("--tablero", default="9x6")
p.add_argument("--cuadrado-mm", type=float, default=38.0)
a = p.parse_args()

cal = StereoCalibration.load(a.calibracion)
cols, filas = (int(x) for x in a.tablero.split("x"))
board = Checkerboard(cols, filas, a.cuadrado_mm / 1000)
P1, P2 = cal.rect.P1, cal.rect.P2

verticales, escalas = [], []
for carpeta in a.carpetas:
    c = Path(carpeta)
    for n in sorted(int(f.stem.split("_")[1]) for f in c.glob("left_*.jpg")):
        izq = cv2.imread(str(c / f"left_{n}.jpg"))
        der = cv2.imread(str(c / f"right_{n}.jpg"))
        cl, cr = detect_corners(izq, board), detect_corners(der, board)
        if cl is None or cr is None:
            print(f"{c.parent.name}#{n}: sin tablero en los dos ojos")
            continue
        pr, _ = match_order(cl.points, cr.points)
        # Píxeles originales -> rectificados: en una buena calibración, misma fila en los dos ojos.
        ul = undistort_points(cal.model, cl.points, cal.left, cal.rect.R1, P1).reshape(-1, 2)
        ur = undistort_points(cal.model, pr, cal.right, cal.rect.R2, P2).reshape(-1, 2)
        dy = np.abs(ul[:, 1] - ur[:, 1])
        X = cv2.triangulatePoints(P1, P2, ul.T, ur.T)
        X = (X[:3] / X[3]).T  # metros, sistema del ojo izquierdo rectificado
        escala = (similarity_scale(board.object_points().astype(np.float64), X) - 1) * 100
        verticales.append(dy)
        escalas.append(escala)
        print(
            f"{c.parent.name}#{n:3d}  Z {X[:, 2].mean():.2f} m  "
            f"vertical mediana {np.median(dy):.3f} P95 {np.percentile(dy, 95):.3f} px  "
            f"escala {escala:+.2f} %"
        )

if not escalas:
    raise SystemExit("no se detectó el tablero en ningún par")
dy = np.concatenate(verticales)
print(
    f"TOTAL {len(escalas)} pares: vertical mediana {np.median(dy):.3f} px, "
    f"P95 {np.percentile(dy, 95):.3f} px | "
    f"escala mediana {np.median(escalas):+.2f} % (de {min(escalas):+.2f} a {max(escalas):+.2f})"
)
