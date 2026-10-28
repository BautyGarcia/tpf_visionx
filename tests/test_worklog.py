from datetime import datetime

from visionx.devtools import worklog


def test_slugify_handles_accents_and_spaces():
    assert worklog.slugify("Calibración ChArUco, sesión 2") == "calibracion-charuco-sesion-2"


def test_new_entry_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(worklog, "LOG_DIR", tmp_path)
    path = worklog.new_entry(
        "Prueba de registro", agente="claude-code", tarea="C01", now=datetime(2026, 10, 28, 15, 30)
    )
    text = path.read_text(encoding="utf-8")
    assert path.name.startswith("2026-10-28-1530-")
    assert path.name.endswith("-prueba-de-registro.md")
    assert "tarea: C01" in text and "## Qué se hizo" in text


def test_recent_reads_front_matter(tmp_path, monkeypatch):
    monkeypatch.setattr(worklog, "LOG_DIR", tmp_path)
    worklog.new_entry("Primera", tarea="A01", now=datetime(2026, 10, 28, 10, 0))
    worklog.new_entry("Segunda", tarea="B02", now=datetime(2026, 10, 28, 11, 0))
    entries = worklog.recent(5)
    assert [e["tema"] for e in entries] == ["Segunda", "Primera"]
    assert entries[0]["tarea"] == "B02"
