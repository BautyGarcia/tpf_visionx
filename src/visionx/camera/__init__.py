"""Captura USB, grabación y replay de pares estéreo (T02).

Desde la terminal (ver `python -m visionx.camera --help`):

    uv run python -m visionx.camera ver                 # comprobar que los ojos no estén invertidos
    uv run python -m visionx.camera modos               # qué modos entrega la cámara y a qué FPS
    uv run python -m visionx.camera grabar recordings/prueba --segundos 60
    uv run python -m visionx.camera verificar recordings/prueba

Desde código, todas las fuentes cumplen FrameSource y se pueden intercambiar:

    source = UsbStereoSource(CameraSettings.from_config(load_config()))
    source = ReplaySource("recordings/prueba")
    source = RectifiedSource(source, StereoCalibration.load(ruta))   # opcional
    while (frame := source.read()) is not None:
        ...
"""

from visionx.camera.recording import ImageFormat, Recorder, timing_summary
from visionx.camera.rectified import RectifiedSource
from visionx.camera.replay import ReplaySource, load_recording
from visionx.camera.sbs import split_sbs
from visionx.camera.usb import CameraSettings, UsbStereoSource, new_session_id

__all__ = [
    "CameraSettings",
    "ImageFormat",
    "Recorder",
    "RectifiedSource",
    "ReplaySource",
    "UsbStereoSource",
    "load_recording",
    "new_session_id",
    "split_sbs",
    "timing_summary",
]
