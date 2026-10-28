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


def test_tasks_in_progress_reads_people_and_integrations(tmp_path, monkeypatch):
    monkeypatch.setattr(worklog, "ROOT", tmp_path)
    folder = tmp_path / "docs" / "coordinacion"
    folder.mkdir(parents=True)
    fixtures = {
        "TAREAS.md": "- [ ] C03 · estado: en curso · rama: b/C03-plan\n",
        "A.md": "- [ ] A05 · estado: por integrar · rama: a/A05-fake\n",
        "B.md": "- [ ] B02 · estado: bloqueada · rama: b/B02-replay\n",
        "INTEGRACIONES.md": "- [ ] I00 · estado: en curso · coordinador: B\n",
    }
    for name, text in fixtures.items():
        (folder / name).write_text(text, encoding="utf-8")
    tasks = worklog.tasks_in_progress()
    assert len(tasks) == 4
    assert any("A05" in task for task in tasks)
    assert any("B02" in task for task in tasks)
    assert any("I00" in task for task in tasks)


def test_tasks_in_progress_ignores_closed_and_preserves_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(worklog, "ROOT", tmp_path)
    folder = tmp_path / "docs" / "coordinacion"
    folder.mkdir(parents=True)
    (folder / "TAREAS.md").write_text(
        "- [pendiente] A01 · antigua\n"
        "- [en revisión] C02 · antigua\n"
        "- [ ] B01 · estado: pendiente · rama: —\n"
        "- [x] B02 · estado: hecha · rama: —\n"
        "- [x] B03 · estado: en curso · rama: —\n",
        encoding="utf-8",
    )
    tasks = worklog.tasks_in_progress()
    assert len(tasks) == 1
    assert "C02" in tasks[0]
