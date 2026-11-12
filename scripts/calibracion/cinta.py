"""Prueba con cinta métrica: distancia que mide el estéreo vs. distancia medida a mano.

Uso (desde la raíz del repo):
    uv run python scripts/calibracion/cinta.py CALIBRACION.yaml CARPETA
        [--video 1] [--tablero 9x6] [--cuadrado-mm 38]

Con el tablero apoyado y quieto, apretar `a` en la ventana: toma 3 pares seguidos,
triangula las esquinas y pide en la terminal la distancia medida con cinta. `q` sale.
El estéreo informa la distancia desde el punto medio entre lentes al centro del damero.

Montaje que funcionó (BITACORA 2026-11-12): damero vertical, de frente y centrado, sobre el
borde delantero del apoyo; cinta sobre el piso entre la vertical del vidrio de la lente y la
de la cara impresa. Ese cero queda ~14 mm delante del centro óptico. Control sin calibración:
el ancho del damero en píxeles es inversamente proporcional a la distancia; si el cociente
entre dos mediciones no coincide con el de la cinta, el montaje está mal, no la cámara.

Guarda los pares (left_N/right_N.jpg) y resultados.csv en CARPETA.
"""

import argparse
import csv
import time
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
p.add_argument("carpeta")
p.add_argument("--video", type=int, default=1)
p.add_argument("--tablero", default="9x6")
p.add_argument("--cuadrado-mm", type=float, default=38.0)
a = p.parse_args()

cal = StereoCalibration.load(a.calibracion)
cols, rows = (int(x) for x in a.tablero.split("x"))
board = Checkerboard(cols, rows, a.cuadrado_mm / 1000)
P1, P2 = cal.rect.P1, cal.rect.P2
B = cal.baseline_m
out = Path(a.carpeta)
out.mkdir(parents=True, exist_ok=True)
nuevo = not (out / "resultados.csv").exists()
fcsv = open(out / "resultados.csv", "a", newline="")
w = csv.writer(fcsv)
if nuevo:
    w.writerow(
        [
            "medicion",
            "pares",
            "cinta_m",
            "estereo_m",
            "desvio_mm",
            "diferencia_mm",
            "error_pct",
            "Z_m",
            "escala_tablero_pct",
            "hora",
        ]
    )
    fcsv.flush()  # sin esto el conteo de abajo no ve el encabezado y la primera medición sale 0
n_par = len(list(out.glob("left_*.jpg")))
n_med = sum(1 for _ in open(out / "resultados.csv")) - 1


def medir(izq, der):
    """Distancia (m) del punto medio entre lentes al centro del damero, Z y escala (%)."""
    cl, cr = detect_corners(izq, board), detect_corners(der, board)
    if cl is None or cr is None:
        return None
    pr, _ = match_order(cl.points, cr.points)
    # Píxeles originales -> rectificados (misma fila en los dos ojos) -> triangulación.
    ul = undistort_points(cal.model, cl.points, cal.left, cal.rect.R1, P1)
    ur = undistort_points(cal.model, pr, cal.right, cal.rect.R2, P2)
    X = cv2.triangulatePoints(P1, P2, ul.T, ur.T)
    X = (X[:3] / X[3]).T  # (N, 3) en metros, sistema del ojo izquierdo rectificado
    centro = X.mean(axis=0)  # centro del patrón de esquinas = centro del damero
    medio = np.array([B / 2, 0.0, 0.0])  # el ojo derecho rectificado está en x = +B
    # Escala del tablero triangulado vs. el real (Umeyama, sin el sesgo de medir vecinos).
    escala = similarity_scale(board.object_points().astype(np.float64), X)
    return float(np.linalg.norm(centro - medio)), float(centro[2]), (escala - 1) * 100


cap = cv2.VideoCapture(a.video)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
ok, frame = cap.read()
if not ok or frame.shape[:2] != (1080, 3840):
    raise SystemExit(f"la cámara {a.video} no entrega 3840x1080: {None if not ok else frame.shape}")
print(
    f"calibración {cal.calibration_id}, baseline {B * 1000:.2f} mm. "
    "Apretá 'a' con el tablero quieto."
)

msg = "a = medir   q = salir"
while True:
    ok, frame = cap.read()
    if not ok:
        continue
    vista = cv2.resize(frame, None, fx=0.4, fy=0.4)
    cv2.rectangle(vista, (0, 0), (vista.shape[1], 60), (0, 0, 0), -1)
    cv2.putText(vista, msg, (15, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
    cv2.imshow("cinta", vista)
    k = cv2.waitKey(1) & 0xFF
    if k == ord("q"):
        break
    if k != ord("a"):
        continue
    medidas, pares = [], []
    for _ in range(3):
        for _ in range(5):  # vaciar el buffer: queremos imágenes nuevas, no encoladas
            cap.grab()
        ok, frame = cap.read()
        if not ok:
            continue
        izq, der = frame[:, :1920].copy(), frame[:, 1920:].copy()
        n_par += 1
        cv2.imwrite(str(out / f"left_{n_par}.jpg"), izq)
        cv2.imwrite(str(out / f"right_{n_par}.jpg"), der)
        r = medir(izq, der)
        if r is None:
            print(f"  par {n_par}: no se encontró el tablero en los dos ojos")
        else:
            medidas.append(r)
            pares.append(n_par)
            print(f"  par {n_par}: {r[0]:.4f} m")
        time.sleep(0.3)
    if not medidas:
        msg = "no se detecto el tablero: acercalo o mejora la luz"
        continue
    d = np.array([m[0] for m in medidas])
    z = np.mean([m[1] for m in medidas])
    esc = np.mean([m[2] for m in medidas])
    print(
        f"estéreo: {d.mean():.4f} m (desvío {d.std() * 1000:.1f} mm, Z {z:.4f} m, "
        f"escala del tablero {esc:+.2f} %)"
    )
    txt = (
        input("distancia con cinta en metros (ej. 1.000), Enter = no guardar: ")
        .strip()
        .replace(",", ".")
    )
    if not txt:
        msg = "medicion descartada"
        continue
    cinta = float(txt)
    dif = (d.mean() - cinta) * 1000
    n_med += 1
    w.writerow(
        [
            n_med,
            " ".join(map(str, pares)),
            f"{cinta:.4f}",
            f"{d.mean():.4f}",
            f"{d.std() * 1000:.1f}",
            f"{dif:+.1f}",
            f"{dif / cinta / 10:+.2f}",
            f"{z:.4f}",
            f"{esc:+.2f}",
            time.strftime("%H:%M:%S"),
        ]
    )
    fcsv.flush()
    print(
        f"==> medición {n_med}: cinta {cinta:.3f} m, estéreo {d.mean():.3f} m, "
        f"diferencia {dif:+.1f} mm ({dif / cinta / 10:+.2f} %)"
    )
    msg = f"{n_med}: cinta {cinta:.2f} m  estereo {d.mean():.3f} m  dif {dif:+.0f} mm"

cap.release()
cv2.destroyAllWindows()
fcsv.close()
