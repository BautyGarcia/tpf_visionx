"""Interfaces públicas entre módulos (docs/CONTRATOS.md, "Interfaces públicas").

Son Protocols: una clase cumple la interfaz si tiene estos métodos, sin heredar de nada.
Los módulos falsos (fakes) y los reales tienen exactamente la misma firma, así se pueden
intercambiar por configuración. Nadie importa funciones internas del área del otro.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from visionx.shared.contracts import AudioEvent, DepthResult, Detection, SpatialObject, StereoFrame


@runtime_checkable
class FrameSource(Protocol):
    """Fuente de pares estéreo: cámara USB, stream de la Pi o grabación (área B).

    read() devuelve None solo al terminar normalmente una grabación. Un fallo de dispositivo
    lanza SourceError.
    """

    def read(self) -> StereoFrame | None: ...

    def close(self) -> None: ...


@runtime_checkable
class DepthEstimator(Protocol):
    """Método de profundidad: SGBM, B4, Fusion, Lite o FakeDepth (área A).

    Siempre devuelve un DepthResult con status (válido, parcial o no medible) y reason. Un
    fallo del algoritmo lanza EstimatorError.
    """

    model_id: str

    def predict(self, frame: StereoFrame) -> DepthResult: ...

    def close(self) -> None: ...


@runtime_checkable
class Detector(Protocol):
    """Detector y segmentador de objetos (área B).

    Cero objetos es una Detection vacía. Un fallo del modelo lanza EstimatorError.
    """

    model_id: str

    def predict(self, frame: StereoFrame) -> Detection: ...

    def close(self) -> None: ...


@runtime_checkable
class SpatialEstimator(Protocol):
    """Ubica cada objeto detectado: ángulos y distancia (área A).

    Rechaza con IdentityMismatch entradas de frames o geometrías distintas.
    """

    def locate(
        self, frame: StereoFrame, depth: DepthResult, detections: Detection
    ) -> Sequence[SpatialObject]: ...


@runtime_checkable
class AudioSink(Protocol):
    """Salida de audio (área B).

    cancel() descarta lo pendiente y corta lo que suena de ese pedido.
    """

    def submit(self, event: AudioEvent) -> None: ...

    def cancel(self, request_id: int) -> None: ...

    def close(self) -> None: ...
