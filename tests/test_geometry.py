"""Tests de geometría (M0): ida y vuelta d <-> Z, resize, recorte, doffs y máscaras."""

import math

import numpy as np
import pytest

from visionx.shared.errors import IdentityMismatch, InvalidInput
from visionx.shared.geometry import StereoGeometry, resize_disparity, resize_mask

# Parecida a la ELP a 1080p: focal ~1000 px, baseline ~6 cm, centros alineados.
ELP = StereoGeometry(1920, 1080, 1000.0, 1000.0, 959.5, 539.5, 0.06)
# Con doffs distinto de 0, como Middlebury.
MB = StereoGeometry(1500, 1000, 3000.0, 3000.0, 700.0, 500.0, 0.17, doffs=120.0)


def project(g: StereoGeometry, x: float, y: float, z: float) -> tuple[float, float, float]:
    """Proyecta un punto 3D (cámara izquierda) a (u_izq, v, u_der) con el modelo pinhole."""
    u_left = g.fx * x / z + g.cx
    v = g.fy * y / z + g.cy
    u_right = g.fx * (x - g.baseline_m) / z + (g.cx + g.doffs)
    return u_left, v, u_right


# --- Construcción -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "kw",
    [
        dict(width=0),
        dict(height=-5),
        dict(width=1920.0),
        dict(fx=0.0),
        dict(fy=-1.0),
        dict(fx=float("nan")),
        dict(cx=5000.0),  # centro fuera de la imagen
        dict(cy=-10.0),
        dict(baseline_m=0.0),
        dict(baseline_m=-0.06),
        dict(doffs=float("inf")),
    ],
)
def test_geometry_rejects_bad_parameters(kw):
    base = dict(width=1920, height=1080, fx=1000.0, fy=1000.0, cx=959.5, cy=539.5, baseline_m=0.06)
    base.update(kw)
    with pytest.raises(InvalidInput):
        StereoGeometry(**base)


def test_geometry_id_is_deterministic_and_changes_with_parameters():
    same = StereoGeometry(1920, 1080, 1000.0, 1000.0, 959.5, 539.5, 0.06)
    assert same.geometry_id == ELP.geometry_id
    assert ELP.geometry_id.startswith("1920x1080-")
    other = StereoGeometry(1920, 1080, 1000.0, 1000.0, 959.5, 539.5, 0.061)
    assert other.geometry_id != ELP.geometry_id
    assert ELP.resized(1280, 720).geometry_id != ELP.geometry_id


def test_from_projections_matches_opencv_layout():
    fx, cx_l, cx_r, cy, b = 1000.0, 950.0, 960.0, 540.0, 0.06
    p1 = np.array([[fx, 0, cx_l, 0], [0, fx, cy, 0], [0, 0, 1, 0]])
    p2 = np.array([[fx, 0, cx_r, -fx * b], [0, fx, cy, 0], [0, 0, 1, 0]])
    g = StereoGeometry.from_projections(p1, p2, 1920, 1080)
    assert g.baseline_m == pytest.approx(b)
    assert g.doffs == pytest.approx(cx_r - cx_l)
    # Un punto proyectado con esas matrices recupera su profundidad.
    ul, _, ur = project(g, 0.2, 0.1, 1.7)
    assert g.depth_at(ul - ur) == pytest.approx(1.7, rel=1e-12)


def test_from_projections_rejects_mismatched_pair():
    p1 = np.array([[1000.0, 0, 950, 0], [0, 1000, 540, 0], [0, 0, 1, 0]])
    p2 = p1.copy()
    p2[0, 0] = 900.0
    with pytest.raises(InvalidInput):
        StereoGeometry.from_projections(p1, p2, 1920, 1080)
    with pytest.raises(InvalidInput):
        StereoGeometry.from_projections(p1[:, :3], p2, 1920, 1080)


# --- Disparidad <-> profundidad ---------------------------------------------------------


@pytest.mark.parametrize("g", [ELP, MB], ids=["elp", "doffs"])
def test_round_trip_depth_disparity_depth(g):
    """M0: d -> Z -> d con error relativo <= 1e-5 en todo el rango útil."""
    z = np.linspace(0.5, 3.0, g.width * g.height, dtype=np.float32).reshape(g.height, g.width)
    d, ok_d = g.depth_to_disparity(z)
    z2, ok_z = g.disparity_to_depth(d, ok_d)
    d2, _ = g.depth_to_disparity(z2, ok_z)
    assert ok_d.all() and ok_z.all()
    assert np.max(np.abs(z2 - z) / z) <= 1e-5
    assert np.max(np.abs(d2 - d) / d) <= 1e-5


@pytest.mark.parametrize("g", [ELP, MB], ids=["elp", "doffs"])
def test_projected_point_gives_its_depth(g):
    for z in (0.5, 1.0, 2.0, 3.0):
        ul, _, ur = project(g, -0.3, 0.2, z)
        assert g.depth_at(ul - ur) == pytest.approx(z, rel=1e-12)
        assert g.disparity_at(z) == pytest.approx(ul - ur, rel=1e-12)


def test_invalid_disparities_never_become_distances():
    d = np.full((ELP.height, ELP.width), 30.0, np.float32)
    d[0, 0] = 0.0  # cero: infinitamente lejos, no medible
    d[0, 1] = -4.0
    d[0, 2] = np.nan
    d[0, 3] = np.inf
    valid = np.ones(d.shape, bool)
    valid[0, 4] = False  # el que ya venía inválido sigue inválido
    z, ok = ELP.disparity_to_depth(d, valid)
    assert z.dtype == np.float32 and ok.dtype == np.bool_
    assert not ok[0, :5].any()
    assert np.isnan(z[0, :5]).all()
    assert ok[1:].all()
    assert np.all(z[ok] > 0)
    for bad in (0.0, -4.0, float("nan")):
        assert ELP.depth_at(bad) is None
    for bad in (0.0, -1.0, float("inf")):
        assert ELP.disparity_at(bad) is None


def test_depth_far_beyond_doffs_is_unmeasurable():
    # Con doffs grande, una Z enorme daría disparidad negativa: no se inventa.
    z = np.full((MB.height, MB.width), 1e6, np.float32)
    d, ok = MB.depth_to_disparity(z)
    assert not ok.any() and np.isnan(d).all()


@pytest.mark.parametrize(
    "call",
    [
        lambda: ELP.disparity_to_depth(np.ones((1080, 1920), np.float64)),
        lambda: ELP.disparity_to_depth(np.ones((720, 1280), np.float32)),
        lambda: ELP.disparity_to_depth(
            np.ones((1080, 1920), np.float32), np.ones((1080, 1920), np.uint8)
        ),
        lambda: ELP.depth_to_disparity(np.ones((1080, 1920, 1), np.float32)),
    ],
)
def test_maps_must_match_dtype_and_geometry(call):
    with pytest.raises((InvalidInput, IdentityMismatch)):
        call()


def test_require_size():
    ELP.require_size(np.zeros((1080, 1920, 3), np.uint8))
    with pytest.raises(IdentityMismatch):
        ELP.require_size(np.zeros((720, 1280, 3), np.uint8))


# --- Ángulos ----------------------------------------------------------------------------


def test_pixel_to_angles_signs():
    assert ELP.pixel_to_angles(ELP.cx, ELP.cy) == (0.0, 0.0)
    h, v = ELP.pixel_to_angles(ELP.cx + ELP.fx, ELP.cy - ELP.fy)  # a la derecha y arriba
    assert h == pytest.approx(45.0) and v == pytest.approx(45.0)
    h, v = ELP.pixel_to_angles(0, 1079)  # esquina inferior izquierda
    assert h < 0 and v < 0


# --- Cambio de resolución y recorte -----------------------------------------------------


def test_resize_keeps_depth_and_angles_of_the_same_point():
    g720 = ELP.resized(1280, 720)
    s = 1280 / 1920
    assert g720.fx == pytest.approx(ELP.fx * s)
    for x, y, z in [(0.0, 0.0, 1.0), (-0.4, 0.25, 0.8), (0.6, -0.3, 2.7)]:
        ul, v, ur = project(ELP, x, y, z)
        d1080 = ul - ur
        d720 = d1080 * s  # la disparidad escala con el ancho
        assert g720.depth_at(d720) == pytest.approx(z, rel=1e-9)
        # El mismo punto, en coordenadas de 720p, tiene los mismos ángulos.
        u720 = (ul + 0.5) * s - 0.5
        v720 = (v + 0.5) * s - 0.5
        a1080 = ELP.pixel_to_angles(ul, v)
        a720 = g720.pixel_to_angles(u720, v720)
        assert a720 == pytest.approx(a1080, abs=1e-9)


def test_resize_back_and_forth_is_identity():
    back = ELP.resized(1280, 720).resized(1920, 1080)
    for name in ("fx", "fy", "cx", "cy", "baseline_m", "doffs"):
        assert getattr(back, name) == pytest.approx(getattr(ELP, name), rel=1e-12)
    assert MB.resized(750, 500).doffs == pytest.approx(MB.doffs / 2)


def test_crop_moves_center_but_keeps_depth_and_angles():
    c = ELP.cropped(100, 50, 1280, 720)
    assert (c.fx, c.baseline_m, c.doffs) == (ELP.fx, ELP.baseline_m, ELP.doffs)
    ul, v, ur = project(ELP, 0.1, -0.05, 1.5)
    assert c.depth_at(ul - ur) == pytest.approx(1.5)
    assert c.pixel_to_angles(ul - 100, v - 50) == pytest.approx(ELP.pixel_to_angles(ul, v))


@pytest.mark.parametrize(
    "call",
    [
        lambda: ELP.resized(0, 720),
        lambda: ELP.resized(1280.0, 720),
        lambda: ELP.cropped(1000, 0, 1280, 720),  # se sale por la derecha
        lambda: ELP.cropped(-1, 0, 100, 100),
        lambda: ELP.cropped(0, 0, 0, 100),
    ],
)
def test_bad_resize_or_crop_rejected(call):
    with pytest.raises(InvalidInput):
        call()


# --- Máscaras y mapas -------------------------------------------------------------------


def test_resize_mask_stays_boolean_and_keeps_area():
    m = np.zeros((1080, 1920), bool)
    m[300:600, 900:1200] = True
    small = resize_mask(m, 1280, 720)
    assert small.dtype == np.bool_ and small.shape == (720, 1280)
    assert small.sum() == pytest.approx(m.sum() * (720 / 1080) * (1280 / 1920), rel=0.02)
    # El bloque queda donde corresponde: centro escalado.
    ys, xs = np.nonzero(small)
    assert xs.mean() == pytest.approx(((900 + 1199) / 2 + 0.5) * 2 / 3 - 0.5, abs=1.0)


def test_resize_mask_batch_for_detections():
    masks = np.zeros((3, 1080, 1920), bool)
    masks[1, :10, :10] = True
    out = resize_mask(masks, 1280, 720)
    assert out.shape == (3, 720, 1280) and out.dtype == np.bool_
    assert not out[0].any() and out[1].any() and not out[2].any()


@pytest.mark.parametrize(
    "bad",
    [np.zeros((10, 10), np.uint8), np.zeros((2, 2, 2, 2), bool), [[True]]],
)
def test_resize_mask_rejects_non_bool(bad):
    with pytest.raises(InvalidInput):
        resize_mask(bad, 5, 5)


def test_resize_disparity_scales_values_and_never_blends():
    d = np.full((1080, 1920), 60.0, np.float32)
    d[:, 960:] = 20.0  # borde vertical: objeto cerca a la izquierda, fondo a la derecha
    valid = np.ones(d.shape, bool)
    valid[:100] = False
    d[:100] = np.nan
    d720, v720 = resize_disparity(d, valid, 1280, 720)
    assert d720.dtype == np.float32 and v720.dtype == np.bool_
    # Solo aparecen los dos valores escalados: ningún valor intermedio inventado en el borde.
    assert np.unique(d720[v720]).tolist() == pytest.approx([20.0 * 2 / 3, 40.0], rel=1e-6)
    assert np.isnan(d720[~v720]).all()
    # La profundidad se conserva al cambiar de geometría.
    z1080, _ = ELP.disparity_to_depth(d, valid)
    z720, _ = ELP.resized(1280, 720).disparity_to_depth(d720, v720)
    assert np.nanmax(z720) == pytest.approx(np.nanmax(z1080), rel=1e-6)
    assert np.nanmin(z720) == pytest.approx(np.nanmin(z1080), rel=1e-6)


def test_angles_are_finite_everywhere():
    for u, v in [(0, 0), (1919, 1079), (959.5, 0)]:
        assert all(math.isfinite(a) for a in ELP.pixel_to_angles(u, v))
