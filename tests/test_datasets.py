"""Tests de datos y GT (T04) sin descargar nada: escenas sintéticas de disparidad conocida."""

import numpy as np
import pytest

from visionx.depth.datasets.audit import (
    SHIFTS_PX,
    alignment_curve,
    audit_sample,
    contact_sheet,
    dataset_verdict,
    subpixel_minimum,
    verdict,
)
from visionx.depth.datasets.manifest import file_entry, sha256_file, verify_files
from visionx.depth.datasets.pfm import read_pfm, write_pfm
from visionx.depth.datasets.sample import StereoSample
from visionx.depth.datasets.splits import check_no_leak, split_scenes
from visionx.shared.errors import InvalidInput
from visionx.shared.geometry import StereoGeometry

D_TRUE = 6  # píxeles


def synthetic_sample(d: float = D_TRUE, **kwargs) -> StereoSample:
    """Textura aleatoria; el ojo derecho ve cada punto D_TRUE px más a la izquierda."""
    rng = np.random.default_rng(0)
    h, w = 160, 240  # suficientes píxeles para que el ruido no decida la auditoría
    left = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    left = np.repeat(np.repeat(left[::2, ::2], 2, 0), 2, 1)  # manchas de 2 px: interpolable
    right = np.roll(left, -D_TRUE, axis=1)  # right[x - d] = left[x]
    valid = np.ones((h, w), bool)
    valid[:, :D_TRUE] = False  # esas columnas no tienen correspondencia en el ojo derecho
    disparity = np.where(valid, np.float32(d), np.nan).astype(np.float32)
    args = dict(dataset="sintetico", sample_id="s0", scene_id="escena0", left=left,
                right=right, disparity=disparity, valid=valid)  # fmt: skip
    args.update(kwargs)
    return StereoSample(**args)


# --- PFM -------------------------------------------------------------------------------


def test_pfm_roundtrip_keeps_row_order_and_inf(tmp_path):
    values = np.arange(12, dtype=np.float32).reshape(3, 4)
    values[0, 0] = np.inf  # Middlebury marca así los píxeles sin GT
    write_pfm(tmp_path / "d.pfm", values)
    back = read_pfm(tmp_path / "d.pfm")
    assert back.dtype == np.float32
    assert np.array_equal(back, values)  # fila 0 sigue arriba


def test_pfm_big_endian_and_truncated(tmp_path):
    values = np.array([[1.5, 2.5]], np.float32)
    path = tmp_path / "be.pfm"
    path.write_bytes(b"Pf\n2 1\n1.0\n" + values.astype(">f4").tobytes())
    assert np.array_equal(read_pfm(path), values)
    path.write_bytes(b"Pf\n2 2\n-1.0\n" + values.astype("<f4").tobytes())
    with pytest.raises(InvalidInput, match="truncado"):
        read_pfm(path)
    path.write_bytes(b"P6\n2 1\n255\n")
    with pytest.raises(InvalidInput, match="no es PFM"):
        read_pfm(path)


# --- Muestra -----------------------------------------------------------------------------


def test_sample_rejects_zero_as_missing_gt():
    s = synthetic_sample()
    bad = s.disparity.copy()
    bad[~s.valid] = 0.0  # un 0 fuera de valid parecería una medición
    with pytest.raises(InvalidInput, match="NaN"):
        synthetic_sample(disparity=bad)


def test_sample_checks_masks_and_geometry():
    s = synthetic_sample()
    with pytest.raises(InvalidInput, match="nonoccluded"):
        synthetic_sample(nonoccluded=~s.valid)
    with pytest.raises(InvalidInput, match="geometría"):
        synthetic_sample(geometry=StereoGeometry(100, 60, 500.0, 500.0, 50.0, 30.0, 0.1))
    with pytest.raises(InvalidInput, match="sin calibración"):
        s.depth()
    g = StereoGeometry(240, 160, 600.0, 600.0, 120.0, 80.0, 0.06)
    z, ok = synthetic_sample(geometry=g).depth()
    assert np.allclose(z[ok], 600.0 * 0.06 / D_TRUE)


# --- Auditoría fotométrica -----------------------------------------------------------------


def test_alignment_minimum_at_zero_for_correct_gt(tmp_path):
    s = synthetic_sample()
    errors, n = alignment_curve(s)
    assert n > 0
    # Sin corrimiento el census coincide salvo en el borde que np.roll mezcla.
    assert errors[len(errors) // 2] < 0.01 < min(errors[0], errors[-1])
    report = audit_sample(s)
    assert report["fotometrico"]["gt_alineada"] is True
    assert report["fotometrico"]["minimo_en_px"] == 0.0
    assert report["disparidad_px"]["p50"] == D_TRUE
    assert contact_sheet(s, tmp_path / "hoja.png").exists()


def test_alignment_ignores_exposure_change():
    """Ojo derecho más oscuro (como MotorcycleE): census no cambia, la GT sigue alineada."""
    s = synthetic_sample()
    darker = (s.right.astype(np.float32) * 0.6 + 10).astype(np.uint8)
    assert audit_sample(synthetic_sample(right=darker))["fotometrico"]["gt_alineada"] is True


@pytest.mark.parametrize("wrong", [D_TRUE * 100.0, -D_TRUE, D_TRUE / 2])
def test_audit_flags_badly_read_gt(wrong):
    """Escala x100 olvidada, signo invertido o escala mal: la prueba lo detecta."""
    report = audit_sample(synthetic_sample(d=wrong))
    assert report["fotometrico"]["gt_alineada"] is False
    # Un dataset entero leído así no pasa, aunque alguna muestra quedara «no concluyente».
    assert dataset_verdict([report] * 20)["ok"] is False


def test_audit_verdicts_and_subpixel_minimum():
    flat = [0.5] * len(SHIFTS_PX)  # pared lisa: corrimientos indistinguibles
    assert verdict(flat, 100_000) == "no concluyente"
    v = [abs(s - 0.25) + 0.1 for s in SHIFTS_PX]  # mínimo real en +0,25 px
    assert verdict(v, 100_000) == "alineada"  # el discreto cae en 0 o +0,5: un paso
    assert subpixel_minimum([(s - 0.25) ** 2 for s in SHIFTS_PX]) == pytest.approx(0.25)
    far = [abs(s - 2.0) + 0.1 for s in SHIFTS_PX]
    assert verdict(far, 100_000) == "desalineada"
    assert verdict(v, 5_000) == "no concluyente"  # pocos píxeles


def _report(veredicto, sub=0.0, muestra="m"):
    return {"muestra": muestra, "fotometrico": {"veredicto": veredicto, "minimo_subpx": sub}}


def test_dataset_verdict_rules():
    good = [_report("alineada", 0.1)] * 99
    assert dataset_verdict([*good, _report("no concluyente")])["ok"] is True  # 1 %
    assert dataset_verdict([*good[:90], *[_report("no concluyente")] * 10])["ok"] is False
    assert dataset_verdict([*good, _report("desalineada", 2.0, "x")])["desalineadas"] == ["x"]
    shifted = [_report("alineada", 0.4)] * 50  # todo corrido ~0,4 px: no es ruido
    assert dataset_verdict(shifted)["ok"] is False


# --- Particiones y manifiesto ----------------------------------------------------------------


def test_split_is_deterministic_and_stable():
    scenes = [f"s{i:02d}" for i in range(20)]
    rest, held = split_scenes(scenes * 3, 0.2, "visionx")  # pares repetidos por escena
    assert len(held) == 4 and len(rest) == 16
    assert split_scenes(reversed(scenes), 0.2, "visionx") == (rest, held)
    check_no_leak({"train": rest, "val": held})
    with pytest.raises(InvalidInput, match="fuga"):
        check_no_leak({"train": rest, "val": held + [rest[0]]})
    with pytest.raises(InvalidInput):
        split_scenes(["a"], 0.5, "x")


def test_manifest_detects_changed_files(tmp_path):
    f = tmp_path / "a" / "x.bin"
    f.parent.mkdir()
    f.write_bytes(b"hola")
    entry = file_entry(f, tmp_path)
    assert entry["ruta"] == "a/x.bin"
    assert entry["sha256"] == sha256_file(f)
    assert verify_files([entry], tmp_path) == []
    f.write_bytes(b"chau")
    assert verify_files([entry], tmp_path) == ["hash distinto: a/x.bin"]
    f.unlink()
    assert verify_files([entry], tmp_path) == ["falta a/x.bin"]


# --- Formato Middlebury / ETH3D --------------------------------------------------------------


def _write_middlebury(folder, sample, doffs=10.0, mask_override=None):
    """Escribe una muestra sintética como la publica Middlebury (baseline en mm)."""
    import cv2

    folder.mkdir(parents=True, exist_ok=True)
    w, h = sample.size
    cv2.imwrite(str(folder / "im0.png"), sample.left)
    cv2.imwrite(str(folder / "im1.png"), sample.right)
    write_pfm(folder / "disp0GT.pfm", np.where(sample.valid, sample.disparity - doffs, np.inf))
    mask = np.where(sample.valid, 255, 0).astype(np.uint8)
    mask[:, -10:][sample.valid[:, -10:]] = 128  # algunas ocluidas
    cv2.imwrite(str(folder / "mask0nocc.png"), mask if mask_override is None else mask_override)
    (folder / "calib.txt").write_text(
        f"cam0=[600 0 120; 0 600 80; 0 0 1]\ncam1=[600 0 {120 + doffs}; 0 600 80; 0 0 1]\n"
        f"doffs={doffs}\nbaseline=60.0\nwidth={w}\nheight={h}\nndisp=64\n",
        encoding="utf-8",
    )


def test_middlebury_folder_reads_units_masks_and_doffs(tmp_path):
    from visionx.depth.datasets.middlebury import load_folder

    src = synthetic_sample()
    _write_middlebury(tmp_path / "Escena", src)
    s = load_folder(tmp_path / "Escena", "mb", "Escena", "Escena", tmp_path)
    assert s.geometry.baseline_m == pytest.approx(0.060)  # mm -> m
    assert s.geometry.doffs == pytest.approx(10.0)
    assert np.array_equal(s.valid, src.valid)
    assert s.nonoccluded.sum() < s.valid.sum()  # las de 128 quedan como ocluidas
    z, ok = s.depth()  # d + doffs = D_TRUE: Z = 600 * 0.06 / 6
    assert np.allclose(z[ok], 6.0)
    assert s.files[0] == "Escena/im0.png"
    assert audit_sample(s)["fotometrico"]["gt_alineada"] is True


def test_middlebury_folder_rejects_inconsistent_files(tmp_path):
    from visionx.depth.datasets.middlebury import load_folder

    src = synthetic_sample()
    bad_mask = np.full(src.valid.shape, 255, np.uint8)  # dice "hay GT" donde el PFM tiene inf
    _write_middlebury(tmp_path / "A", src, mask_override=bad_mask)
    with pytest.raises(InvalidInput, match="no coinciden"):
        load_folder(tmp_path / "A", "mb", "A", "A", tmp_path)
    _write_middlebury(tmp_path / "B", src)
    calib = (tmp_path / "B" / "calib.txt").read_text().replace("doffs=10.0", "doffs=3.0")
    (tmp_path / "B" / "calib.txt").write_text(calib)
    with pytest.raises(InvalidInput, match="doffs"):
        load_folder(tmp_path / "B", "mb", "B", "B", tmp_path)


def test_catalog_groups_variants_into_scenes(tmp_path):
    from visionx.depth.datasets.catalog import CATALOG

    src = synthetic_sample()
    for name in ("Motorcycle", "MotorcycleE", "Teddy"):
        _write_middlebury(tmp_path / "mb" / "MiddEval3" / "trainingH" / name, src)
    scenes = {r.sample_id: r.scene_id for r in CATALOG["middeval3"].index(tmp_path / "mb")}
    assert scenes == {"Motorcycle": "Motorcycle", "MotorcycleE": "Motorcycle", "Teddy": "Teddy"}
    for name in ("electro_1l", "electro_1s", "forest_2s"):
        _write_middlebury(tmp_path / "eth" / name, src)
    scenes = {r.sample_id: r.scene_id for r in CATALOG["eth3d"].index(tmp_path / "eth")}
    assert scenes == {"electro_1l": "electro", "electro_1s": "electro", "forest_2s": "forest"}


# --- InStereo2K y CLI ------------------------------------------------------------------------


def _write_instereo2k(folder, sample, scale=100.0):
    import cv2

    folder.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(folder / "left.png"), sample.left)
    cv2.imwrite(str(folder / "right.png"), sample.right)
    raw = np.where(sample.valid, np.rint(np.nan_to_num(sample.disparity) * scale), 0)
    cv2.imwrite(str(folder / "left_disp.png"), raw.astype(np.uint16))
    cv2.imwrite(str(folder / "right_disp.png"), raw.astype(np.uint16))


def test_instereo2k_divides_by_100_and_partitions_by_block(tmp_path):
    from visionx.depth.datasets.catalog import CATALOG

    src = synthetic_sample()
    root = tmp_path / "raw"
    # Estructura real: train/part<N>/<cuadro>/ y test/<cuadro>/, cuadros numerados en común.
    for frame in (1, 2, 101, 102, 401):
        _write_instereo2k(root / "train" / f"part{(frame - 1) // 400 + 1}" / f"{frame:06d}", src)
    _write_instereo2k(root / "test" / "000040", src)
    info = CATALOG["instereo2k"]
    refs = info.index(root)
    assert [r.sample_id for r in refs] == ["000001", "000002", "000040", "000101", "000102",
                                           "000401"]  # fmt: skip
    scenes = {r.sample_id: r.scene_id for r in refs}
    assert scenes["000001"] == scenes["000040"] == "tramo-00"  # el test oficial sigue al tramo
    assert scenes["000401"] == "tramo-04"
    sample = refs[0].load()
    assert sample.geometry is None  # sin calibración publicada
    assert np.allclose(sample.disparity[sample.valid], D_TRUE)  # 600 / 100
    assert np.array_equal(sample.valid, src.valid)  # 0 = sin GT
    assert audit_sample(sample)["fotometrico"]["gt_alineada"] is True
    groups = info.partition(refs)
    # La semilla fija aparta tramo-00 y tramo-04 de los 21 tramos del dataset completo.
    assert groups == {"train": ["tramo-01"], "val": ["tramo-00", "tramo-04"]}
    assert info.partition(refs[:4]) == {"train": ["tramo-01"], "val": ["tramo-00"]}  # estable


def test_instereo2k_rejects_repeated_frames(tmp_path):
    from visionx.depth.datasets.catalog import CATALOG

    for part in ("part1", "part2"):
        _write_instereo2k(tmp_path / "train" / part / "000007", synthetic_sample())
    (tmp_path / "test").mkdir()
    with pytest.raises(InvalidInput, match="repetidos"):
        CATALOG["instereo2k"].index(tmp_path)


def test_cli_extracts_manual_archives_after_checking_hash(tmp_path, monkeypatch):
    import dataclasses
    import zipfile

    from visionx.depth.datasets import __main__ as cli
    from visionx.depth.datasets.catalog import CATALOG, Download

    data = tmp_path / "data"
    zpath = data / "descargas" / "instereo2k" / "part9.zip"
    zpath.parent.mkdir(parents=True)
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("part9/003001/left.png", b"x")
    item = Download("", sha256_file(zpath), zpath.stat().st_size, "part9.zip", "train")
    info = dataclasses.replace(CATALOG["instereo2k"], downloads=(item,))
    monkeypatch.setitem(cli.CATALOG, "instereo2k", info)
    assert cli.main(["descargar", "instereo2k", "--datos", str(data)]) == 0
    assert (data / "raw" / "instereo2k" / "train" / "part9" / "003001" / "left.png").exists()
    zpath.write_bytes(b"otro contenido")  # el zip cambió: no se extrae
    assert cli.main(["descargar", "instereo2k", "--datos", str(data)]) == 1


def test_instereo2k_wrong_scale_is_caught_by_audit(tmp_path):
    """Si la escala real fuera /1024 (como asume torchvision), leer /100 se detecta."""
    from visionx.depth.datasets.instereo2k import load_pair

    _write_instereo2k(tmp_path / "train" / "a", synthetic_sample(), scale=1024.0)
    sample = load_pair(tmp_path / "train" / "a", "a", "a", tmp_path)
    assert audit_sample(sample)["fotometrico"]["gt_alineada"] is False


def test_cli_audit_manifest_verify(tmp_path, capsys):
    from visionx.depth.datasets.__main__ import main

    src = synthetic_sample()
    for name in ("electro_1l", "forest_2s"):
        _write_middlebury(tmp_path / "data" / "raw" / "eth3d" / name, src)
    data, out, man = str(tmp_path / "data"), str(tmp_path / "out"), str(tmp_path / "man")
    assert main(["auditar", "eth3d", "--datos", data, "--salida", out, "--hojas", "1"]) == 0
    assert len(list((tmp_path / "out" / "eth3d").glob("*.png"))) == 1
    out0 = str(tmp_path / "out0")
    assert main(["auditar", "eth3d", "--datos", data, "--salida", out0, "--hojas", "0"]) == 0
    assert not list((tmp_path / "out0" / "eth3d").glob("*.png"))  # 0 hojas = ninguna
    assert main(["manifiesto", "eth3d", "--datos", data, "--manifiestos", man]) == 0
    assert main(["verificar", "eth3d", "--datos", data, "--manifiestos", man]) == 0
    (tmp_path / "data" / "raw" / "eth3d" / "forest_2s" / "im1.png").write_bytes(b"roto")
    assert main(["verificar", "eth3d", "--datos", data, "--manifiestos", man]) == 1
    assert main(["descargar", "instereo2k", "--datos", data]) == 1
    assert "a mano" in capsys.readouterr().err
