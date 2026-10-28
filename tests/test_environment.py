import cv2

from visionx.cli import _charuco
from visionx.shared.config import load_config


def test_config_loads_and_has_core_sections():
    cfg = load_config()
    for key in ("camera", "depth", "calibration"):
        assert key in cfg


def test_charuco_board_can_be_built():
    assert "creado" in _charuco()


def test_wls_filter_available():
    assert cv2.ximgproc.createDisparityWLSFilterGeneric(False) is not None
