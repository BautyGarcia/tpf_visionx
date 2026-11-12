"""Modos reales de la ELP y prueba larga de captura (T02). También sirve de calentamiento.

Uso (cámara quieta sobre la mesa, nada más usándola):
    uv run python scripts/calibracion/modos.py CARPETA [--video 1]
        [--largo 2560x720:10 3840x1080:30]

1. Pide cada resolución candidata, anota lo que la cámara entrega de verdad y mide FPS 8 s.
2. Para cada modo de --largo (ANCHOxALTO:MINUTOS) captura sin parar y registra, por segundo,
   FPS, huecos entre cuadros (> 1,5 veces el intervalo típico) y memoria del proceso.
   El último modo de la lista queda transmitiendo hasta el final: dejarlo en 3840x1080.

Guarda modos.csv, largo_<modo>.csv y resumen.txt en CARPETA.
"""

import argparse
import csv
import platform
import resource
import time
from pathlib import Path

import cv2
import numpy as np

CANDIDATOS = [(3840, 1080), (2560, 960), (2560, 720), (1920, 1080), (1280, 480), (640, 240)]

p = argparse.ArgumentParser()
p.add_argument("carpeta")
p.add_argument("--video", type=int, default=1)
p.add_argument("--largo", nargs="*", default=["2560x720:10", "3840x1080:30"])
a = p.parse_args()
out = Path(a.carpeta)
out.mkdir(parents=True, exist_ok=False)
resumen = [f"equipo: {platform.platform()}  OpenCV {cv2.__version__}  video {a.video}"]


def abrir(w, h):
    cap = cv2.VideoCapture(a.video)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    return cap


def memoria_mb():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 1e6 if platform.system() == "Darwin" else rss / 1e3  # macOS da bytes, Linux KB


# --- 1. Enumeración -------------------------------------------------------------------------
with open(out / "modos.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["pedido", "entregado", "fps_medido", "fps_informado", "cuadros"])
    for cw, ch in CANDIDATOS:
        cap = abrir(cw, ch)
        ok, frame = cap.read()
        if not ok:
            w.writerow([f"{cw}x{ch}", "sin imagen", "", "", 0])
            cap.release()
            continue
        for _ in range(10):  # descartar el arranque
            cap.read()
        n, t0 = 0, time.monotonic()
        while time.monotonic() - t0 < 8:
            if cap.read()[0]:
                n += 1
        fps = n / (time.monotonic() - t0)
        real = f"{frame.shape[1]}x{frame.shape[0]}"
        w.writerow([f"{cw}x{ch}", real, f"{fps:.1f}", f"{cap.get(cv2.CAP_PROP_FPS):.1f}", n])
        f.flush()
        linea = f"pedido {cw}x{ch} -> entrega {real}, {fps:.1f} fps"
        print(linea, flush=True)
        resumen.append(linea)
        cap.release()

# --- 2. Pruebas largas ----------------------------------------------------------------------
for modo in a.largo:
    res, minutos = modo.split(":")
    cw, ch = (int(x) for x in res.split("x"))
    cap = abrir(cw, ch)
    ok, frame = cap.read()
    if not ok or frame.shape[:2] != (ch, cw):
        linea = f"largo {res}: la cámara no entrega ese modo ({None if not ok else frame.shape})"
        print(linea)
        resumen.append(linea)
        cap.release()
        continue
    print(f"prueba larga {res} durante {minutos} min ...", flush=True)
    tiempos, fallos = [], 0
    t0 = time.monotonic()
    fin = t0 + float(minutos) * 60
    seg_sig = t0 + 1
    with open(out / f"largo_{res}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["segundo", "cuadros", "fallos_lectura", "memoria_max_mb"])
        n_seg, fallos_seg = 0, 0
        while time.monotonic() < fin:
            ok, _ = cap.read()
            ahora = time.monotonic()
            if ok:
                tiempos.append(ahora)
                n_seg += 1
            else:
                fallos += 1
                fallos_seg += 1
            if ahora >= seg_sig:
                s = int(seg_sig - t0)
                w.writerow([s, n_seg, fallos_seg, f"{memoria_mb():.0f}"])
                if s % 60 == 0:
                    f.flush()
                    print(f"  {s // 60:3d} min  {n_seg} fps", flush=True)
                n_seg, fallos_seg = 0, 0
                seg_sig += 1
    cap.release()
    dt = np.diff(tiempos)
    tipico = float(np.median(dt))
    huecos = dt[dt > 1.5 * tipico]
    linea = (
        f"largo {res} {minutos} min: {len(tiempos)} cuadros, "
        f"{len(tiempos) / (tiempos[-1] - tiempos[0]):.2f} fps promedio, "
        f"intervalo típico {tipico * 1000:.1f} ms, "
        f"{len(huecos)} huecos (> {1.5 * tipico * 1000:.0f} ms; máximo {dt.max() * 1000:.0f} ms), "
        f"{fallos} lecturas fallidas, memoria máx {memoria_mb():.0f} MB"
    )
    print(linea, flush=True)
    resumen.append(linea)

(out / "resumen.txt").write_text("\n".join(resumen) + "\n", encoding="utf-8")
print("listo:", out / "resumen.txt")
