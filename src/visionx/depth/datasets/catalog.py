"""Catálogo de datasets públicos: de dónde se bajan, con qué hash, licencia y cómo se leen.

Los hashes se fijaron con la primera descarga (13/11/2026): las fuentes no publican sumas
de verificación. Si una descarga posterior da otro hash, el archivo cambió en el servidor
o llegó roto, y no se usa sin revisar.

Roles (TECNICO T04, decidido 13/11):
- middeval3: test público principal. Entrenamiento de MiddEval3 a media resolución (H),
  15 pares con GT; es el protocolo de FoundationStereo (bad-2 en píxeles visibles).
- eth3d: test público secundario. Imágenes en grises replicadas a 3 canales.
- instereo2k: entrenamiento y validación. Se baja a mano (OneDrive no deja bajar por
  script); `descargar` controla el hash de los zip y los extrae.

Cada dataset se describe con un **índice liviano** (SampleRef: id, escena, archivos) y se
carga muestra por muestra. InStereo2K tiene ~2000 pares: cargarlos juntos ocuparía GB.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from visionx.depth.datasets import instereo2k, middlebury
from visionx.depth.datasets.sample import StereoSample
from visionx.depth.datasets.splits import check_no_leak, split_scenes

SPLIT_SEED = "visionx-T04"  # fija la partición train/val; cambiarla es cambiar el protocolo
VAL_FRACTION = 0.10


@dataclass(frozen=True)
class Download:
    """Archivo comprimido con su hash. `url` vacía = se baja a mano y se deja en
    data/descargas/<dataset>/<name>; `extract_to` es la subcarpeta de data/raw/<dataset>/."""

    url: str
    sha256: str
    bytes: int
    name: str = ""  # por defecto, el final de la url
    extract_to: str = ""

    @property
    def filename(self) -> str:
        return self.name or self.url.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class SampleRef:
    """Una muestra sin cargar: lo necesario para particionar, hashear y leerla después."""

    sample_id: str
    scene_id: str
    group: str  # grupo oficial del dataset: "training", "train", "test"
    files: tuple[str, ...]  # rutas relativas a la raíz extraída
    load: Callable[[], StereoSample] = field(compare=False, repr=False)


@dataclass(frozen=True)
class DatasetInfo:
    name: str
    role: str
    license: str
    citation: str
    source: str
    downloads: tuple[Download, ...]
    index: Callable[[Path], list[SampleRef]]  # recibe la carpeta raíz extraída
    gt_rules: tuple[str, ...]
    partition: Callable[[list[SampleRef]], dict[str, list[str]]]  # grupo -> escenas
    notes: tuple[str, ...] = ()
    manual_download: str = ""  # instrucciones si no se puede bajar por script


def _all_test(refs: list[SampleRef]) -> dict[str, list[str]]:
    """Dataset de evaluación: todas sus escenas son test; no entrena ni elige nada."""
    return {"test": sorted({r.scene_id for r in refs})}


# --- MiddEval3 y ETH3D (formato Middlebury) --------------------------------------------------

MIDDLEBURY_RULES = (
    "disparidad en px, d = x_izq - x_der; infinito del PFM = sin GT (NaN en StereoSample)",
    "máscara: 0 sin GT, 128 ocluido, 255 visible en ambos; métricas noc usan 255",
    "metros: Z = fx * baseline / (d + doffs), baseline de calib.txt en mm -> m",
)

# Variantes de la misma escena (otra exposición/iluminación) comparten escena: no son
# evidencia independiente. ArtL viene de la escena Art de 2005.
_MIDDEVAL3_SCENE = {"MotorcycleE": "Motorcycle", "PianoL": "Piano", "PlaytableP": "Playtable",
                    "ArtL": "Art"}  # fmt: skip


def _middlebury_refs(
    folders: list[Path], dataset: str, group: str, scene_of: Callable[[str], str], root: Path
) -> list[SampleRef]:
    refs = []
    for folder in folders:
        scene = scene_of(folder.name)
        files = tuple((folder / n).relative_to(root).as_posix() for n in middlebury.FILES)
        load = lambda f=folder, s=scene: middlebury.load_folder(f, dataset, f.name, s, root)  # noqa: E731
        refs.append(SampleRef(folder.name, scene, group, files, load))
    return refs


def _middeval3(root: Path) -> list[SampleRef]:
    base = root / "MiddEval3" / "trainingH"
    folders = sorted(p for p in base.iterdir() if p.is_dir())
    return _middlebury_refs(folders, "middeval3", "training",
                            lambda n: _MIDDEVAL3_SCENE.get(n, n), root)  # fmt: skip


def _eth3d(root: Path) -> list[SampleRef]:
    folders = sorted(p for p in root.iterdir() if p.is_dir())
    # delivery_area_1l / delivery_area_1s: mismo lugar, otro punto de vista o lente.
    return _middlebury_refs(folders, "eth3d", "training",
                            lambda n: re.sub(r"_\d+[ls]$", "", n), root)  # fmt: skip


# --- InStereo2K -----------------------------------------------------------------------------


def _instereo2k(root: Path) -> list[SampleRef]:
    base = instereo2k.find_base(root)
    refs = []
    for group, folder in instereo2k.frame_folders(base):
        sample_id = folder.name  # número de cuadro, único entre train y test
        scene = instereo2k.block_of(instereo2k.frame_number(folder))
        files = tuple((folder / n).relative_to(root).as_posix() for n in instereo2k.FILES)
        load = lambda f=folder, i=sample_id, s=scene: instereo2k.load_pair(f, i, s, root)  # noqa: E731
        refs.append(SampleRef(sample_id, scene, group, files, load))
    return refs


def _instereo2k_partition(refs: list[SampleRef]) -> dict[str, list[str]]:
    """Tramos -> train/val. El test oficial no forma grupo propio: sus cuadros están
    intercalados en los mismos tramos que train, así que siguen al tramo como cualquier otro.

    La partición se elige sobre todos los tramos del dataset (no solo los descargados) para
    que completar la descarga no mueva tramos de grupo; acá se listan los presentes.
    """
    train, val = split_scenes(instereo2k.all_blocks(), VAL_FRACTION, SPLIT_SEED)
    present = {r.scene_id for r in refs}
    groups = {"train": sorted(present & set(train)), "val": sorted(present & set(val))}
    check_no_leak(groups)
    return groups


CATALOG: dict[str, DatasetInfo] = {
    "middeval3": DatasetInfo(
        name="middeval3",
        role="test público principal",
        license="Sin licencia declarada en la página; uso académico citando el paper",
        citation="Scharstein et al., High-resolution stereo datasets with subpixel-accurate "
        "ground truth, GCPR 2014",
        source="https://vision.middlebury.edu/stereo/submit3/",
        downloads=(
            Download(
                "https://vision.middlebury.edu/stereo/submit3/zip/MiddEval3-data-H.zip",
                "2fc24f494a1e62066d0519cf86b759f344fc7bf0f49785632b582763fb0770a8",
                109900544,
            ),
            Download(
                "https://vision.middlebury.edu/stereo/submit3/zip/MiddEval3-GT0-H.zip",
                "c6537f6ee9debcf2a2ec605e69950b5feecb3c5df369f313bb22761acf74025c",
                53097428,
            ),
        ),
        index=_middeval3,
        gt_rules=MIDDLEBURY_RULES,
        partition=_all_test,
        notes=(
            "Solo trainingH tiene GT; testH no se usa.",
            "Comparadores: no usar pesos entrenados con Middlebury (TECNICO T14).",
        ),
    ),
    "eth3d": DatasetInfo(
        name="eth3d",
        role="test público secundario",
        license="Sin licencia declarada en la página; uso académico citando el paper",
        citation="Schöps et al., A multi-view stereo benchmark with high-resolution images "
        "and multi-camera videos, CVPR 2017",
        source="https://www.eth3d.net/datasets",
        downloads=(
            Download(
                "https://www.eth3d.net/data/two_view_training.7z",
                "cb7683a01ba037759f30b5a4f561d302453e20f1f7095cbdc51c8564b218224b",
                14283045,
            ),
            Download(
                "https://www.eth3d.net/data/two_view_training_gt.7z",
                "e440f7ec4444dfd2af33a44495f325a3aed06762432e2419277596ba7dcb9b40",
                14863383,
            ),
        ),
        index=_eth3d,
        gt_rules=MIDDLEBURY_RULES,
        partition=_all_test,
        notes=("Imágenes en grises: DA V2 y Fusion las reciben replicadas a 3 canales.",),
    ),
    "instereo2k": DatasetInfo(
        name="instereo2k",
        role="entrenamiento y validación",
        license="Uso no comercial (investigación, docencia, publicaciones), según el README",
        citation="Bao et al., InStereo2K: a large real dataset for stereo matching in indoor "
        "scenes, Science China Information Sciences 63, 212101, 2020",
        source="https://github.com/YuhuaXu/StereoDataset",
        # Hashes de la descarga manual del 13/11/2026. part1, part5 y part6 no están
        # disponibles (OneDrive: "This file cannot be downloaded"): trabajamos sin ellas.
        downloads=(
            Download(
                url="",
                name="part2.zip",
                extract_to="train",
                bytes=1777751123,
                sha256="9f21fcb1195a1467f1fa485f0310780f332d49ca5b618efab3828983d17e7302",
            ),
            Download(
                url="",
                name="part3.zip",
                extract_to="train",
                bytes=1773314372,
                sha256="64b46042f765504bb4f6f2cd4d01d32df1a7c34b73c2ca337fa1a8e27e65d678",
            ),
            Download(
                url="",
                name="part4.zip",
                extract_to="train",
                bytes=1782540810,
                sha256="2e7e5b9815904ec1a1c230cf9e67238012859415d34e63884540e4c0b6da3a68",
            ),
            Download(
                url="",
                name="test.zip",
                extract_to="",
                bytes=225603067,
                sha256="d68314e2869b850fdd6fec0118c4c15b7abbd62761bd4437d8eb3904dce780da",
            ),
        ),
        index=_instereo2k,
        gt_rules=(
            "disparidad en px = PNG uint16 / 100; 0 = sin GT (NaN en StereoSample)",
            "sin calibración publicada: sin metros",
        ),
        partition=_instereo2k_partition,
        notes=(
            "Escena = tramo de 100 cuadros consecutivos (los cuadros vecinos son el mismo "
            "armado); el dataset no publica escenas.",
            "El test oficial (cuadros 000040, 000080, ...) comparte tramos con train: no es "
            "independiente y no se usa como test.",
            "Subconjunto disponible: part2-4 y test, 1221 de 2050 pares. part1, part5 y part6 "
            "no se pueden bajar de OneDrive (13/11/2026).",
            "Comparadores FoundationStereo/FFS entrenaron con InStereo2K: no es test.",
        ),
        manual_download=(
            "Los links de OneDrive del README (https://github.com/YuhuaXu/StereoDataset) no se "
            "pueden bajar por script. Bajar a mano los zip (partN.zip y test.zip), dejarlos en "
            "data/descargas/instereo2k/ y correr `descargar instereo2k`: controla el hash y "
            "los extrae."
        ),
    ),
}
