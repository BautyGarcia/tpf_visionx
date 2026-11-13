"""Tests de captura, grabación y replay (T02) sin cámara.

Una cámara falsa entrega cuadros SBS donde cada ojo lleva escrito su número de cuadro y su
lado. Así se puede comprobar que los ojos no se cruzan, que el replay devuelve exactamente
lo grabado y que los fallos de dispositivo o de archivo no se confunden con "fin de video".
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np
import pytest
import yaml

from visionx.calibration import StereoCalibration
from visionx.camera import (
    CameraSettings,
    ImageFormat,
    Recorder,
    RectifiedSource,
    ReplaySource,
    UsbStereoSource,
    load_recording,
    split_sbs,
    timing_summary,
)
from visionx.camera.__main__ import main as camera_main
from visionx.shared.clock import ManualClock
from visionx.shared.config import ROOT, load_config
from visionx.shared.contracts import StereoFrame
from visionx.shared.errors import IdentityMismatch, InvalidInput, SourceError
from visionx.shared.interfaces import FrameSource

EYE = (64, 48)  # (ancho, alto) chico para que los tests sean rápidos


def sbs_image(n: int, eye: tuple[int, int] = EYE) -> np.ndarray:
    """Cuadro SBS sintético: ojo izquierdo con valor n en el canal 0 y 10 en el 2;
    ojo derecho con n en el canal 0 y 200 en el 2. Un poco de textura para JPEG."""
    w, h = eye
    image = np.zeros((h, 2 * w, 3), np.uint8)
    image[:, :w, 0] = n % 256
    image[:, :w, 2] = 10
    image[:, w:, 0] = n % 256
    image[:, w:, 2] = 200
    image[::8, :, 1] = 255
    return image


class FakeCapture:
    """Imita cv2.VideoCapture. `fail_at` = cuadros (por número de lectura) que fallan."""

    def __init__(self, eye=EYE, *, opened=True, fail_at=(), start=0):
        self.eye = eye
        self.opened = opened
        self.fail_at = set(fail_at)
        self.reads = start
        self.released = False

    def isOpened(self):  # noqa: N802
        return self.opened

    def read(self):
        n = self.reads
        self.reads += 1
        if n in self.fail_at:
            return False, None
        return True, sbs_image(n, self.eye)

    def release(self):
        self.released = True


def settings(**kw) -> CameraSettings:
    base = {"capture_size": (2 * EYE[0], EYE[1]), "warmup_frames": 0, "reconnect_wait_s": 0.0}
    base.update(kw)
    return CameraSettings(**base)


def live_source(caps, **kw) -> UsbStereoSource:
    """Fuente USB que abre, en orden, las cámaras falsas de `caps`."""
    pending = list(caps)
    return UsbStereoSource(
        settings(**kw.pop("settings", {})),
        session_id="s-test",
        clock=kw.pop("clock", ManualClock(1_000)),
        open_fn=lambda _s: pending.pop(0),
        sleep=lambda _t: None,
    )


def frame(i: int, t_ns: int, session="s-test", eye=EYE) -> StereoFrame:
    left, right = split_sbs(sbs_image(i, eye))
    return StereoFrame(session, i, left, right, received_ns=t_ns)


def record(folder: Path, frames, **kw) -> dict:
    with Recorder(folder, **kw) as rec:
        for f in frames:
            rec.write(f)
    return yaml.safe_load((folder / "manifest.yaml").read_text(encoding="utf-8"))


# --- SBS ---------------------------------------------------------------------------------


def test_split_sbs_separa_y_puede_invertir():
    img = sbs_image(7)
    left, right = split_sbs(img)
    assert left.shape == right.shape == (EYE[1], EYE[0], 3)
    assert left[0, 0, 2] == 10 and right[0, 0, 2] == 200
    left, right = split_sbs(img, swap_eyes=True)
    assert left[0, 0, 2] == 200 and right[0, 0, 2] == 10


@pytest.mark.parametrize(
    "bad",
    [
        np.zeros((4, 7, 3), np.uint8),  # ancho impar
        np.zeros((4, 8, 3), np.float32),  # dtype
        np.zeros((4, 8), np.uint8),  # sin canales
        np.zeros((0, 8, 3), np.uint8),  # vacío
    ],
)
def test_split_sbs_rechaza_cuadros_invalidos(bad):
    with pytest.raises(InvalidInput):
        split_sbs(bad)


# --- Configuración -------------------------------------------------------------------------


def test_settings_desde_la_config_por_defecto():
    s = CameraSettings.from_config(load_config())
    assert s.capture_size == (3840, 1080)
    assert s.eye_size == (1920, 1080)
    assert s.fourcc == "MJPG" and s.swap_eyes is False
    assert "calibration" in s.extra


@pytest.mark.parametrize(
    "kw",
    [{"backend": "inventado"}, {"capture_size": (101, 10)}, {"fourcc": "MJ"}],
)
def test_settings_invalidos(kw):
    with pytest.raises(InvalidInput):
        settings(**kw)


# --- Fuente USB ----------------------------------------------------------------------------


def test_usb_entrega_pares_con_identidad_y_reloj():
    clock = ManualClock(5_000)
    src = live_source([FakeCapture()], clock=clock)
    assert isinstance(src, FrameSource)
    a = src.read()
    clock.advance(16_000_000)
    b = src.read()
    assert (a.session_id, a.frame_id, b.frame_id) == ("s-test", 0, 1)
    assert a.received_ns == 5_000 and b.received_ns == 5_000 + 16_000_000
    assert not a.rectified and a.replay_original_ns is None and a.source_id == "elp"
    # el izquierdo es la mitad izquierda del SBS (canal 2 = 10)
    assert a.left[0, 0, 2] == 10 and a.right[0, 0, 2] == 200
    # el primer cuadro leído al abrir se usó para verificar el tamaño: b es el cuadro 2
    assert int(b.left[0, 0, 0]) == 2


def test_usb_descarta_cuadros_de_arranque():
    src = live_source([FakeCapture()], settings={"warmup_frames": 3})
    assert int(src.read().left[0, 0, 0]) == 4


def test_usb_no_abre_es_source_error():
    cap = FakeCapture(opened=False)
    with pytest.raises(SourceError, match="no se pudo abrir"):
        live_source([cap])
    assert cap.released


def test_usb_modo_distinto_al_pedido_es_source_error():
    # La ELP entrega otro modo sin avisar si el pedido no existe.
    cap = FakeCapture(eye=(32, 24))
    with pytest.raises(SourceError, match="en vez de"):
        live_source([cap])
    assert cap.released


def test_usb_reconecta_y_sigue_la_numeracion():
    first = FakeCapture(fail_at={2})  # lectura 0 al abrir, 1 ok, 2 falla
    second = FakeCapture(start=100)
    src = live_source([first, second])
    assert src.read().frame_id == 0
    after = src.read()  # falla, reconecta y entrega el cuadro de la cámara nueva
    assert after.frame_id == 1
    assert int(after.left[0, 0, 0]) == 101
    assert first.released
    assert (src.stats.read_failures, src.stats.reconnects) == (1, 1)


def test_usb_falla_persistente_es_source_error():
    caps = [FakeCapture(fail_at={1})] + [FakeCapture(opened=False) for _ in range(3)]
    src = live_source(caps, settings={"reconnect_attempts": 3})
    with pytest.raises(SourceError, match="no volvió"):
        src.read()
    with pytest.raises(SourceError, match="cerrada"):
        src.read()


# --- Grabación y replay ----------------------------------------------------------------------


def test_png_ida_y_vuelta_exacta(tmp_path):
    folder = tmp_path / "rec"
    frames = [frame(i, 1_000_000 + i * 16_666_667) for i in range(5)]
    manifest = record(folder, frames, image_format=ImageFormat("png"))
    assert manifest["estado"] == "cerrada" and manifest["pares"] == 5
    assert manifest["ojo"] == list(EYE) and manifest["session_id"] == "s-test"
    assert manifest["tiempos"]["fps_efectivo"] == pytest.approx(60.0, rel=1e-3)

    src = ReplaySource(folder, clock=ManualClock(0))
    assert isinstance(src, FrameSource) and len(src) == 5
    for original in frames:
        got = src.read()
        assert got.key == original.key
        assert got.replay_original_ns == original.received_ns
        assert got.is_replay and not got.rectified
        np.testing.assert_array_equal(got.left, original.left)
        np.testing.assert_array_equal(got.right, original.right)
    assert src.read() is None
    assert src.read() is None  # el fin es estable


def test_jpg_conserva_tamano_y_contenido_aproximado(tmp_path):
    # Degradé suave, más parecido a una escena que las rayas saturadas de sbs_image.
    w, h = EYE
    ramp = np.linspace(0, 200, w, dtype=np.float32)[None, :, None].repeat(h, 0).repeat(3, 2)
    left = ramp.astype(np.uint8)
    right = (ramp + 40).astype(np.uint8)
    original = StereoFrame("s-test", 0, left, right, received_ns=10)
    folder = tmp_path / "rec"
    record(folder, [original])
    got = ReplaySource(folder).read()
    assert got.left.shape == original.left.shape
    for a, b in ((got.left, left), (got.right, right)):
        assert np.abs(a.astype(int) - b.astype(int)).mean() < 2  # JPEG 95: pocos niveles
    assert got.right.mean() > got.left.mean() + 30  # los ojos no se cruzaron


def test_replay_con_manual_clock_respeta_los_intervalos_grabados(tmp_path):
    folder = tmp_path / "rec"
    times = [5_000_000_000, 5_033_000_000, 5_100_000_000]
    record(folder, [frame(i, t) for i, t in enumerate(times)])
    clock = ManualClock(42)
    src = ReplaySource(folder, clock=clock)
    received = [src.read().received_ns for _ in times]
    assert received == [42, 42 + 33_000_000, 42 + 100_000_000]


def test_replay_realtime_espera_entre_pares(tmp_path):
    folder = tmp_path / "rec"
    record(folder, [frame(0, 0), frame(1, 50_000_000)])
    waits = []
    src = ReplaySource(folder, realtime=True, sleep=waits.append)
    src.read()
    src.read()
    assert waits and 0 < waits[-1] <= 0.05


def test_hash_alterado_es_source_error(tmp_path):
    folder = tmp_path / "rec"
    record(folder, [frame(0, 0), frame(1, 1)])
    target = folder / "frames" / "000001_R.jpg"
    target.write_bytes(target.read_bytes()[:-10])
    src = ReplaySource(folder)
    src.read()
    with pytest.raises(SourceError, match="SHA-256"):
        src.read()


def test_archivo_faltante_es_source_error(tmp_path):
    folder = tmp_path / "rec"
    record(folder, [frame(0, 0)])
    (folder / "frames" / "000000_L.jpg").unlink()
    with pytest.raises(SourceError, match="falta"):
        ReplaySource(folder).read()


def test_linea_final_a_medio_escribir_se_ignora(tmp_path):
    folder = tmp_path / "rec"
    record(folder, [frame(0, 0), frame(1, 1)])
    with open(folder / "frames.jsonl", "a", encoding="utf-8") as f:
        f.write('{"frame_id": 2, "received_')  # corte de luz a mitad de línea
    src = ReplaySource(folder)
    assert src.truncated and len(src) == 2


def test_linea_rota_en_el_medio_es_error(tmp_path):
    folder = tmp_path / "rec"
    record(folder, [frame(0, 0)])
    index = folder / "frames.jsonl"
    index.write_text("{roto}\n" + index.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(SourceError, match="ilegible"):
        ReplaySource(folder)


def test_imagenes_sin_linea_no_cuentan(tmp_path):
    # Si se corta después de escribir las imágenes y antes de la línea, el par no existe.
    folder = tmp_path / "rec"
    record(folder, [frame(0, 0)])
    (folder / "frames" / "000001_L.jpg").write_bytes(b"x")
    assert len(ReplaySource(folder)) == 1


def test_no_es_una_grabacion(tmp_path):
    with pytest.raises(SourceError, match="no es una grabación"):
        ReplaySource(tmp_path)
    (tmp_path / "manifest.yaml").write_text("formato: otro\n", encoding="utf-8")
    with pytest.raises(SourceError, match="formato"):
        load_recording(tmp_path)


def test_grabacion_vacia_termina_enseguida(tmp_path):
    folder = tmp_path / "rec"
    record(folder, [])
    assert ReplaySource(folder).read() is None


def test_recorder_no_sobrescribe(tmp_path):
    folder = tmp_path / "rec"
    record(folder, [frame(0, 0)])
    with pytest.raises(InvalidInput, match="no se sobrescribe"):
        Recorder(folder)


def test_recorder_rechaza_mezclar_sesiones_tamanos_o_retroceder(tmp_path):
    with Recorder(tmp_path / "a") as rec:
        rec.write(frame(0, 0))
        with pytest.raises(IdentityMismatch):
            rec.write(frame(1, 1, session="otra"))
        with pytest.raises(IdentityMismatch):
            rec.write(frame(2, 2, eye=(32, 24)))
        with pytest.raises(InvalidInput, match="no avanza"):
            rec.write(frame(0, 3))


def test_recorder_con_cola_descarta_y_lo_registra(tmp_path):
    gate = threading.Event()
    started = threading.Event()

    def slow_encode(image):
        started.set()
        gate.wait(5)
        return ImageFormat("png").encode(image)

    folder = tmp_path / "rec"
    rec = Recorder(folder, image_format=ImageFormat("png"), queue_size=1, encode=slow_encode)
    assert rec.write(frame(0, 0))  # el hilo lo toma y queda trabado en slow_encode
    started.wait(5)
    assert rec.write(frame(1, 1))  # ocupa el único lugar de la cola
    assert not rec.write(frame(2, 2))  # cola llena: se descarta y se informa
    gate.set()
    manifest = rec.close()
    assert manifest["pares"] == 2
    assert manifest["descartados"] == {"cantidad": 1, "frame_ids": [2]}
    ids = [json.loads(line)["frame_id"] for line in (folder / "frames.jsonl").open()]
    assert ids == [0, 1]
    # el replay deja ver el hueco: la identidad original se conserva
    src = ReplaySource(folder)
    assert [src.read().frame_id, src.read().frame_id] == [0, 1]


def test_grabar_desde_la_fuente_usb_y_reproducir(tmp_path):
    src = live_source([FakeCapture()])
    folder = tmp_path / "rec"
    with Recorder(folder, image_format=ImageFormat("png")) as rec:
        live = [src.read() for _ in range(3)]
        for f in live:
            rec.write(f)
    replay = ReplaySource(folder)
    for f in live:
        got = replay.read()
        assert got.key == f.key and got.source_id == "elp"
        np.testing.assert_array_equal(got.left, f.left)


def test_timing_summary_detecta_huecos():
    t = [0, 16, 33, 50, 100, 116]  # ms; 50 -> 100 es un hueco
    s = timing_summary([x * 1_000_000 for x in t])
    assert s["huecos"] == 1 and s["intervalo_max_ms"] == 50
    assert timing_summary([1]) == {"pares": 1}


# --- Rectificación ---------------------------------------------------------------------------

CALIB = ROOT / "configs" / "calib" / "elp-2026-11-11-corregida.yaml"


class ListSource:
    def __init__(self, frames):
        self.frames = list(frames)
        self.closed = False

    def read(self):
        return self.frames.pop(0) if self.frames else None

    def close(self):
        self.closed = True


def test_rectified_source_marca_calibracion_y_geometria():
    calib = StereoCalibration.load(CALIB)
    w, h = calib.image_size
    rng = np.random.default_rng(0)
    raw = StereoFrame(
        "s",
        0,
        rng.integers(0, 255, (h, w, 3), dtype=np.uint8),
        rng.integers(0, 255, (h, w, 3), dtype=np.uint8),
        received_ns=1,
    )
    inner = ListSource([raw])
    src = RectifiedSource(inner, calib)
    out = src.read()
    assert out.rectified and out.calibration_id == calib.calibration_id
    assert out.geometry_id == src.geometry.geometry_id == calib.geometry().geometry_id
    assert out.key == raw.key and out.size == raw.size
    assert not np.array_equal(out.left, raw.left)  # se remapeó
    assert src.read() is None
    src.close()
    assert inner.closed


def test_rectified_source_rechaza_otro_modo():
    calib = StereoCalibration.load(CALIB)
    src = RectifiedSource(ListSource([frame(0, 0)]), calib)
    with pytest.raises(InvalidInput, match="no corresponde a este modo"):
        src.read()


# --- CLI -----------------------------------------------------------------------------------


def test_cli_verificar(tmp_path, capsys):
    folder = tmp_path / "rec"
    record(folder, [frame(0, 0), frame(1, 16_000_000)])
    assert camera_main(["verificar", str(folder)]) == 0
    out = capsys.readouterr().out
    assert "2 de 2" in out
    (folder / "frames" / "000000_L.jpg").write_bytes(b"roto")
    assert camera_main(["verificar", str(folder)]) == 1
