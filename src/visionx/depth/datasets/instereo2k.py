"""Lector de InStereo2K (entrenamiento y validación de Fusion, TECNICO T04).

Formato según el README oficial (https://github.com/YuhuaXu/StereoDataset):
- Disparidad en PNG de 16 bits, multiplicada por 100 y redondeada: d = valor / 100.
- 0 significa "sin GT" y se excluye. Ojo: torchvision divide por 1024; seguimos el README
  y la auditoría fotométrica lo confirmó con los archivos reales (BITACORA 2026-11-13).
- No publica focal ni baseline: estas muestras no tienen geometría ni metros.

Estructura real (vista al extraer los zip de OneDrive, 13/11/2026):
    <raíz>/train/part<N>/<cuadro>/{left.png, right.png, left_disp.png, right_disp.png}
    <raíz>/test/<cuadro>/...
`<cuadro>` es un número de 6 cifras único en todo el dataset (000001–002050). El test oficial
son cuadros sueltos intercalados (000040, 000080, ...) en la misma secuencia que train.

**Escenas.** Los cuadros consecutivos son la misma habitación con objetos movidos y la cámara
corrida un poco; el dataset no publica a qué escena pertenece cada cuadro. Agrupamos en
tramos de `FRAMES_PER_BLOCK` cuadros consecutivos: un armado dura ~5–30 cuadros, así que solo
los bordes de un tramo pueden parecerse al tramo vecino.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from visionx.depth.datasets.sample import StereoSample
from visionx.shared.errors import InvalidInput

FILES = ("left.png", "right.png", "left_disp.png")
DISPARITY_SCALE = 100.0  # README: valores x100 en uint16
FRAMES_PER_BLOCK = 100  # tramo = unidad de partición (ver docstring)
LAST_FRAME = 2050  # el paper publica 2050 pares; fija cuántos tramos existen


def load_pair(folder: Path, sample_id: str, scene_id: str, root: Path) -> StereoSample:
    left = cv2.imread(str(folder / "left.png"), cv2.IMREAD_COLOR)
    right = cv2.imread(str(folder / "right.png"), cv2.IMREAD_COLOR)
    raw = cv2.imread(str(folder / "left_disp.png"), cv2.IMREAD_UNCHANGED)
    if left is None or right is None or raw is None:
        raise InvalidInput(f"{folder}: falta left.png, right.png o left_disp.png")
    if raw.dtype != np.uint16 or raw.ndim != 2:
        raise InvalidInput(f"{folder}: left_disp.png tiene que ser gris de 16 bits, es {raw.dtype}")
    valid = raw > 0
    disparity = np.full(raw.shape, np.nan, np.float32)
    disparity[valid] = raw[valid].astype(np.float32) / DISPARITY_SCALE
    return StereoSample(
        dataset="instereo2k",
        sample_id=sample_id,
        scene_id=scene_id,
        left=left,
        right=right,
        disparity=disparity,
        valid=valid,
        files=tuple((folder / n).relative_to(root).as_posix() for n in FILES),
    )


def frame_number(folder: Path) -> int:
    if not folder.name.isdigit():
        raise InvalidInput(f"{folder}: esperaba una carpeta con número de cuadro")
    return int(folder.name)


def block_of(frame: int) -> str:
    """Tramo de un cuadro: 000001–000100 -> tramo-00, 000101–000200 -> tramo-01, ..."""
    if not 1 <= frame <= LAST_FRAME:
        raise InvalidInput(f"cuadro {frame} fuera de 1–{LAST_FRAME}")
    return f"tramo-{(frame - 1) // FRAMES_PER_BLOCK:02d}"


def all_blocks() -> list[str]:
    """Todos los tramos del dataset completo, estén o no descargados.

    La partición se calcula sobre esta lista fija: bajar una parte que faltaba no cambia
    a qué grupo va un tramo que ya estaba.
    """
    return sorted({block_of(f) for f in range(1, LAST_FRAME + 1)})


def frame_folders(base: Path) -> list[tuple[str, Path]]:
    """(grupo oficial, carpeta) de cada cuadro, en orden de cuadro."""
    found = [("train", p) for p in base.glob("train/part*/*") if p.is_dir()]
    found += [("test", p) for p in base.glob("test/*") if p.is_dir()]
    found.sort(key=lambda gp: frame_number(gp[1]))
    numbers = [frame_number(p) for _, p in found]
    if len(set(numbers)) != len(numbers):
        raise InvalidInput(f"{base}: hay números de cuadro repetidos entre carpetas")
    return found


def find_base(root: Path) -> Path:
    """Carpeta que contiene train/ y test/, esté donde esté dentro de lo extraído."""
    for candidate in [root, *sorted(p for p in root.rglob("train") if p.is_dir())]:
        base = candidate if (candidate / "train").is_dir() else candidate.parent
        if (base / "train").is_dir() and (base / "test").is_dir():
            return base
    raise InvalidInput(f"{root}: no encontré las carpetas train/ y test/ de InStereo2K")
