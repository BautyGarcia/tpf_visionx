"""Fakes mínimos que cumplen las interfaces, y relojes."""

import numpy as np
import pytest

from visionx.shared.clock import Clock, ManualClock, MonotonicClock
from visionx.shared.contracts import (
    AudioEvent,
    DepthResult,
    DepthStatus,
    Detection,
    SpatialObject,
    StereoFrame,
    check_same_frame,
)
from visionx.shared.interfaces import (
    AudioSink,
    DepthEstimator,
    Detector,
    FrameSource,
    SpatialEstimator,
)


class ListSource:
    def __init__(self, n):
        self._i, self._n = 0, n

    def read(self) -> StereoFrame | None:
        if self._i >= self._n:
            return None
        im = np.zeros((4, 4, 3), np.uint8)
        self._i += 1
        return StereoFrame("s", self._i - 1, im, im.copy(), received_ns=self._i)

    def close(self) -> None:
        pass


class ConstDepth:
    model_id = "const"

    def predict(self, frame: StereoFrame) -> DepthResult:
        w, h = frame.size
        return DepthResult(
            frame.session_id,
            frame.frame_id,
            self.model_id,
            "g",
            np.ones((h, w), np.float32),
            np.ones((h, w), bool),
            DepthStatus.VALID,
            0.0,
        )

    def close(self) -> None:
        pass


class NoneDetector:
    model_id = "none"

    def predict(self, frame: StereoFrame) -> Detection:
        return Detection(
            frame.session_id,
            frame.frame_id,
            self.model_id,
            frame.size,
            np.zeros((0, 4), np.float32),
            (),
            np.zeros(0, np.float32),
            0.0,
        )

    def close(self) -> None:
        pass


class EmptySpatial:
    def locate(self, frame, depth, detections) -> list[SpatialObject]:
        check_same_frame(frame, depth, detections)
        return []


class ListSink:
    def __init__(self):
        self.events: list[AudioEvent] = []

    def submit(self, event: AudioEvent) -> None:
        self.events.append(event)

    def cancel(self, request_id: int) -> None:
        self.events = [e for e in self.events if e.request_id != request_id]

    def close(self) -> None:
        pass


def test_fakes_satisfy_interfaces():
    assert isinstance(ListSource(1), FrameSource)
    assert isinstance(ConstDepth(), DepthEstimator)
    assert isinstance(NoneDetector(), Detector)
    assert isinstance(EmptySpatial(), SpatialEstimator)
    assert isinstance(ListSink(), AudioSink)
    assert not isinstance(ConstDepth(), FrameSource)


def test_pipeline_with_fakes_runs_until_end_of_stream():
    src, dep, det, spa = ListSource(3), ConstDepth(), NoneDetector(), EmptySpatial()
    seen = []
    while (f := src.read()) is not None:
        assert spa.locate(f, dep.predict(f), det.predict(f)) == []
        seen.append(f.frame_id)
    assert seen == [0, 1, 2]


def test_clocks():
    assert isinstance(MonotonicClock(), Clock)
    c = ManualClock(10)
    assert isinstance(c, Clock)
    c.advance(5)
    assert c.now_ns() == 15
    with pytest.raises(ValueError):
        c.set(3)
