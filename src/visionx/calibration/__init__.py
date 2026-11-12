"""Calibración estéreo de la ELP (T03).

Uso típico desde la terminal:

    uv run python -m visionx.calibration revisar CARPETA --tablero 9x6 --cuadrado-mm 28
    uv run python -m visionx.calibration calibrar --sesion S1 --sesion S2 \\
        --tablero 9x6 --cuadrado-mm 28 --salida outputs/calibracion/elp.yaml

Desde código:

    calib = StereoCalibration.load("outputs/calibracion/elp.yaml")
    left_r, right_r = calib.rectify(left, right)
    geometry = calib.geometry()  # StereoGeometry compartida: disparidad -> metros
"""

from visionx.calibration.board import Checkerboard
from visionx.calibration.calibrate import CalibrationOptions, CalibrationRun, calibrate
from visionx.calibration.models import LensModel
from visionx.calibration.sessions import PairView, Session, load_session
from visionx.calibration.storage import StereoCalibration, from_i308_pickle

__all__ = [
    "CalibrationOptions",
    "CalibrationRun",
    "Checkerboard",
    "LensModel",
    "PairView",
    "Session",
    "StereoCalibration",
    "calibrate",
    "from_i308_pickle",
    "load_session",
]
