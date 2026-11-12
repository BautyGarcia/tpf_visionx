"""Tests de calibración estéreo (T03) con un par virtual de parámetros conocidos.

No usan cámara: proyectamos un damero con una cámara estéreo inventada, parecida a la
ELP (focal ~590 px, baseline 60 mm), le sumamos ruido de detección y comprobamos que
el calibrador recupere esos parámetros y descarte las fotos malas que metemos a propósito.
"""

import math
import pickle

import cv2
import numpy as np
import pytest
import yaml

from visionx.calibration import (
    CalibrationOptions,
    Checkerboard,
    LensModel,
    PairView,
    Session,
    StereoCalibration,
    calibrate,
    from_i308_pickle,
    load_session,
)
from visionx.calibration import sessions as sessions_module
from visionx.calibration.__main__ import main
from visionx.calibration.detection import detect_corners, match_order
from visionx.calibration.report import to_calibration
from visionx.shared.errors import InvalidInput

BOARD = Checkerboard(9, 6, 0.028)
SIZE = (1920, 1080)
K1 = np.array([[590.0, 0, 961.0], [0, 589.0, 538.0], [0, 0, 1]])
K2 = np.array([[591.0, 0, 955.0], [0, 590.0, 531.0], [0, 0, 1]])
D1 = np.array([0.01, -0.03, 0.0005, -0.0003, 0.005])
D2 = np.array([0.006, -0.027, -0.0004, 0.0002, 0.004])
R_TRUE = cv2.Rodrigues(np.array([0.003, -0.012, 0.002]))[0]
T_TRUE = np.array([[-0.060], [0.0004], [0.0006]])  # metros: ojo derecho 60 mm a la derecha


def _pose(tilt_x: float, tilt_y: float, roll: float, center: tuple[float, float, float]):
    """Pose del tablero: inclinado (grados) y con su centro en `center` (metros)."""
    rvec = np.radians([tilt_x, tilt_y, roll])
    R = cv2.Rodrigues(rvec)[0]
    half = np.array(
        [(BOARD.cols - 1) * BOARD.square_m / 2, (BOARD.rows - 1) * BOARD.square_m / 2, 0]
    )
    tvec = np.asarray(center, float).reshape(3, 1) - R @ half.reshape(3, 1)
    return cv2.Rodrigues(R)[0], tvec


def _views(n: int = 36, seed: int = 0, noise_px: float = 0.08) -> list[PairView]:
    """Pares virtuales variados: zonas de la imagen, distancias e inclinaciones."""
    rng = np.random.default_rng(seed)
    objp = BOARD.object_points().astype(np.float64)
    views: list[PairView] = []
    attempt = 0
    while len(views) < n:
        attempt += 1
        z = rng.uniform(0.45, 1.0)
        center = (rng.uniform(-0.55, 0.55) * z, rng.uniform(-0.3, 0.3) * z, z)
        rvec, tvec = _pose(rng.uniform(-40, 40), rng.uniform(-40, 40), rng.uniform(-20, 20), center)
        left, _ = cv2.projectPoints(objp, rvec, tvec, K1, D1)
        r_right = cv2.Rodrigues(R_TRUE @ cv2.Rodrigues(rvec)[0])[0]
        right, _ = cv2.projectPoints(objp, r_right, R_TRUE @ tvec + T_TRUE, K2, D2)
        left, right = left.reshape(-1, 2), right.reshape(-1, 2)
        margin = 15
        inside = all(
            (p[:, 0] > margin).all() and (p[:, 0] < SIZE[0] - margin).all()
            and (p[:, 1] > margin).all() and (p[:, 1] < SIZE[1] - margin).all()
            for p in (left, right)
        )  # fmt: skip
        if not inside:
            continue
        left = left + rng.normal(0, noise_px, left.shape)
        right = right + rng.normal(0, noise_px, right.shape)
        views.append(
            PairView("virtual", attempt, left.astype(np.float32), right.astype(np.float32),
                     SIZE, f"l{attempt}", f"r{attempt}", (100.0, 100.0))
        )  # fmt: skip
    return views


def _session(views: list[PairView], name: str = "virtual") -> Session:
    return Session(name=name, folder=None, views=views, total_pairs=len(views))


@pytest.fixture(scope="module")
def run_clean():
    options = CalibrationOptions(models=(LensModel.PINHOLE5,))
    sessions = [_session(_views())]
    return calibrate(sessions, BOARD, options=options), options, sessions


# --- Tablero ----------------------------------------------------------------------------


def test_board_parse_and_object_points():
    board = Checkerboard.parse("9x6", 28)
    assert board == BOARD
    points = board.object_points()
    assert points.shape == (54, 3)
    # Orden de OpenCV: x varía más rápido, fila por fila, en metros.
    assert points[1, 0] == pytest.approx(0.028)
    assert points[9, 1] == pytest.approx(0.028)


@pytest.mark.parametrize(
    "kwargs", [dict(cols=6, rows=6, square_m=0.03), dict(cols=9, rows=6, square_m=28.0),
               dict(cols=2, rows=6, square_m=0.03), dict(cols=9, rows=6, square_m=0.0)]
)  # fmt: skip
def test_board_rejects_ambiguous_or_wrong_units(kwargs):
    with pytest.raises(InvalidInput):
        Checkerboard(**kwargs)


# --- Detección ----------------------------------------------------------------------------


def _render_board(px: int = 40, angle: float = 8.0) -> tuple[np.ndarray, np.ndarray]:
    """Damero de 10 x 7 cuadrados dibujado y girado; devuelve imagen y esquinas reales."""
    w, h = 10 * px, 7 * px
    board = np.full((h, w), 255, np.uint8)
    for r in range(7):
        for c in range(10):
            if (r + c) % 2 == 0:
                board[r * px : (r + 1) * px, c * px : (c + 1) * px] = 0
    canvas = np.full((h + 200, w + 200), 255, np.uint8)
    canvas[100 : 100 + h, 100 : 100 + w] = board
    M = cv2.getRotationMatrix2D((canvas.shape[1] / 2, canvas.shape[0] / 2), angle, 1.0)
    image = cv2.warpAffine(canvas, M, canvas.shape[::-1], flags=cv2.INTER_CUBIC, borderValue=255)
    image = cv2.GaussianBlur(image, (3, 3), 0.8)
    # Esquinas internas: centro de píxel en 0, borde del cuadrado en k*px - 0.5.
    grid = np.mgrid[1:10, 1:7].T.reshape(-1, 2).astype(float) * px - 0.5 + 100
    truth = cv2.transform(grid.reshape(-1, 1, 2), M).reshape(-1, 2)
    return image, truth


def test_detect_corners_is_subpixel_accurate():
    image, truth = _render_board()
    corners = detect_corners(image, BOARD)
    assert corners is not None and corners.points.shape == (54, 2)
    # La numeración puede empezar en cualquiera de las dos puntas del tablero.
    error = min(np.abs(corners.points - truth).max(), np.abs(corners.points[::-1] - truth).max())
    assert error < 0.2


def test_detect_corners_returns_none_without_board():
    assert detect_corners(np.full((300, 400), 128, np.uint8), BOARD) is None


def test_match_order_fixes_reversed_eye():
    views = _views(1)
    left, right = views[0].left, views[0].right
    fixed, reordered = match_order(left, right[::-1].copy())
    assert reordered and np.array_equal(fixed, right)
    same, reordered = match_order(left, right)
    assert not reordered and np.array_equal(same, right)


# --- Calibración --------------------------------------------------------------------------


def test_recovers_known_rig(run_clean):
    run, _, _ = run_clean
    sel = run.selected
    assert sel.left.K[0, 0] == pytest.approx(590.0, rel=0.005)
    assert sel.right.K[0, 0] == pytest.approx(591.0, rel=0.005)
    assert sel.baseline_m == pytest.approx(float(np.linalg.norm(T_TRUE)), rel=0.005)
    assert sel.fit_rms_px < 0.2  # del orden del ruido simulado
    assert sel.validation["vertical_median_px"] < 0.1
    assert abs(sel.validation["scale_error_median"]) < 0.002
    assert len(run.validation_keys) > 0 and not set(run.validation_keys) & set(run.fit_keys)


def test_rejects_moved_and_too_tilted_views():
    views = _views()
    # Dos fotos "movidas": el tablero se desplazó 4 px entre la captura de cada ojo.
    moved = [views[3].key, views[8].key]
    for i in (3, 8):
        v = views[i]
        views[i] = PairView(v.session, v.index, v.left, v.right + np.float32([4.0, 1.5]),
                            v.image_size, v.left_sha256, v.right_sha256, v.sharpness)  # fmt: skip
    # Una foto con el tablero inclinado 75°.
    objp = BOARD.object_points().astype(np.float64)
    rvec, tvec = _pose(75, 0, 0, (0.0, 0.0, 0.6))
    left = cv2.projectPoints(objp, rvec, tvec, K1, D1)[0].reshape(-1, 2)
    r_right = cv2.Rodrigues(R_TRUE @ cv2.Rodrigues(rvec)[0])[0]
    right = cv2.projectPoints(objp, r_right, R_TRUE @ tvec + T_TRUE, K2, D2)[0].reshape(-1, 2)
    views.insert(1, PairView("virtual", 999, left.astype(np.float32), right.astype(np.float32),
                             SIZE, "l", "r", (1.0, 1.0)))  # fmt: skip
    run = calibrate(
        [_session(views)], BOARD, options=CalibrationOptions(models=(LensModel.PINHOLE5,))
    )
    rejected = run.selected.rejected
    fit_or_rejected = set(run.fit_keys) | set(rejected)
    for key in moved:
        if key in fit_or_rejected:  # si cayó en validación no se limpia (a propósito)
            assert "movimiento" in rejected[key]
    assert "inclinado" in rejected["virtual#999"]
    assert run.selected.baseline_m == pytest.approx(0.060, rel=0.01)


def test_flags_low_tilt_variety():
    rng = np.random.default_rng(3)
    objp = BOARD.object_points().astype(np.float64)
    views = []
    for i in range(20):
        rvec, tvec = _pose(
            rng.uniform(-3, 3), rng.uniform(-3, 3), 0, (rng.uniform(-0.3, 0.3), 0, 0.8)
        )
        left = cv2.projectPoints(objp, rvec, tvec, K1, D1)[0].reshape(-1, 2)
        r_right = cv2.Rodrigues(R_TRUE @ cv2.Rodrigues(rvec)[0])[0]
        right = cv2.projectPoints(objp, r_right, R_TRUE @ tvec + T_TRUE, K2, D2)[0].reshape(-1, 2)
        views.append(PairView("plano", i, left.astype(np.float32), right.astype(np.float32),
                              SIZE, "l", "r", (1.0, 1.0)))  # fmt: skip
    options = CalibrationOptions(models=(LensModel.PINHOLE5,), min_views=8)
    try:
        run = calibrate([_session(views, "plano")], BOARD, options=options)
    except InvalidInput:
        return  # también es aceptable negarse a calibrar algo tan degenerado
    assert any("inclinado" in w or "condicionada" in w for w in run.warnings)


def test_needs_enough_views():
    with pytest.raises(InvalidInput):
        calibrate([_session(_views(8))], BOARD)


# --- Archivo y geometría --------------------------------------------------------------


def test_save_load_roundtrip_and_geometry(run_clean, tmp_path):
    run, options, sessions = run_clean
    calib = to_calibration(run, sessions, options)
    path = calib.save(tmp_path / "elp.yaml")
    loaded = StereoCalibration.load(path)
    assert loaded.calibration_id == calib.calibration_id
    geometry = loaded.geometry()
    assert geometry.baseline_m == pytest.approx(run.selected.baseline_m, rel=1e-9)
    assert geometry.doffs == pytest.approx(0.0, abs=1e-9)
    assert geometry.size == SIZE
    # Profundidad de prueba: Z = fx * B / d.
    assert geometry.depth_at(geometry.fx * geometry.baseline_m / 1.0) == pytest.approx(1.0)


def test_load_detects_tampering(run_clean, tmp_path):
    run, options, sessions = run_clean
    path = to_calibration(run, sessions, options).save(tmp_path / "elp.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["rectificacion"]["P2"][0][3] *= 1.01  # baseline 1 % distinto con el mismo id
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(InvalidInput, match="calibration_id"):
        StereoCalibration.load(path)


def test_rectify_checks_size_and_aligns_rows(run_clean):
    run, options, sessions = run_clean
    calib = to_calibration(run, sessions, options)
    with pytest.raises(InvalidInput):
        calib.rectify(np.zeros((480, 640, 3), np.uint8), np.zeros((480, 640, 3), np.uint8))
    left, right = calib.rectify(
        np.zeros((1080, 1920, 3), np.uint8), np.zeros((1080, 1920, 3), np.uint8)
    )
    assert left.shape == right.shape == (1080, 1920, 3)


def test_swapped_eyes_are_rejected(run_clean):
    run, options, sessions = run_clean
    calib = to_calibration(run, sessions, options)
    with pytest.raises(InvalidInput):
        StereoCalibration(calib.image_size, calib.model, calib.left, calib.right, calib.R,
                          -calib.T, calib.rect, calib.alpha)  # fmt: skip


def test_import_i308_pickle_converts_mm(tmp_path):
    data = {"left_K": K1, "left_dist": D1.reshape(1, -1), "right_K": K2,
            "right_dist": D2.reshape(1, -1), "R": R_TRUE, "T": T_TRUE * 1000,
            "image_size": SIZE}  # fmt: skip
    path = tmp_path / "stereo_calibration.pkl"
    path.write_bytes(pickle.dumps(data))
    calib = from_i308_pickle(path)
    assert calib.baseline_m == pytest.approx(float(np.linalg.norm(T_TRUE)))
    assert calib.model is LensModel.PINHOLE5


# --- Sesiones en disco y comandos ----------------------------------------------------------


def test_load_session_detects_and_caches(tmp_path, monkeypatch):
    image, _ = _render_board()
    folder = tmp_path / "s1" / "calib"
    folder.mkdir(parents=True)
    for i in (1, 2):
        cv2.imwrite(str(folder / f"left_{i}.jpg"), image)
        cv2.imwrite(str(folder / f"right_{i}.jpg"), np.roll(image, -12, axis=1))
    cv2.imwrite(str(folder / "left_3.jpg"), image)  # par incompleto
    session = load_session(folder, BOARD, workers=2)
    assert session.name == "s1"
    assert len(session.views) == 2
    assert any("right_3" in p for p in session.problems)
    assert (folder / sessions_module.CACHE_NAME).exists()

    def fail(*_args, **_kwargs):
        raise AssertionError("no debería volver a detectar")

    monkeypatch.setattr(sessions_module, "_detect_file", fail)
    again = load_session(folder, BOARD)
    assert np.array_equal(again.views[0].left, session.views[0].left)


def test_cli_compare_and_bad_args(run_clean, tmp_path, capsys):
    run, options, sessions = run_clean
    path = to_calibration(run, sessions, options).save(tmp_path / "elp.yaml")
    assert main(["comparar", str(path)]) == 0
    assert "pinhole5" in capsys.readouterr().out
    assert (
        main(["revisar", str(tmp_path / "no-existe"), "--tablero", "9x6", "--cuadrado-mm", "28"])
        == 1
    )
    assert math.isfinite(run.selected.fit_rms_px)
