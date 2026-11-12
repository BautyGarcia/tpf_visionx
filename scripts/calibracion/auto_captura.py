"""Captura estéreo sin manos: saca la foto sola cuando el tablero queda quieto.

Uso:
    uv run python scripts/calibracion/auto_captura.py CARPETA/calib
        [--video 1] [--tablero 9x6] [--quieto 1.0]

Reglas:
- Saca foto cuando los dos ojos ven el tablero entero y las esquinas se movieron menos
  de --tolerancia px durante --quieto segundos.
- Después de una foto, la próxima exige mover el tablero al menos --mover px (promedio de
  esquinas) o sacarlo de cuadro: así no salen dos fotos iguales.
- Suena un "ding" y dice el número de foto en voz alta.
- Teclas: q = salir, u = borrar la última foto, espacio = pausa / seguir.

Guarda left_N.jpg / right_N.jpg en el mismo formato que calib-stereo y sigue la numeración
de lo que ya haya en la carpeta.
"""

import argparse
import re
import subprocess
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

ESCALA = 0.7  # misma escala de detección que calib-stereo: mismo alcance (~1,4 m con A3)
FLAGS = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FAST_CHECK


def detectar(img, patron):
    """Esquinas en coordenadas de la imagen completa, o None si no está el tablero entero."""
    chica = cv2.resize(img, None, fx=ESCALA, fy=ESCALA, interpolation=cv2.INTER_AREA)
    gris = cv2.cvtColor(chica, cv2.COLOR_BGR2GRAY)
    ok, esq = cv2.findChessboardCorners(gris, patron, FLAGS)
    return esq.reshape(-1, 2) / ESCALA if ok else None


class Disparador:
    """Decide cuándo sacar la foto a partir de la secuencia de detecciones."""

    def __init__(self, quieto, tolerancia, mover):
        self.quieto, self.tolerancia, self.mover = quieto, tolerancia, mover
        self.historial = deque()  # (t, esquinas izquierda+derecha)
        self.ultima = None  # esquinas de la última foto; None = listo para la próxima

    def paso(self, t, izq, der):
        """Devuelve (disparar, estado) para mostrar en pantalla."""
        if izq is None or der is None:
            self.historial.clear()
            self.ultima = None  # sacar el tablero de cuadro también habilita la próxima
            return False, "sin tablero en los dos ojos"
        esq = np.vstack([izq, der])
        if self.ultima is not None:
            if np.linalg.norm(esq - self.ultima, axis=1).mean() < self.mover:
                return False, "listo: mové el tablero a la próxima pose"
            self.ultima = None
        # Quieto = ninguna esquina se movió más que la tolerancia respecto de la primera
        # detección de la ventana. Si alguna se movió, la ventana arranca de nuevo.
        if self.historial and np.abs(esq - self.historial[0][1]).max() > self.tolerancia:
            self.historial.clear()
        self.historial.append((t, esq))
        quieto_hace = t - self.historial[0][0]
        if quieto_hace >= self.quieto:
            self.historial.clear()
            self.ultima = esq
            return True, "FOTO"
        return False, f"quieto {quieto_hace:.1f}/{self.quieto:.1f} s"


def siguiente_numero(carpeta):
    nums = [
        int(m.group(1))
        for p in carpeta.glob("left_*.jpg")
        if (m := re.match(r"left_(\d+)\.jpg", p.name))
    ]
    return max(nums, default=0) + 1


def avisar(n):
    subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
    subprocess.Popen(["say", "-r", "220", str(n)])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("carpeta")
    p.add_argument("--video", type=int, default=1)
    p.add_argument("--tablero", default="9x6")
    p.add_argument("--quieto", type=float, default=1.0, help="segundos quieto antes de disparar")
    p.add_argument("--tolerancia", type=float, default=2.0, help="px de movimiento aceptado")
    p.add_argument("--mover", type=float, default=40.0, help="px a mover entre fotos")
    a = p.parse_args()

    patron = tuple(int(x) for x in a.tablero.split("x"))
    carpeta = Path(a.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    n = siguiente_numero(carpeta)
    sacadas = []

    cap = cv2.VideoCapture(a.video)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    ok, frame = cap.read()
    if not ok or frame.shape[:2] != (1080, 3840):
        raise SystemExit(
            f"la cámara {a.video} no entrega 3840x1080: {None if not ok else frame.shape}"
        )

    disp = Disparador(a.quieto, a.tolerancia, a.mover)
    pausa = False
    print(f"guardando en {carpeta}, próxima foto: {n}")
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        izq, der = frame[:, :1920], frame[:, 1920:]
        t = time.monotonic()
        if pausa:
            estado, disparar = "PAUSA (espacio para seguir)", False
            ci = cd = None
        else:
            ci, cd = detectar(izq, patron), detectar(der, patron)
            disparar, estado = disp.paso(t, ci, cd)
        if disparar:
            cv2.imwrite(str(carpeta / f"left_{n}.jpg"), izq)
            cv2.imwrite(str(carpeta / f"right_{n}.jpg"), der)
            sacadas.append(n)
            print(f"foto {n}")
            avisar(n)
            n += 1

        # Vista previa en chico, con letras grandes para leer de lejos.
        vista = cv2.resize(frame, None, fx=0.4, fy=0.4)
        for esq, dx in ((ci, 0), (cd, 1920)):
            if esq is not None:
                pts = ((esq + [dx, 0]) * 0.4).reshape(-1, 1, 2).astype(np.float32)
                cv2.drawChessboardCorners(vista, patron, pts, True)
        color = (0, 255, 0) if disparar or estado.startswith("quieto") else (0, 200, 255)
        cv2.rectangle(vista, (0, 0), (vista.shape[1], 70), (0, 0, 0), -1)
        cv2.putText(
            vista,
            f"{len(sacadas)} fotos | {estado}",
            (15, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.4,
            color,
            3,
        )
        cv2.imshow("auto-captura", vista)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if tecla == ord(" "):
            pausa = not pausa
            disp.historial.clear()
        if tecla == ord("u") and sacadas:
            m = sacadas.pop()
            (carpeta / f"left_{m}.jpg").unlink(missing_ok=True)
            (carpeta / f"right_{m}.jpg").unlink(missing_ok=True)
            n = m
            print(f"borrada foto {m}")
            subprocess.Popen(["say", f"borrada {m}"])

    cap.release()
    cv2.destroyAllWindows()
    print(f"{len(sacadas)} fotos nuevas en {carpeta}")


if __name__ == "__main__":
    main()
