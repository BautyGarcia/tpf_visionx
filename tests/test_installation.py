"""Regresiones de configuración e instalación; no requieren cámara ni red."""

from subprocess import CompletedProcess

import pytest

from visionx import cli
from visionx.devtools import worklog
from visionx.shared import config


@pytest.mark.parametrize("text", ["[]", "false", "0", "hello", "{1: x}"])
def test_config_rejects_non_mapping(tmp_path, text):
    p = tmp_path / "bad.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="mapping YAML"):
        config.load_config(p)


def test_overrides_are_explicit_and_do_not_mutate_defaults(tmp_path):
    p = tmp_path / "local.yaml"
    p.write_text("camera:\n  device: 7\n", encoding="utf-8")
    cfg = config.load_config(p)
    assert cfg["camera"]["device"] == 7 and cfg["camera"]["fps"] == 30
    assert config.load_config()["camera"]["device"] == 0


def test_runtime_doctor_does_not_require_git_hooks(monkeypatch):
    def forbidden():
        raise AssertionError("runtime no debe consultar hooks")

    monkeypatch.setattr(cli, "_hooks", forbidden)
    monkeypatch.setattr(cli, "_torch", lambda: "no instalado")
    assert cli.main(["doctor", "--runtime-only"]) == 0


def test_doctor_uses_explicit_override(tmp_path, capsys):
    p = tmp_path / "override.yaml"
    p.write_text("calibration:\n  dictionary: DICT_INEXISTENTE\n", encoding="utf-8")
    assert cli.main(["doctor", "--runtime-only", "--config", str(p)]) == 1
    assert "FALLA" in capsys.readouterr().out


def test_log_outside_checkout_fails_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(worklog, "ROOT", tmp_path)
    assert cli.main(["log", "tema"]) == 1
    assert "requiere un checkout" in capsys.readouterr().err


def test_local_file_in_cwd_is_not_loaded_implicitly(tmp_path, monkeypatch):
    # Un local.yaml existente no debe modificar la ejecución si nadie lo pidió.
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "local.yaml").write_text("camera:\n  device: 99\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert config.load_config()["camera"]["device"] == 0


def test_empty_override_keeps_defaults(tmp_path):
    override_path = tmp_path / "empty.yaml"
    override_path.write_text("", encoding="utf-8")
    assert config.load_config(override_path) == config.load_config()


def test_worklog_preserves_first_porcelain_status_column(monkeypatch):
    """El primer archivo no debe perder su primera letra al registrar cambios."""

    def git_output(command, **kwargs):
        if command[1:] == ["status", "--porcelain"]:
            output = " M README.md\n M src/visionx/cli.py\n"
        else:
            output = ""
        return CompletedProcess(command, 0, stdout=output)

    monkeypatch.setattr(worklog.subprocess, "run", git_output)
    assert worklog.changed_files() == ["README.md", "src/visionx/cli.py"]
