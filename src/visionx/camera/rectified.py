"""Rectificar los pares de cualquier fuente (cámara en vivo o replay) con una calibración.

Es el único lugar donde la captura aplica la calibración: los pares quedan con
rectified=True, calibration_id y geometry_id, y quien los consume (profundidad, detector)
puede comprobar que todos hablan de la misma geometría.
"""

from __future__ import annotations

import dataclasses

from visionx.calibration import StereoCalibration
from visionx.shared.contracts import StereoFrame
from visionx.shared.errors import InvalidInput
from visionx.shared.geometry import StereoGeometry
from visionx.shared.interfaces import FrameSource


class RectifiedSource:
    """FrameSource que envuelve a otra y entrega sus pares rectificados."""

    def __init__(self, source: FrameSource, calibration: StereoCalibration) -> None:
        self._source = source
        self.calibration = calibration
        # La geometría incluye la corrección de disparidad de la calibración (PR #14).
        self.geometry: StereoGeometry = calibration.geometry()
        # Los mapas de remapeo se calculan una sola vez: son caros y no cambian.
        self._maps = calibration.rectify_maps()

    def read(self) -> StereoFrame | None:
        frame = self._source.read()
        if frame is None:
            return None
        if frame.rectified:
            raise InvalidInput(f"el frame {frame.frame_id} ya viene rectificado")
        if frame.size != tuple(self.calibration.image_size):
            w, h = self.calibration.image_size
            raise InvalidInput(
                f"el par mide {frame.size[0]}x{frame.size[1]} por ojo y la calibración "
                f"{self.calibration.calibration_id} es de {w}x{h}: no corresponde a este modo"
            )
        left, right = self.calibration.rectify(frame.left, frame.right, self._maps)
        return dataclasses.replace(
            frame,
            left=left,
            right=right,
            rectified=True,
            calibration_id=self.calibration.calibration_id,
            geometry_id=self.geometry.geometry_id,
        )

    def close(self) -> None:
        self._source.close()
