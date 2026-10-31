"""Tests del contrato (métrica M0): casos válidos y entradas adversas rechazadas."""

import dataclasses

import numpy as np
import pytest

from visionx.shared.contracts import (
    SCHEMA_VERSION,
    AudioEvent,
    CaptureClock,
    Command,
    DepthResult,
    DepthStatus,
    Detection,
    DistancePolicy,
    FrameKey,
    Mode,
    Priority,
    SpatialObject,
    StereoFrame,
    UncertaintyKind,
    check_geometry,
    check_not_expired,
    check_same_frame,
    check_schema,
)
from visionx.shared.errors import (
    ContractError,
    Expired,
    IdentityMismatch,
    InvalidInput,
    SchemaMismatch,
)

S = "sesion-test"


def img(w=64, h=48, dtype=np.uint8):
    return np.zeros((h, w, 3), dtype=dtype)


def frame(**kw):
    base = dict(session_id=S, frame_id=1, left=img(), right=img(), received_ns=1_000)
    base.update(kw)
    return StereoFrame(**base)


def depth(**kw):
    d = np.full((4, 6), 10.0, np.float32)
    base = dict(
        session_id=S,
        frame_id=1,
        model_id="sgbm",
        geometry_id="g720",
        disparity_px=d,
        valid_mask=np.ones(d.shape, bool),
        status=DepthStatus.VALID,
        inference_ms=3.0,
    )
    base.update(kw)
    return DepthResult(**base)


def detection(n=2, w=8, h=6, **kw):
    base = dict(
        session_id=S,
        frame_id=1,
        model_id="fake",
        geometry_id="g1080",
        image_size=(w, h),
        boxes=np.tile(np.array([[1, 1, 3, 3]], np.float32), (n, 1)),
        classes=tuple(["cup"] * n),
        scores=np.full(n, 0.9, np.float32),
        inference_ms=5.0,
    )
    base.update(kw)
    return Detection(**base)


def spatial(**kw):
    base = dict(
        session_id=S,
        frame_id=1,
        detection_index=0,
        track_id=7,
        label="cup",
        depth_model_id="fake",
        angle_h_deg=10.0,
        angle_v_deg=-5.0,
        z_m=1.2,
        z_spread_m=0.03,
        valid_fraction=0.8,
        detector_score=0.9,
        policy=DistancePolicy.SPEAK_METERS,
    )
    base.update(kw)
    return SpatialObject(**base)


# --- Errores ---------------------------------------------------------------------------


def test_contract_errors_are_value_errors():
    assert issubclass(ContractError, ValueError)
    for e in (InvalidInput, SchemaMismatch, IdentityMismatch, Expired):
        assert issubclass(e, ContractError)


# --- FrameKey ----------------------------------------------------------------------------


def test_frame_key_is_hashable_and_compares_by_value():
    assert FrameKey(S, 3) == FrameKey(S, 3)
    assert len({FrameKey(S, 3), FrameKey(S, 3), FrameKey("otra", 3)}) == 2


@pytest.mark.parametrize("sid, fid", [("", 1), ("  ", 1), (S, -1), (S, 1.0), (S, True)])
def test_frame_key_rejects_bad_identity(sid, fid):
    with pytest.raises(InvalidInput):
        FrameKey(sid, fid)


# --- StereoFrame -------------------------------------------------------------------------


def test_stereo_frame_valid():
    f = frame()
    assert f.size == (64, 48)
    assert f.key == FrameKey(S, 1)
    assert not f.is_replay
    assert f.schema == SCHEMA_VERSION


def test_stereo_frame_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        frame().frame_id = 2


@pytest.mark.parametrize(
    "kw",
    [
        dict(left=img(dtype=np.float32), right=img(dtype=np.float32)),  # no uint8
        dict(right=img(32)),  # ojos de distinto tamaño
        dict(left=np.zeros((48, 64), np.uint8), right=np.zeros((48, 64), np.uint8)),  # gris
        dict(left=np.zeros((48, 64, 4), np.uint8), right=np.zeros((48, 64, 4), np.uint8)),
        dict(left=img(0, 0), right=img(0, 0)),  # vacía
        dict(left=[[0]]),  # no es ndarray
        dict(received_ns=-1),
        dict(capture_ns=5),  # hora de captura sin decir de qué reloj
        dict(capture_clock=CaptureClock.DEVICE),  # reloj sin hora
        dict(rectified=True),  # rectificado sin calibración ni geometría
        dict(rectified=True, calibration_id="c1"),  # falta geometría
        dict(session_id=""),
        dict(frame_id=-3),
    ],
)
def test_stereo_frame_rejects_adversarial(kw):
    with pytest.raises(InvalidInput):
        frame(**kw)


def test_stereo_frame_capture_and_replay_times():
    f = frame(
        capture_ns=900,
        capture_clock=CaptureClock.ESTIMATED,
        replay_original_ns=123_456,
        rectified=True,
        calibration_id="c1",
        geometry_id="g1080",
    )
    assert f.is_replay


# --- DepthResult -------------------------------------------------------------------------


def test_depth_result_valid_with_uncertainty_and_depth():
    d = depth(
        depth_m=np.full((4, 6), 1.5, np.float32),
        uncertainty=np.full((4, 6), 0.5, np.float32),
        uncertainty_kind=UncertaintyKind.LAPLACE_B,
    )
    assert d.size == (6, 4)


def test_depth_result_nan_and_zero_allowed_only_outside_mask():
    disp = np.full((4, 6), 10.0, np.float32)
    mask = np.ones((4, 6), bool)
    disp[0, :] = np.nan
    disp[1, :] = 0.0
    mask[:2, :] = False
    depth(disparity_px=disp, valid_mask=mask, status=DepthStatus.PARTIAL, reason="huecos")
    mask[0, 0] = True
    with pytest.raises(InvalidInput):
        depth(disparity_px=disp, valid_mask=mask, status=DepthStatus.PARTIAL, reason="huecos")


def test_depth_result_unmeasurable_needs_empty_mask_and_reason():
    empty = np.zeros((4, 6), bool)
    nan = np.full((4, 6), np.nan, np.float32)
    depth(disparity_px=nan, valid_mask=empty, status=DepthStatus.UNMEASURABLE, reason="oscuro")
    with pytest.raises(InvalidInput):  # sin motivo
        depth(disparity_px=nan, valid_mask=empty, status=DepthStatus.UNMEASURABLE)
    with pytest.raises(InvalidInput):  # máscara vacía declarada válida
        depth(disparity_px=nan, valid_mask=empty, status=DepthStatus.VALID)
    with pytest.raises(InvalidInput):  # píxeles válidos declarados no medibles
        depth(status=DepthStatus.UNMEASURABLE, reason="x")


@pytest.mark.parametrize(
    "kw",
    [
        dict(disparity_px=np.full((4, 6), 10.0, np.float64)),  # float64
        dict(valid_mask=np.full((4, 6), 255, np.uint8)),  # máscara 0/255
        dict(valid_mask=np.ones((4, 5), bool)),  # otro tamaño
        dict(disparity_px=np.full((4, 6), -1.0, np.float32)),  # negativa dentro de la máscara
        dict(depth_m=np.full((4, 6), 0.0, np.float32)),  # cero metros no es una distancia
        dict(depth_m=np.full((4, 6), 1.0, np.float64)),
        dict(depth_m=np.full((3, 6), 1.0, np.float32)),
        dict(inference_ms=-1.0),
        dict(inference_ms=float("nan")),
        dict(geometry_id=""),
        dict(status="valid"),  # texto suelto en vez del enum
        dict(status=DepthStatus.PARTIAL),  # parcial sin motivo
        dict(uncertainty=np.ones((4, 6), np.float32)),  # sin decir de qué tipo
        dict(uncertainty_kind=UncertaintyKind.LAPLACE_B),  # tipo sin valores
        dict(uncertainty=np.zeros((4, 6), np.float32), uncertainty_kind=UncertaintyKind.LAPLACE_B),
        dict(
            uncertainty=np.full((4, 6), np.inf, np.float32),
            uncertainty_kind=UncertaintyKind.LAPLACE_B,
        ),
        dict(
            uncertainty=np.full((4, 6), -1.0, np.float32),
            uncertainty_kind=UncertaintyKind.LR_CONSISTENCY,
        ),
        dict(alignment_quality=float("inf")),
    ],
)
def test_depth_result_rejects_adversarial(kw):
    with pytest.raises(InvalidInput):
        depth(**kw)


def test_lr_consistency_can_be_zero():
    depth(uncertainty=np.zeros((4, 6), np.float32), uncertainty_kind=UncertaintyKind.LR_CONSISTENCY)


# --- Detection ---------------------------------------------------------------------------


def test_detection_valid_with_masks_and_tracks():
    det = detection(masks=np.zeros((2, 6, 8), bool), track_ids=(3, None))
    assert len(det) == 2


def test_detection_zero_objects_is_valid():
    det = detection(n=0, masks=np.zeros((0, 6, 8), bool))
    assert len(det) == 0


@pytest.mark.parametrize(
    "kw",
    [
        dict(classes=("cup",)),  # menos clases que cajas
        dict(classes=["cup", "cup"]),  # lista mutable
        dict(boxes=np.zeros((2, 4), np.float64)),
        dict(boxes=np.array([[3, 1, 1, 3], [1, 1, 3, 3]], np.float32)),  # x2 < x1
        dict(boxes=np.array([[np.nan, 1, 3, 3], [1, 1, 3, 3]], np.float32)),
        dict(scores=np.array([0.5, 1.5], np.float32)),
        dict(scores=np.array([0.5], np.float32)),
        dict(masks=np.zeros((1, 6, 8), bool)),  # una máscara para dos objetos
        dict(masks=np.zeros((2, 8, 6), bool)),  # alto y ancho cruzados
        dict(masks=np.zeros((2, 6, 8), np.uint8)),
        dict(track_ids=(1,)),
        dict(track_ids=(1, -2)),
        dict(image_size=(0, 6)),
        dict(image_size=[8, 6]),
    ],
)
def test_detection_rejects_adversarial(kw):
    with pytest.raises(InvalidInput):
        detection(**kw)


# --- SpatialObject -----------------------------------------------------------------------


def test_spatial_object_valid_and_unmeasured():
    spatial()
    spatial(z_m=None, z_spread_m=None, valid_fraction=0.0, policy=DistancePolicy.DIRECTION_ONLY)


@pytest.mark.parametrize(
    "kw",
    [
        dict(z_m=None),  # decir metros sin distancia
        dict(z_m=0.0),
        dict(z_m=float("nan")),
        dict(z_spread_m=-0.1),
        dict(valid_fraction=1.2),
        dict(detector_score=-0.1),
        dict(angle_h_deg=120.0),
        dict(detection_index=-1),
        dict(policy="speak_meters"),
    ],
)
def test_spatial_object_rejects_adversarial(kw):
    with pytest.raises(InvalidInput):
        spatial(**kw)


# --- Command y AudioEvent ----------------------------------------------------------------


def test_command_and_audio_event_valid():
    Command(1, Mode.DISTANCE, "a qué distancia", 100, deadline_ns=200, frame=FrameKey(S, 1))
    AudioEvent(1, Priority.SEARCH, "bip", 100, deadline_ns=150, frame=FrameKey(S, 1))


@pytest.mark.parametrize(
    "build",
    [
        lambda: Command(1, "search", "buscar", 100),
        lambda: Command(1, Mode.SEARCH, "buscar", 100, deadline_ns=50),  # vence antes de nacer
        lambda: Command(1, Mode.SEARCH, "buscar", 100, target=""),
        lambda: Command(1, Mode.DISTANCE, "x", 100, frame=(S, 1)),
        lambda: AudioEvent(-1, Priority.SHORT, "hola", 0),
        lambda: AudioEvent(1, 2, "hola", 0),
        lambda: AudioEvent(1, Priority.SHORT, "", 0),
    ],
)
def test_command_and_audio_reject_adversarial(build):
    with pytest.raises(InvalidInput):
        build()


def test_priority_order():
    assert Priority.ALERT > Priority.SEARCH > Priority.SHORT > Priority.LONG


# --- Chequeos del consumidor -------------------------------------------------------------


def test_check_same_frame():
    key = check_same_frame(frame(), depth(), detection(), spatial())
    assert key == FrameKey(S, 1)
    with pytest.raises(IdentityMismatch):
        check_same_frame(depth(), detection(frame_id=2))
    with pytest.raises(IdentityMismatch):  # mismo número de frame, otra grabación
        check_same_frame(depth(), detection(session_id="otra"))


def test_check_geometry():
    check_geometry(depth(), "g720")
    with pytest.raises(IdentityMismatch):
        check_geometry(depth(), "g1080")


def test_schema_mismatch_rejected_on_build_and_by_consumer():
    with pytest.raises(SchemaMismatch):
        depth(schema=1)
    with pytest.raises(SchemaMismatch):
        frame(schema=SCHEMA_VERSION + 1)

    class Viejo:
        schema = 1

    with pytest.raises(SchemaMismatch):
        check_schema(Viejo())
    check_schema(depth())


def test_expiry_uses_the_given_clock():
    ev = AudioEvent(1, Priority.SEARCH, "bip", created_ns=1_000, deadline_ns=2_000)
    check_not_expired(ev, now=2_000)
    with pytest.raises(Expired):
        check_not_expired(ev, now=2_001)
    check_not_expired(AudioEvent(2, Priority.SHORT, "sin límite", 0), now=10**18)
