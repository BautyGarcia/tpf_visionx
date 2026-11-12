"""Prueba de deriva: guarda un par estéreo cada INTERVALO segundos, sin tocar nada.

Uso (cámara y tablero quietos todo el tiempo):
    uv run python scripts/calibracion/deriva_captura.py CARPETA
        [--video 1] [--intervalo 30] [--minutos 45]

Guarda left_N.jpg / right_N.jpg (mismo formato que calib-stereo) y tiempos.csv con el
segundo de cada par desde que se abrió la cámara. Cortar antes con Ctrl+C.
"""

import argparse
import csv
import time
from pathlib import Path

import cv2

p = argparse.ArgumentParser()
p.add_argument("carpeta")
p.add_argument("--video", type=int, default=1)
p.add_argument("--intervalo", type=float, default=30.0)
p.add_argument("--minutos", type=float, default=45.0)
a = p.parse_args()

out = Path(a.carpeta)
out.mkdir(parents=True, exist_ok=False)  # carpeta nueva: no pisar otra prueba

# Mismos pedidos que calib-stereo (cfg/stereo.yaml): par lado a lado de 3840x1080.
cap = cv2.VideoCapture(a.video)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
ok, frame = cap.read()
if not ok or frame.shape[1] != 3840 or frame.shape[0] != 1080:
    raise SystemExit(f"la cámara {a.video} no entrega 3840x1080: {None if not ok else frame.shape}")

t0 = time.monotonic()
with open(out / "tiempos.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["par", "segundos", "hora"])
    n = 0
    try:
        while time.monotonic() - t0 < a.minutos * 60:
            # Vaciar el buffer para que el par sea el más reciente, no uno viejo encolado.
            for _ in range(5):
                cap.grab()
            ok, frame = cap.read()
            if not ok:
                print("no llegó imagen; reintento")
                continue
            n += 1
            half = frame.shape[1] // 2  # izquierda = mitad izquierda, como calib-stereo
            cv2.imwrite(str(out / f"left_{n}.jpg"), frame[:, :half])
            cv2.imwrite(str(out / f"right_{n}.jpg"), frame[:, half:])
            s = time.monotonic() - t0
            w.writerow([n, f"{s:.1f}", time.strftime("%H:%M:%S")])
            f.flush()
            print(f"par {n:3d}  {s / 60:5.1f} min", flush=True)
            time.sleep(max(0.0, a.intervalo - (time.monotonic() - t0 - s)))
    except KeyboardInterrupt:
        print("cortado a mano")
cap.release()
print(f"{n} pares en {out}")
