"""Auditoría de muestras (TECNICO T04: diez muestras por adaptador).

Además de mirar rangos, comprobamos que la GT esté bien leída sin confiar en el README:
si la disparidad es correcta, el píxel (x, y) de la izquierda se ve igual que el píxel
(x - d, y) de la derecha. Probamos la GT corrida de -3 a +3 px: el parecido tiene que ser
máximo (el error mínimo) exactamente sin corrimiento. Si la escala está mal (p. ej. falta el
/100 de InStereo2K), el signo está invertido o las filas están dadas vuelta, el mínimo se
corre o desaparece.

Cómo medimos el parecido (aprendido al auditar, BITACORA 2026-11-13):
- **Census** en vez de restar brillos: cada píxel se describe por qué vecinos son más
  oscuros que él. No cambia si un ojo tiene otra exposición o iluminación, como las
  variantes E/L de Middlebury, que con la resta de brillo parecían "GT desalineada".
- **Solo píxeles con textura** (mitad con mayor gradiente horizontal): en una pared lisa
  correr 2 px no cambia nada y diluye la prueba.
- No se exige un parecido mínimo absoluto: en texturas finas (pasto, grava de ETH3D) la
  curva es chata pero su mínimo sigue en 0. Sí se exige que baje respecto de ±3 px.

Veredicto por muestra (ajustado con las 1221 de InStereo2K, BITACORA 2026-11-13):
- **alineada:** curva marcada y mínimo a no más de un paso (0,5 px) de 0. El mínimo real
  suele caer entre dos pasos: en InStereo2K, 24 muestras tenían el mínimo discreto en ±0,5
  con un corrimiento subpíxel de 0,25–0,32 px, no una lectura errónea.
- **no concluyente:** curva plana (pared lisa, pizarrón), mínimo en 0 pero con un extremo casi
  igual (textura periódica, como listones de madera) o pocos píxeles. No prueba nada; en los
  7 casos de InStereo2K verificamos la GT a mano en esquinas y coincidía.
- **desalineada:** curva marcada con el mínimo lejos de 0.
Veredicto del dataset (`dataset_verdict`): ninguna desalineada, no concluyentes <= 5 % y
corrimiento subpíxel mediano <= 0,25 px. Una escala o un signo mal leídos afectan a todas
las muestras: vuelven planas las curvas o corren el mínimo en todas, y eso salta acá.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from visionx.depth.datasets.sample import StereoSample

SHIFTS_PX = tuple(np.round(np.arange(-3.0, 3.01, 0.5), 1).tolist())  # barrido de control
CENSUS_RADIUS = 2  # ventana 5 x 5: 24 comparaciones por píxel
# Con una GT sin relación con las imágenes la curva es plana (cociente ~1) y el mínimo cae
# en cualquier lado, también en 0 por azar. Exigimos una caída real. Las GT reales más
# chatas que vimos (texturas finas de ETH3D) dan ~0,87.
MAX_RATIO = 0.95
# Con pocos píxeles el ruido puede fabricar una caída. Las muestras reales usan 10^5 o más.
MIN_PIXELS = 10_000
STEP_PX = 0.5  # paso del barrido: tolerancia del mínimo discreto
MAX_INCONCLUSIVE = 0.05  # fracción tolerada de muestras sin textura suficiente
MAX_MEDIAN_OFFSET_PX = 0.25  # corrimiento subpíxel mediano tolerado en un dataset


def census(gray: np.ndarray, radius: int = CENSUS_RADIUS) -> np.ndarray:
    """H x W x K bool: para cada vecino, si es más oscuro que el píxel central."""
    h, w = gray.shape
    p = np.pad(gray, radius, mode="edge")
    bits = [
        p[radius + dy : radius + dy + h, radius + dx : radius + dx + w] < gray
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if dy or dx
    ]
    return np.stack(bits, axis=-1)


def alignment_curve(
    sample: StereoSample, shifts: tuple[float, ...] = SHIFTS_PX
) -> tuple[list[float], int]:
    """Error census (fracción de bits distintos, 0–1) para la GT corrida cada `shift` px.

    Usa píxeles visibles en ambos ojos (nonoccluded, o valid si el dataset no la da) y con
    textura. Devuelve (errores en el orden de `shifts`, píxeles usados sin corrimiento).
    """
    left = cv2.cvtColor(sample.left, cv2.COLOR_BGR2GRAY).astype(np.float32)
    right = cv2.cvtColor(sample.right, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mask = sample.nonoccluded if sample.nonoccluded is not None else sample.valid
    if not mask.any():
        return [float("nan")] * len(shifts), 0
    grad = np.abs(cv2.Sobel(left, cv2.CV_32F, 1, 0, ksize=3))
    textured = mask & (grad > np.percentile(grad[mask], 50))
    ys, xs = np.nonzero(textured)
    cl, cr = census(left), census(right)
    w = left.shape[1]
    errors, used = [], 0
    for shift in shifts:
        # Columna correspondiente en el ojo derecho; vecino más cercano alcanza a 0,5 px.
        xr = np.rint(xs - (sample.disparity[ys, xs] + shift)).astype(np.int64)
        ok = (xr >= 0) & (xr < w)
        if shift == 0:
            used = int(ok.sum())
        n = int(ok.sum())
        errors.append(
            float((cl[ys[ok], xs[ok]] != cr[ys[ok], xr[ok]]).mean()) if n else float("nan")
        )
    return errors, used


def subpixel_minimum(errors: list[float], shifts: tuple[float, ...] = SHIFTS_PX) -> float | None:
    """Corrimiento del mínimo con precisión subpíxel: parábola por el mínimo y sus vecinos."""
    if not all(np.isfinite(errors)):
        return None
    i = int(np.argmin(errors))
    if i in (0, len(errors) - 1):
        return float(shifts[i])
    a, b, c = errors[i - 1], errors[i], errors[i + 1]
    curvature = a - 2 * b + c
    step = shifts[i + 1] - shifts[i]
    return float(shifts[i]) + (0.5 * step * (a - c) / curvature if curvature > 0 else 0.0)


def verdict(errors: list[float], n: int) -> str:
    """ "alineada", "no concluyente" o "desalineada" (ver docstring del módulo)."""
    zero = SHIFTS_PX.index(0.0)
    edges = min(errors[0], errors[-1])
    if n < MIN_PIXELS or not all(np.isfinite(errors)) or edges <= 0:
        return "no concluyente"
    if min(errors) / max(errors) >= MAX_RATIO:
        return "no concluyente"  # curva plana en todo el barrido: no hay con qué decidir
    best = SHIFTS_PX[int(np.argmin(errors))]
    if abs(best) > STEP_PX:
        return "desalineada"  # evidencia positiva: la GT corrida se parece más
    if errors[zero] / edges < MAX_RATIO:
        return "alineada"
    # Mínimo en 0 pero un extremo casi igual de bueno: textura periódica (listones) o de un
    # solo lado. No acusa a la GT ni la confirma.
    return "no concluyente"


def dataset_verdict(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Resumen de la auditoría de un dataset; `ok` decide el código de salida del CLI."""
    by = {"alineada": [], "no concluyente": [], "desalineada": []}
    for r in reports:
        by[r["fotometrico"]["veredicto"]].append(r["muestra"])
    offsets = [r["fotometrico"]["minimo_subpx"] for r in reports
               if r["fotometrico"]["veredicto"] == "alineada"]  # fmt: skip
    median = round(float(np.median(offsets)), 3) if offsets else None
    share = len(by["no concluyente"]) / len(reports) if reports else 1.0
    problems = []
    if by["desalineada"]:
        problems.append(f"{len(by['desalineada'])} desalineadas")
    if share > MAX_INCONCLUSIVE:
        problems.append(
            f"{100 * share:.1f} % no concluyentes (máx. {100 * MAX_INCONCLUSIVE:.0f} %)"
        )
    if median is None or abs(median) > MAX_MEDIAN_OFFSET_PX:
        problems.append(f"corrimiento mediano {median} px (máx. ±{MAX_MEDIAN_OFFSET_PX})")
    return {"ok": not problems, "problemas": problems, "alineadas": len(by["alineada"]),
            "no_concluyentes": by["no concluyente"], "desalineadas": by["desalineada"],
            "corrimiento_mediano_px": median}  # fmt: skip


def audit_sample(sample: StereoSample) -> dict[str, Any]:
    """Resumen numérico de una muestra, listo para guardar en YAML."""
    w, h = sample.size
    d = sample.disparity[sample.valid]
    errors, n = alignment_curve(sample)
    finite = [e for e in errors if np.isfinite(e)]
    zero = SHIFTS_PX.index(0.0)
    best = int(np.nanargmin(errors)) if finite else -1
    edges = min(errors[0], errors[-1])
    sub = subpixel_minimum(errors)
    result = verdict(errors, n)
    report: dict[str, Any] = {
        "muestra": sample.sample_id,
        "escena": sample.scene_id,
        "tamaño": [w, h],
        "grises": sample.grayscale,
        "gt_valida_pct": round(100 * float(sample.valid.mean()), 2),
        "no_ocluida_pct": None
        if sample.nonoccluded is None
        else round(100 * float(sample.nonoccluded.mean()), 2),
        "disparidad_px": {
            "min": round(float(d.min()), 3) if d.size else None,
            "p50": round(float(np.median(d)), 3) if d.size else None,
            "max": round(float(d.max()), 3) if d.size else None,
        },
        "fotometrico": {
            "metodo": "census 5x5, píxeles con textura, GT corrida -3..+3 px",
            "error_por_corrimiento": {
                f"{s:+.1f}": round(e, 4) for s, e in zip(SHIFTS_PX, errors, strict=True)
            },
            "pixeles": n,
            "minimo_en_px": SHIFTS_PX[best] if best >= 0 else None,
            "minimo_subpx": None if sub is None else round(sub, 3),
            # Error con la GT / error con la GT corrida 3 px: más bajo = curva más marcada.
            "cociente": round(errors[zero] / edges, 3) if n and edges > 0 else None,
            "veredicto": result,
            "gt_alineada": result == "alineada",
        },
    }
    if sample.geometry is not None:
        z, ok = sample.depth()
        zs = z[ok]
        report["geometria"] = {
            "fx": round(sample.geometry.fx, 3),
            "baseline_m": round(sample.geometry.baseline_m, 5),
            "doffs": round(sample.geometry.doffs, 3),
        }
        report["profundidad_m"] = {
            "min": round(float(zs.min()), 3),
            "p50": round(float(np.median(zs)), 3),
            "max": round(float(zs.max()), 3),
        }
    return report


def contact_sheet(sample: StereoSample, path: str | Path, width: int = 1600) -> Path:
    """Imagen para mirar a ojo: izquierda | derecha arriba, disparidad | máscara abajo."""
    d = sample.disparity
    finite = sample.valid
    lo, hi = np.percentile(d[finite], [1, 99]) if finite.any() else (0.0, 1.0)
    norm = np.clip((np.nan_to_num(d, nan=lo) - lo) / max(hi - lo, 1e-6), 0, 1)
    color = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    color[~finite] = 0  # sin GT: negro
    mask = np.zeros_like(sample.left)
    mask[sample.valid] = (128, 128, 128)  # GT ocluida: gris
    if sample.nonoccluded is not None:
        mask[sample.nonoccluded] = (255, 255, 255)  # GT visible en los dos ojos: blanco
    sheet = np.vstack([np.hstack([sample.left, sample.right]), np.hstack([color, mask])])
    scale = width / sheet.shape[1]
    sheet = cv2.resize(sheet, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), sheet)
    return path
