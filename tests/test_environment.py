import cv2

from visionx import cli
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


def test_doctor_fails_when_required_hooks_are_missing(monkeypatch):
    def missing_hooks():
        raise RuntimeError("hooks inactivos")

    monkeypatch.setattr(cli, "_hooks", missing_hooks)
    monkeypatch.setattr(cli, "_torch", lambda: "no instalado (opcional)")
    assert cli.doctor() == 1


def test_doctor_accepts_base_environment_without_optional_ml(monkeypatch):
    monkeypatch.setattr(cli, "_hooks", lambda: "activos")
    monkeypatch.setattr(cli, "_torch", lambda: "no instalado (opcional)")
    assert cli.doctor() == 0
