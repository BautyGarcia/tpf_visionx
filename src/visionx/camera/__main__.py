"""Comandos de captura (T02).

    uv run python -m visionx.camera ver [--config X]
    uv run python -m visionx.camera modos [--config X] [--segundos 5]
    uv run python -m visionx.camera grabar CARPETA [--segundos 60] [--formato jpg|png]
        [--cada 1] [--cola 8] [--config X]
    uv run python -m visionx.camera verificar CARPETA

La cámara se configura en la sección `camera` de configs/default.yaml; el índice y el backend
de cada computadora van en un override explícito (por ejemplo configs/local.yaml + --config).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from visionx.camera.recording import ImageFormat, Recorder, timing_summary
from visionx.camera.replay import ReplaySource
from visionx.camera.usb import CameraSettings, UsbStereoSource, open_capture
from visionx.shared.config import ROOT, load_config
from visionx.shared.errors import SourceError

# Modos que vale la pena probar en la ELP (cuadro SBS completo). BITACORA 2026-11-12.
MODOS_CANDIDATOS = [(3840, 1080), (2560, 960), (2560, 720), (1920, 1080), (1280, 480), (640, 240)]


def _settings(config: str | None) -> tuple[CameraSettings, dict[str, Any]]:
    cfg = load_config(config)
    return CameraSettings.from_config(cfg), cfg


def _calibration_info(cfg: dict[str, Any]) -> dict[str, Any]:
    """Calibración configurada al grabar (informativo: se graba el par sin rectificar)."""
    path = (cfg.get("camera") or {}).get("calibration")
    if not path:
        return {}
    full = Path(path) if Path(path).is_absolute() else ROOT / path
    info: dict[str, Any] = {"ruta": str(path)}
    try:
        from visionx.calibration import StereoCalibration

        info["calibration_id"] = StereoCalibration.load(full).calibration_id
    except (OSError, ValueError) as exc:
        info["error"] = str(exc)
    return info


# --- ver --------------------------------------------------------------------------------


def cmd_ver(args: argparse.Namespace) -> int:
    settings, _ = _settings(args.config)
    source = UsbStereoSource(settings, session_id="vista")
    print("Tapá con la mano el lente que, mirando desde atrás de la cámara, queda a la izquierda:")
    print("la mitad rotulada IZQUIERDO tiene que oscurecerse. Si se oscurece la otra, poner")
    print("camera.swap_eyes: true en la config. Tecla q para salir.")
    try:
        while True:
            frame = source.read()
            panels = []
            for name, image in (("IZQUIERDO", frame.left), ("DERECHO", frame.right)):
                small = cv2.resize(image, (640, int(640 * image.shape[0] / image.shape[1])))
                cv2.putText(small, name, (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                panels.append(small)
            cv2.imshow("VisionX - ojos", np.hstack(panels))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                return 0
    finally:
        source.close()
        cv2.destroyAllWindows()


# --- modos ------------------------------------------------------------------------------


def cmd_modos(args: argparse.Namespace) -> int:
    """Pide cada modo candidato, anota lo que entrega la cámara y mide FPS."""
    base, _ = _settings(args.config)
    print(f"cámara {base.device}, backend {base.backend}, fourcc {base.fourcc}")
    print("pedido      entregado   fps_medido  fps_informado")
    for w, h in MODOS_CANDIDATOS:
        settings = CameraSettings(
            device=base.device, backend=base.backend, capture_size=(w, h), fourcc=base.fourcc,
            fps=base.fps,
        )  # fmt: skip
        cap = open_capture(settings)
        try:
            ok, image = cap.read()
            if not ok or image is None:
                print(f"{w}x{h:<7} sin imagen")
                continue
            for _ in range(10):  # descartar el arranque
                cap.read()
            n, t0 = 0, time.monotonic()
            while time.monotonic() - t0 < args.segundos:
                n += bool(cap.read()[0])
            fps = n / (time.monotonic() - t0)
            got = f"{image.shape[1]}x{image.shape[0]}"
            informed = cap.get(cv2.CAP_PROP_FPS)
            print(f"{w}x{h:<7} {got:<11} {fps:10.1f}  {informed:13.1f}")
        finally:
            cap.release()
    print("CAP_PROP_FPS no es confiable en la ELP: usar fps_medido.")
    return 0


# --- grabar -----------------------------------------------------------------------------


def cmd_grabar(args: argparse.Namespace) -> int:
    settings, cfg = _settings(args.config)
    if args.cada < 1:
        print("--cada tiene que ser >= 1", file=sys.stderr)
        return 2
    info = {
        "camara": settings.describe(),
        "calibracion_configurada": _calibration_info(cfg),
        "cada": args.cada,
        "nota": args.nota or "",
    }
    # Primero la cámara: si no abre, no queda una carpeta de grabación vacía.
    source = UsbStereoSource(settings)
    try:
        recorder = Recorder(
            args.carpeta, image_format=ImageFormat(args.formato), queue_size=args.cola, info=info
        )
    except BaseException:
        source.close()
        raise
    print(f"grabando sesión {source.session_id} en {args.carpeta} (Ctrl+C para terminar)")
    received: list[int] = []
    t_end = time.monotonic() + args.segundos if args.segundos else None
    error: str | None = None
    try:
        while t_end is None or time.monotonic() < t_end:
            frame = source.read()
            received.append(frame.received_ns)
            if frame.frame_id % args.cada == 0:
                recorder.write(frame)
            if frame.frame_id and frame.frame_id % 300 == 0:
                print(f"  {frame.frame_id} pares leídos, {recorder.stored} guardados", flush=True)
    except KeyboardInterrupt:
        print("interrumpido por el usuario")
    except SourceError as exc:
        error = str(exc)
        print(f"error de cámara: {exc}", file=sys.stderr)
    finally:
        source.close()
        recorder.info["lectura"] = {
            **timing_summary(received),
            "fallos_lectura": source.stats.read_failures,
            "reconexiones": source.stats.reconnects,
            "error": error,
        }
        manifest = recorder.close()
    lectura = recorder.info["lectura"]
    print(
        f"leídos {lectura.get('pares', 0)} pares a {lectura.get('fps_efectivo')} fps; "
        f"guardados {manifest['pares']}, "
        f"descartados por disco {manifest['descartados']['cantidad']}"
    )
    return 1 if error else 0


# --- verificar --------------------------------------------------------------------------


def cmd_verificar(args: argparse.Namespace) -> int:
    try:
        source = ReplaySource(args.carpeta)
        original: list[int] = []
        size = None
        while (frame := source.read()) is not None:
            original.append(frame.replay_original_ns or 0)
            size = frame.size
    except SourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    m = source.manifest
    print(f"sesión {m.get('session_id')}  estado {m.get('estado')}  ojo {size}")
    print(f"pares legibles con hash correcto: {len(original)} de {len(source)}")
    print(f"tiempos grabados: {timing_summary(original)}")
    print(f"descartados al grabar: {m.get('descartados', {}).get('cantidad', 0)}")
    if source.truncated:
        print("aviso: la última línea del índice quedó a medio escribir y se ignoró")
    if m.get("estado") != "cerrada":
        print("aviso: la grabación no se cerró normalmente")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m visionx.camera",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ver", help="ventana con los dos ojos rotulados")
    p.add_argument("--config")
    p.set_defaults(fn=cmd_ver)

    p = sub.add_parser("modos", help="modos que entrega la cámara y FPS medidos")
    p.add_argument("--config")
    p.add_argument("--segundos", type=float, default=5.0)
    p.set_defaults(fn=cmd_modos)

    p = sub.add_parser("grabar", help="grabar pares sin rectificar en una carpeta nueva")
    p.add_argument("carpeta")
    p.add_argument("--segundos", type=float, default=60.0, help="0 = hasta Ctrl+C")
    p.add_argument("--formato", choices=["jpg", "png"], default="jpg")
    p.add_argument("--cada", type=int, default=1, help="guardar 1 de cada N pares leídos")
    p.add_argument("--cola", type=int, default=8, help="pares en espera de disco (0 = sin hilo)")
    p.add_argument("--nota", help="texto libre para el manifiesto (escena, iluminación...)")
    p.add_argument("--config")
    p.set_defaults(fn=cmd_grabar)

    p = sub.add_parser("verificar", help="reproducir una grabación y comprobar sus hashes")
    p.add_argument("carpeta")
    p.set_defaults(fn=cmd_verificar)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
