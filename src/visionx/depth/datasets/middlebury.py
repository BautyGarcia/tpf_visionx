"""Lector del formato Middlebury, que usan MiddEval3 y ETH3D two-view.

Cada par vive en una carpeta con:
    im0.png, im1.png   ojo izquierdo y derecho, ya rectificados
    disp0GT.pfm        disparidad GT del ojo izquierdo, en píxeles; infinito = sin GT
    mask0nocc.png      0 = sin GT, 128 = GT pero ocluido en el derecho, 255 = visible en ambos
    calib.txt          cam0/cam1 = [f 0 cx; 0 f cy; 0 0 1], doffs (px), baseline (mm), ...

Lo comprobamos en los archivos descargados (BITACORA 2026-11-13): los 0 de la máscara
coinciden exactamente con los infinitos del PFM. ETH3D guarda imágenes en grises como
tres canales iguales.

Z = baseline * f / (d + doffs). Middlebury da el baseline en milímetros: lo pasamos a metros
para usar la misma StereoGeometry que la ELP.
"""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from visionx.depth.datasets.pfm import read_pfm
from visionx.depth.datasets.sample import StereoSample
from visionx.shared.errors import InvalidInput
from visionx.shared.geometry import StereoGeometry

MASK_NO_GT, MASK_OCCLUDED, MASK_VISIBLE = 0, 128, 255
FILES = ("im0.png", "im1.png", "disp0GT.pfm", "mask0nocc.png", "calib.txt")


def read_calib(path: str | Path) -> dict[str, object]:
    """calib.txt a diccionario: matrices como arrays 3x3, el resto como float."""
    values: dict[str, object] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, raw = (part.strip() for part in line.split("=", 1))
        if raw.startswith("["):
            rows = raw.strip("[]").split(";")
            values[key] = np.array([[float(x) for x in r.split()] for r in rows], np.float64)
        else:
            values[key] = float(raw)
    for key in ("cam0", "cam1", "doffs", "baseline", "width", "height"):
        if key not in values:
            raise InvalidInput(f"{path}: falta {key}")
    return values


def geometry_from_calib(calib: dict[str, object]) -> StereoGeometry:
    cam0, cam1 = calib["cam0"], calib["cam1"]
    doffs = float(calib["doffs"])
    # Control de coherencia: doffs es la diferencia de centros ópticos de los dos ojos.
    if not math.isclose(doffs, cam1[0, 2] - cam0[0, 2], abs_tol=0.01):
        raise InvalidInput(f"doffs {doffs} no coincide con cx1 - cx0 = {cam1[0, 2] - cam0[0, 2]}")
    return StereoGeometry(
        width=int(calib["width"]),
        height=int(calib["height"]),
        fx=float(cam0[0, 0]),
        fy=float(cam0[1, 1]),
        cx=float(cam0[0, 2]),
        cy=float(cam0[1, 2]),
        baseline_m=float(calib["baseline"]) / 1000.0,  # mm -> m
        doffs=doffs,
    )


def _read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)  # siempre 3 canales BGR uint8
    if image is None:
        raise InvalidInput(f"no se pudo leer {path}")
    return image


def load_folder(
    folder: str | Path, dataset: str, sample_id: str, scene_id: str, root: str | Path
) -> StereoSample:
    """Lee una carpeta en formato Middlebury. `root` sirve para guardar rutas relativas."""
    folder, root = Path(folder), Path(root)
    left = _read_image(folder / "im0.png")
    right = _read_image(folder / "im1.png")
    raw = read_pfm(folder / "disp0GT.pfm")
    mask = cv2.imread(str(folder / "mask0nocc.png"), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise InvalidInput(f"no se pudo leer {folder / 'mask0nocc.png'}")
    unknown = set(np.unique(mask).tolist()) - {MASK_NO_GT, MASK_OCCLUDED, MASK_VISIBLE}
    if unknown:
        raise InvalidInput(f"{folder}: valores de máscara inesperados {sorted(unknown)}")
    valid = np.isfinite(raw)
    if not np.array_equal(valid, mask != MASK_NO_GT):
        raise InvalidInput(f"{folder}: la máscara y los infinitos del PFM no coinciden")
    disparity = np.where(valid, raw, np.nan).astype(np.float32)
    gray = bool(
        np.array_equal(left[..., 0], left[..., 1]) and np.array_equal(left[..., 1], left[..., 2])
    )
    return StereoSample(
        dataset=dataset,
        sample_id=sample_id,
        scene_id=scene_id,
        left=left,
        right=right,
        disparity=disparity,
        valid=valid,
        nonoccluded=mask == MASK_VISIBLE,
        geometry=geometry_from_calib(read_calib(folder / "calib.txt")),
        grayscale=gray,
        files=tuple((folder / n).relative_to(root).as_posix() for n in FILES),
    )
