"""Ajusta y verifica la corrección de disparidad con mediciones de cinta ya guardadas.

Uso (desde la raíz del repo):
    uv run python scripts/calibracion/offset_cinta.py CALIBRACION.yaml CARPETA_CINTA
        [--ajuste 1 2 2.5 3] [--tablero 9x6] [--cuadrado-mm 38] [--salida NUEVA.yaml]

CARPETA_CINTA es la salida de `cinta.py`: left_N/right_N.jpg y resultados.csv.

Por qué (BITACORA 2026-11-12): la ELP caliente mide la disparidad δ px menor que la real.
El error en metros crece con la distancia (+3 % a 1 m, +5 % a 3 m), que es la firma de un
corrimiento fijo de disparidad y no de un error de escala. Modelo de cada medición:

    distancia_estereo(δ) = cinta + c

- δ: corrimiento de disparidad, en píxeles de la resolución calibrada. Va a la calibración.
- c: el cero de la cinta (vidrio de la lente) queda c metros delante del centro óptico.
  Es del montaje, no de la cámara: no va a la calibración, pero sirve para medir GT.

El ajuste usa solo las distancias de `--ajuste`; las demás quedan como control independiente.
Se prueba δ en una grilla fina; para cada δ, c es el promedio del desvío (cuadrados mínimos).
La verificación final recalcula todo con `calib.geometry()`, el mismo camino que usa VisionX.
"""

import argparse
import csv
import time
from pathlib import Path

import cv2
import numpy as np

from visionx.calibration.board import Checkerboard
from visionx.calibration.detection import detect_corners, match_order
from visionx.calibration.models import undistort_points
from visionx.calibration.storage import StereoCalibration

p = argparse.ArgumentParser()
p.add_argument("calibracion", help="calibración SIN corrección (se ajusta desde cero)")
p.add_argument("carpeta")
p.add_argument("--ajuste", type=float, nargs="+", default=[1.0, 2.0, 2.5, 3.0],
               help="distancias de cinta (m) usadas para ajustar; el resto es control")  # fmt: skip
p.add_argument("--tablero", default="9x6")
p.add_argument("--cuadrado-mm", type=float, default=38.0)
p.add_argument("--salida", help="guardar acá la calibración con la corrección ajustada")
a = p.parse_args()

cal = StereoCalibration.load(a.calibracion)
if cal.disparity_offset_px != 0.0:
    raise SystemExit("la calibración ya trae corrección: pasá la original para ajustar desde cero")
cols, rows = (int(x) for x in a.tablero.split("x"))
board = Checkerboard(cols, rows, a.cuadrado_mm / 1000)
g0 = cal.geometry()  # sin corrección
carpeta = Path(a.carpeta)


def esquinas(n: int):
    """Esquinas rectificadas del par n: (u, v) del ojo izquierdo y disparidad d por esquina."""
    izq = cv2.imread(str(carpeta / f"left_{n}.jpg"))
    der = cv2.imread(str(carpeta / f"right_{n}.jpg"))
    cl, cr = detect_corners(izq, board), detect_corners(der, board)
    if cl is None or cr is None:
        return None
    pr, _ = match_order(cl.points, cr.points)
    ul = undistort_points(cal.model, cl.points, cal.left, cal.rect.R1, cal.rect.P1)
    ur = undistort_points(cal.model, pr, cal.right, cal.rect.R2, cal.rect.P2)
    return ul[:, 0], ul[:, 1], ul[:, 0] - ur[:, 0]


def distancia(u, v, z, g) -> float:
    """Distancia del punto medio entre lentes al centro del damero (como cinta.py)."""
    x = (u - g.cx) * z / g.fx  # retroproyección en el sistema del ojo izquierdo rectificado
    y = (v - g.cy) * z / g.fy
    centro = np.array([x.mean(), y.mean(), z.mean()])
    return float(np.linalg.norm(centro - np.array([g.baseline_m / 2, 0.0, 0.0])))


# --- Mediciones: cinta y esquinas de cada par ---------------------------------------------
mediciones = []
with open(carpeta / "resultados.csv", newline="") as f:
    for fila in csv.DictReader(f):
        pares = [e for e in (esquinas(int(n)) for n in fila["pares"].split()) if e is not None]
        if pares:
            mediciones.append((float(fila["cinta_m"]), pares))
mediciones.sort(key=lambda m: m[0])
en_ajuste = [any(abs(cinta - x) < 1e-6 for x in a.ajuste) for cinta, _ in mediciones]
if sum(en_ajuste) < 2:
    raise SystemExit("hacen falta al menos 2 distancias de ajuste presentes en el CSV")


def distancias(delta: float) -> np.ndarray:
    """Distancia estéreo de cada medición (promedio de sus pares) con corrección delta."""
    k = g0.fx * g0.baseline_m
    return np.array([
        np.mean([distancia(u, v, k / (d + g0.doffs + delta), g0) for u, v, d in pares])
        for _, pares in mediciones
    ])  # fmt: skip


# --- Ajuste de δ y c ----------------------------------------------------------------------
cinta = np.array([m[0] for m in mediciones])
sel = np.array(en_ajuste)
mejor = None
for delta in np.arange(-2.0, 2.0, 0.0005):
    resto = distancias(delta) - cinta
    c = resto[sel].mean()
    sse = float(((resto[sel] - c) ** 2).sum())
    if mejor is None or sse < mejor[0]:
        mejor = (sse, float(delta), float(c))
_, delta, c = mejor
delta = round(delta, 4)

# --- Verificación por el camino real: calib.geometry() con la corrección -------------------
corregida = cal.with_disparity_offset(delta, {})
g = corregida.geometry()
print(f"calibración {cal.calibration_id}: δ = {delta:.4f} px, cero de cinta c = {c * 1000:.1f} mm")
print(f"{'cinta':>6} {'uso':>8} {'sin corr.':>10} {'error':>8} {'corregida':>10} {'error':>8}")
filas = []
for (cm, pares), ajuste in zip(mediciones, en_ajuste, strict=True):
    sin = np.mean([distancia(u, v, g0.fx * g0.baseline_m / (d + g0.doffs), g0)
                   for u, v, d in pares])  # fmt: skip
    con = np.mean([
        distancia(u, v, np.array([g.depth_at(float(x)) for x in d]), g) for u, v, d in pares
    ])  # fmt: skip
    # float de Python: el YAML seguro no sabe guardar escalares de NumPy.
    err_sin, err_con = float((sin - c - cm) * 1000), float((con - c - cm) * 1000)
    uso = "ajuste" if ajuste else "control"
    filas.append({"cinta_m": cm, "uso": uso, "error_sin_mm": round(err_sin, 1),
                  "error_corregido_mm": round(err_con, 1)})  # fmt: skip
    print(f"{cm:6.2f} {uso:>8} {sin - c:9.3f}m {err_sin:+7.1f} {con - c:9.3f}m {err_con:+7.1f}")

if a.salida:
    fuente = {
        "fecha_ajuste": time.strftime("%Y-%m-%d"),
        "metodo": "scripts/calibracion/offset_cinta.py: grilla de δ, c por cuadrados mínimos",
        "calibracion_base": cal.calibration_id,
        "datos": f"{carpeta.name} (cinta.py, 3 pares por distancia, BITACORA 2026-11-12)",
        "tablero": f"{a.tablero}, cuadrado {a.cuadrado_mm} mm",
        "distancias_ajuste_m": [float(x) for x in cinta[sel]],
        "distancias_control_m": [float(x) for x in cinta[~sel]],
        "cero_cinta_mm": round(c * 1000, 1),
        "nota_cero": "el centro óptico queda cero_cinta_mm detrás del vidrio; no se aplica a Z",
        "errores_mm": filas,
        "decision": "BITACORA 2026-11-13: se acepta; no se repite por día, se asume estable",
    }
    print(f"guardada en {cal.with_disparity_offset(delta, fuente).save(a.salida)}")
