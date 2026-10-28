import numpy as np
import pytest

from visionx.shared.contracts import (
    DepthResult,
    Detection,
    StereoFrame,
    UncertaintyKind,
    now_ns,
)


def _img(w=64, h=48):
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_stereo_frame_size():
    f = StereoFrame(frame_id=1, capture_ns=now_ns(), left=_img(), right=_img())
    assert f.size == (64, 48)


def test_stereo_frame_rejects_mismatched_eyes():
    with pytest.raises(ValueError):
        StereoFrame(frame_id=1, capture_ns=0, left=_img(64), right=_img(32))


def test_depth_result_uncertainty_must_match_kind():
    d = np.zeros((4, 4), np.float32)
    m = np.ones((4, 4), bool)
    DepthResult(1, "sgbm", d, m, 1.0)
    DepthResult(1, "fusion", d, m, 1.0, uncertainty=d, uncertainty_kind=UncertaintyKind.LAPLACE_B)
    with pytest.raises(ValueError):
        DepthResult(1, "fusion", d, m, 1.0, uncertainty=d)


def test_detection_counts_must_match():
    Detection(1, np.zeros((2, 4)), ["cup", "cup"], np.ones(2), track_ids=[3, 4])
    with pytest.raises(ValueError):
        Detection(1, np.zeros((2, 4)), ["cup"], np.ones(2))
