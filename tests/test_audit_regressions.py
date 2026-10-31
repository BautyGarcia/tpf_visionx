"""Regresiones de A04.1–A04.6 con datos pequeños e independientes de hardware."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from visionx.shared.clock import ManualClock
from visionx.shared.contracts import (
    SCHEMA_VERSION,
    DepthResult,
    DepthStatus,
    Detection,
    StereoFrame,
    check_depth_geometry,
    check_detection_frame,
)
from visionx.shared.errors import IdentityMismatch, InvalidInput, SchemaMismatch
from visionx.shared.geometry import StereoGeometry, resize_disparity, resize_mask


def geometry(**overrides):
    """Cámara virtual pequeña; no representa una calibración física de la ELP."""
    arguments = dict(width=4, height=3, fx=100.0, fy=90.0, cx=1.5, cy=1.0, baseline_m=0.06)
    arguments.update(overrides)
    return StereoGeometry(**arguments)


def pair(g=None, **overrides):
    """Par sintético que declara el contexto geométrico de sus imágenes."""
    if g is None:
        g = geometry()
    arguments = dict(
        session_id="s",
        frame_id=1,
        left=np.zeros((g.height, g.width, 3), np.uint8),
        right=np.zeros((g.height, g.width, 3), np.uint8),
        received_ns=0,
        rectified=True,
        calibration_id="virtual",
        geometry_id=g.geometry_id,
    )
    arguments.update(overrides)
    return StereoFrame(**arguments)


def result(g=None, **overrides):
    """Plano a un metro: f*B/Z = 6 píxeles de disparidad efectiva."""
    if g is None:
        g = geometry()
    arguments = dict(
        session_id="s",
        frame_id=1,
        model_id="virtual",
        geometry_id=g.geometry_id,
        doffs=g.doffs,
        disparity_px=np.full((g.height, g.width), 6.0 - g.doffs, np.float32),
        valid_mask=np.ones((g.height, g.width), bool),
        status=DepthStatus.VALID,
        inference_ms=0.0,
    )
    arguments.update(overrides)
    return DepthResult(**arguments)


def detection(g=None, **overrides):
    """Una detección en la imagen de referencia; máscara y profundidad comparten frame."""
    if g is None:
        g = geometry()
    arguments = dict(
        session_id="s",
        frame_id=1,
        model_id="virtual",
        geometry_id=g.geometry_id,
        calibration_id="virtual",
        image_size=g.size,
        boxes=np.array([[0, 0, 2, 2]], np.float32),
        classes=("cup",),
        scores=np.array([0.9], np.float32),
        inference_ms=0.0,
        masks=np.ones((1, g.height, g.width), bool),
    )
    arguments.update(overrides)
    return Detection(**arguments)


@pytest.mark.parametrize("offset", [-10.0, 0.0, 6.0, 10.0])
def test_offset_round_trip_and_contract(offset):
    g = geometry(doffs=offset)
    z = np.full((3, 4), 1.0, np.float32)
    d, mask = g.depth_to_disparity(z)
    assert mask.all()
    np.testing.assert_allclose(d, 6.0 - offset)
    back, ok = g.disparity_to_depth(d, mask)
    np.testing.assert_allclose(back, z)
    assert ok.all()
    check_depth_geometry(result(g, disparity_px=d), g)
    assert g.disparity_at(1.0) == pytest.approx(6.0 - offset)
    assert g.depth_at(6.0 - offset) == pytest.approx(1.0)


def test_crop_outside_principal_preserves_rays_and_depth():
    g = geometry(width=100, height=100, cx=49.5, cy=49.5)
    c = g.cropped(0, 0, 20, 20)
    assert c.cx == 49.5
    assert c.pixel_to_angles(10, 10) == g.pixel_to_angles(10, 10)
    assert c.depth_at(6.0) == g.depth_at(6.0)
    c = g.cropped(80, 80, 20, 20)
    assert c.cx < 0 and c.cy < 0
    assert c.pixel_to_angles(10, 10) == g.pixel_to_angles(90, 90)


@pytest.mark.parametrize(
    "which,index,value",
    [
        (0, (0, 1), 1.0),
        (0, (0, 3), 1.0),
        (0, (2, 2), 2.0),
        (1, (1, 1), 999.0),
        (1, (1, 3), -1.0),
        (1, (2, 2), np.nan),
        (1, (2, 3), np.inf),
        (1, (0, 3), 0.0),
        (1, (0, 3), 6.0),
    ],
)
def test_invalid_projections_rejected(which, index, value):
    p1 = np.array([[100.0, 0, 1.5, 0], [0, 90.0, 1.0, 0], [0, 0, 1.0, 0]])
    p2 = p1.copy()
    p2[0, 3] = -6.0
    matrices = [p1, p2]
    matrices[which][index] = value
    with pytest.raises(InvalidInput):
        StereoGeometry.from_projections(p1, p2, 4, 3)


def test_projection_layout_from_real_opencv_rectification():
    import cv2

    k = np.array([[100.0, 0, 49.5], [0, 100.0, 49.5], [0, 0, 1.0]])
    _, _, p1, p2, _, _, _ = cv2.stereoRectify(
        k, np.zeros(5), k, np.zeros(5), (100, 100), np.eye(3), np.array([[-0.06], [0.0], [0.0]])
    )
    g = StereoGeometry.from_projections(p1, p2, 100, 100)
    assert g.baseline_m == pytest.approx(0.06)


@pytest.mark.parametrize(
    "kw",
    [
        {"calibration_id": ""},
        {"geometry_id": "  "},
        {"rectified": 1},
        {"capture_ns": 0, "capture_clock": "device"},
    ],
)
def test_bad_frame_metadata_rejected(kw):
    with pytest.raises(InvalidInput):
        pair(**kw)


@pytest.mark.parametrize(
    "kw",
    [
        {"uncertainty": np.ones((3, 4), np.float32), "uncertainty_kind": "inventado"},
        {"doffs": np.nan},
        {"doffs": True},
    ],
)
def test_bad_depth_metadata_rejected(kw):
    with pytest.raises(InvalidInput):
        result(**kw)


def test_schema_two_requires_explicit_rebuild():
    assert SCHEMA_VERSION == 3
    with pytest.raises(SchemaMismatch):
        pair(schema=2)
    with pytest.raises(SchemaMismatch):
        result(schema=2)


def test_all_array_messages_are_independent_read_only_snapshots():
    image = np.zeros((3, 4, 3), np.uint8)
    disp = np.full((3, 4), 6.0, np.float32)
    mask = np.ones((3, 4), bool)
    boxes = np.array([[0, 0, 2, 2]], np.float32)
    scores = np.array([0.9], np.float32)
    masks = np.ones((1, 3, 4), bool)
    depth = np.ones((3, 4), np.float32)
    f = pair(left=image, right=image)
    d = result(disparity_px=disp, valid_mask=mask, depth_m=depth)
    det = detection(boxes=boxes, scores=scores, masks=masks)
    # Simular que el productor reutiliza todos sus buffers después de publicar.
    image[:] = 255
    disp[:] = 0
    mask[:] = False
    boxes[:] = 0
    scores[:] = 0
    masks[:] = False
    depth[:] = 0
    assert f.left[0, 0, 0] == 0 and d.disparity_px[0, 0] == 6 and d.valid_mask.all()
    assert d.depth_m[0, 0] == 1 and det.boxes[0, 2] == 2 and det.scores[0] > 0.8 and det.masks.all()
    # El consumidor tampoco puede reactivar la escritura sobre los mensajes publicados.
    for arr in [
        f.left,
        f.right,
        d.disparity_px,
        d.valid_mask,
        d.depth_m,
        det.boxes,
        det.scores,
        det.masks,
    ]:
        with pytest.raises(ValueError):
            arr.flat[0] = 0
        with pytest.raises(ValueError):
            arr.setflags(write=True)


def test_detection_reference_rejects_same_size_different_rectification():
    f = pair()
    det = detection()
    check_detection_frame(f, det)
    with pytest.raises(IdentityMismatch):
        check_detection_frame(f, replace(det, geometry_id=geometry(cx=1.0).geometry_id))
    with pytest.raises(IdentityMismatch):
        check_detection_frame(f, replace(det, frame_id=2))
    with pytest.raises(IdentityMismatch):
        check_detection_frame(replace(f, geometry_id=None, rectified=False), det)
    with pytest.raises(InvalidInput):
        detection(geometry_id="")


def test_depth_geometry_rejects_wrong_offset_and_shape():
    g = geometry()
    with pytest.raises(IdentityMismatch):
        check_depth_geometry(result(doffs=1.0), g)
    small = geometry(width=2)
    with pytest.raises(IdentityMismatch):
        check_depth_geometry(result(small, geometry_id=g.geometry_id), g)


def test_geometry_id_distinguishes_submicron_baseline_change():
    assert geometry().geometry_id != geometry(baseline_m=0.0600001).geometry_id


@pytest.mark.parametrize(
    "operation",
    [
        lambda: ManualClock(-1),
        lambda: ManualClock(1.5),
        lambda: ManualClock(True),
        lambda: ManualClock().advance(0.5),
        lambda: ManualClock().advance(-1),
        lambda: ManualClock().set(1.5),
    ],
)
def test_clock_rejects_truncation_and_invalid_times(operation):
    with pytest.raises(ValueError):
        operation()


@pytest.mark.parametrize(
    "call",
    [
        lambda: resize_disparity(np.ones((0, 4), np.float32), np.ones((0, 4), bool), 2, 2),
        lambda: resize_mask(np.zeros((0, 4), bool), 2, 2),
        lambda: geometry().require_size(np.zeros(4)),
        lambda: geometry().pixel_to_angles(np.nan, 0),
    ],
)
def test_invalid_shapes_and_angles_fail_explicitly(call):
    with pytest.raises(InvalidInput):
        call()


def test_same_geometry_but_other_calibration_is_rejected():
    with pytest.raises(IdentityMismatch):
        check_detection_frame(pair(), replace(detection(), calibration_id="otra"))


def test_depth_map_must_agree_with_disparity():
    with pytest.raises(IdentityMismatch):
        check_depth_geometry(result(depth_m=np.full((3, 4), 2.0, np.float32)), geometry())


def test_float32_overflow_is_invalid_not_a_valid_infinity():
    g = geometry(fx=1e30, baseline_m=1e10)
    with np.errstate(over="raise"):
        z, ok = g.disparity_to_depth(np.ones((3, 4), np.float32))
    assert not ok.any() and np.isnan(z).all()


def test_schema_three_fixture_can_be_consumed_end_to_end():
    """Fixture pública para que productores/consumidores validen el nuevo convenio."""
    fixture_path = Path(__file__).parent / "fixtures" / "schema3-negative-disparity.yaml"
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    camera = StereoGeometry(**fixture["geometry"])
    frame = pair(
        camera,
        session_id=fixture["session_id"],
        frame_id=fixture["frame_id"],
        calibration_id=fixture["calibration_id"],
        schema=fixture["schema"],
    )
    objects = detection(
        camera,
        session_id=frame.session_id,
        frame_id=frame.frame_id,
        calibration_id=frame.calibration_id,
        schema=fixture["schema"],
    )
    disparity = np.full((camera.height, camera.width), fixture["expected_disparity_px"], np.float32)
    depth_m, mask = camera.disparity_to_depth(disparity)
    prediction = result(
        camera,
        session_id=frame.session_id,
        frame_id=frame.frame_id,
        disparity_px=disparity,
        valid_mask=mask,
        depth_m=depth_m,
        schema=fixture["schema"],
    )
    check_detection_frame(frame, objects)
    check_depth_geometry(prediction, camera)
    assert mask.all()
    np.testing.assert_allclose(depth_m, fixture["expected_depth_m"])


@pytest.mark.parametrize("rotation_y", [-0.02, 0.0, 0.02])
def test_canonical_projection_validation_accepts_small_real_rotations(rotation_y):
    import cv2

    intrinsics = np.array([[100.0, 0.0, 49.5], [0.0, 100.0, 49.5], [0.0, 0.0, 1.0]])
    rotation, _ = cv2.Rodrigues(np.array([[0.0], [rotation_y], [0.0]]))
    translation = np.array([[-0.06], [0.001], [0.001]])
    _, _, left, right, _, _, _ = cv2.stereoRectify(
        intrinsics, np.zeros(5), intrinsics, np.zeros(5), (100, 100), rotation, translation
    )
    camera = StereoGeometry.from_projections(left, right, 100, 100)
    assert camera.baseline_m == pytest.approx(float(np.linalg.norm(translation)))


def test_resize_disparity_clears_mask_on_float32_overflow():
    values = np.full((1, 1), np.finfo(np.float32).max, np.float32)
    resized, mask = resize_disparity(values, np.ones((1, 1), bool), 2, 1)
    assert not mask.any()
    assert np.isnan(resized).all()


@pytest.mark.parametrize(
    "bad_projection",
    [
        [["invalid"]],
        np.ones((3, 4), dtype=np.complex128) * (1 + 1j),
    ],
)
def test_nonnumeric_or_complex_projections_rejected(bad_projection):
    with pytest.raises(InvalidInput):
        StereoGeometry.from_projections(bad_projection, np.zeros((3, 4)), 4, 3)
