"""Revisión rápida de cobertura: zona de cada foto, hacia dónde está girado el tablero y mosaico.

Uso (desde la raíz del repo):
    uv run python scripts/calibracion/zonas.py CARPETA MOSAICO.jpg [--tablero 9x6]

Para cada left_N.jpg imprime la zona 3x3 donde cae el centro del tablero (ojo izquierdo),
qué costado está más cerca de la cámara y el cociente de altos/anchos de los bordes.
El mosaico numera las fotos y dibuja la grilla 3x3 para detectar zonas repetidas a ojo.
Complementa `python -m visionx.calibration revisar`, que cuenta fotos por zona.
"""

import argparse
import re
from pathlib import Path

import cv2
import numpy as np

ESCALA = 0.7  # detección rápida a 70 %, como la herramienta de captura
FILAS = ["arriba", "medio", "abajo"]
COLUMNAS = ["izq", "centro", "der"]

p = argparse.ArgumentParser()
p.add_argument("carpeta")
p.add_argument("mosaico")
p.add_argument("--tablero", default="9x6", help="esquinas internas COLSxFILAS")
a = p.parse_args()
cols, filas = (int(x) for x in a.tablero.split("x"))
d = Path(a.carpeta)
nums = sorted(int(re.match(r"left_(\d+)", f.stem).group(1)) for f in d.glob("left_*.jpg"))

miniaturas = []
for n in nums:
    img = cv2.imread(str(d / f"left_{n}.jpg"))
    alto, ancho = img.shape[:2]
    gris = cv2.cvtColor(cv2.resize(img, None, fx=ESCALA, fy=ESCALA), cv2.COLOR_BGR2GRAY)
    ok, c = cv2.findChessboardCorners(
        gris, (cols, filas), cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    )
    texto = f"{n}: sin tablero"
    if ok:
        c = c.reshape(filas, cols, 2) / ESCALA  # vuelta a píxeles de la imagen completa
        cx, cy = c.reshape(-1, 2).mean(0)
        zona = f"{FILAS[min(2, int(3 * cy / alto))]}-{COLUMNAS[min(2, int(3 * cx / ancho))]}"
        # El costado más cercano a la cámara se ve más alto en la imagen (perspectiva).
        h0 = np.linalg.norm(c[0, 0] - c[-1, 0])
        h1 = np.linalg.norm(c[0, -1] - c[-1, -1])
        w0 = np.linalg.norm(c[0, 0] - c[0, -1])
        w1 = np.linalg.norm(c[-1, 0] - c[-1, -1])
        # OpenCV puede numerar las esquinas desde cualquier extremo: ordenar por posición.
        if c[0, 0, 0] > c[0, -1, 0]:
            h0, h1 = h1, h0
        if c[0, 0, 1] > c[-1, 0, 1]:
            w0, w1 = w1, w0
        rh, rw = h0 / h1, w0 / w1
        lado = "frente" if abs(rh - 1) < 0.08 else ("izq más cerca" if rh > 1 else "der más cerca")
        texto = f"{n}: {zona:14s} {lado:14s} (izq/der {rh:.2f}, arr/abj {rw:.2f}, ancho {w0:.0f}px)"
    print(texto)
    m = cv2.resize(img, (384, 216))
    cv2.rectangle(m, (0, 0), (60, 34), (0, 0, 0), -1)
    cv2.putText(m, str(n), (5, 28), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    for k in (1, 2):
        cv2.line(m, (128 * k, 0), (128 * k, 216), (255, 0, 255), 1)
        cv2.line(m, (0, 72 * k), (384, 72 * k), (255, 0, 255), 1)
    miniaturas.append(m)

if not miniaturas:
    raise SystemExit(f"{d}: no hay fotos left_N.jpg")
while len(miniaturas) % 5:
    miniaturas.append(np.zeros_like(miniaturas[0]))
cv2.imwrite(
    a.mosaico, np.vstack([np.hstack(miniaturas[i : i + 5]) for i in range(0, len(miniaturas), 5)])
)
print("mosaico:", a.mosaico, "(puede mostrar personas: no subir)")
