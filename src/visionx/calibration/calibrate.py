"""Calibración estéreo robusta: limpiar fotos malas, ajustar y elegir con validación.

Recorrido, para cada modelo de lente:

1. Calibrar cada ojo por separado con las fotos de ajuste.
2. Calibrar el par con esos intrínsecos fijos (solo R y T).
3. Medir cada foto. Una foto se descarta si su error se aleja mucho del resto, y se
   registra el motivo:
   - error alto en un solo ojo: esquinas mal detectadas en esa imagen;
   - cada ojo bien pero el par mal: el tablero se movió entre las dos capturas
     (los dos sensores no exponen exactamente en el mismo instante);
   - tablero demasiado inclinado: los cuadrados se aplastan y las esquinas pierden precisión.
4. Repetir hasta que no haya más descartes (con un tope de fotos descartadas).
5. Ajuste final de dos maneras: intrínsecos fijos, o todo junto partiendo de ellos.

Al final se elige el candidato con menor error vertical en las **fotos de validación**,
que nunca participan del ajuste ni de la limpieza. Entre candidatos casi empatados se prefiere el
más simple. Así un modelo con más coeficientes solo gana si de verdad generaliza mejor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from visionx.calibration import models as m
from visionx.calibration.board import Checkerboard
from visionx.calibration.models import Intrinsics, LensModel, Rectification
from visionx.calibration.sessions import PairView, Session
from visionx.shared.errors import InvalidInput

# Complejidad para desempatar: menos coeficientes primero.
_COMPLEXITY = {LensModel.FISHEYE: 4, LensModel.PINHOLE5: 5, LensModel.RATIONAL: 8}


@dataclass(frozen=True, slots=True)
class CalibrationOptions:
    models: tuple[LensModel, ...] = (LensModel.PINHOLE5, LensModel.RATIONAL, LensModel.FISHEYE)
    alpha: float = 0.0  # rectificación: 0 = solo píxeles válidos, 1 = imagen completa
    outlier_sigma: float = 4.0  # cuántas desviaciones robustas por encima de la mediana
    outlier_floor_px: float = 0.75  # nunca descartar una foto con error menor a esto
    max_rejected_fraction: float = 0.30  # tope de fotos descartadas por limpieza
    max_tilt_deg: float = 65.0  # más inclinado que esto, las esquinas pierden precisión
    min_views: int = 12  # mínimo de pares para calibrar
    validation_every: int = 5  # sin sesión de validación: 1 de cada N pares a validación
    tie_tolerance: float = 0.02  # 2 %: dentro de esto, preferir el modelo más simple


@dataclass(frozen=True, slots=True)
class ViewReport:
    """Diagnóstico de una foto con la calibración elegida."""

    key: str
    role: str  # "ajuste", "validación" o "descartada"
    tilt_deg: float  # inclinación del tablero respecto del eje óptico
    distance_m: float  # distancia cámara izquierda - tablero
    left_px: float  # error de reproyección RMS en el ojo izquierdo
    right_px: float
    transfer_px: float  # error al pasar la pose de un ojo al otro con R, T
    vertical_px: float  # mediana de |fila izq - fila der| tras rectificar
    scale_error: float  # lado del cuadrado triangulado / nominal - 1
    reason: str = ""  # motivo del descarte, si corresponde


@dataclass(slots=True)
class Candidate:
    model: LensModel
    refine: bool  # True: intrínsecos reajustados junto con R, T
    fit_rms_px: float = math.nan
    left: Intrinsics | None = None
    right: Intrinsics | None = None
    R: np.ndarray | None = None
    T: np.ndarray | None = None
    rect: Rectification | None = None
    fit_keys: list[str] = field(default_factory=list)
    rejected: dict[str, str] = field(default_factory=dict)  # clave -> motivo
    validation: dict[str, float] = field(default_factory=dict)
    moved_validation: list[str] = field(default_factory=list)  # validación que parece movida
    error: str = ""  # si OpenCV no pudo calibrar este modelo

    @property
    def name(self) -> str:
        return f"{self.model.value}{'+refinado' if self.refine else ''}"

    @property
    def baseline_m(self) -> float:
        return float(np.linalg.norm(self.T)) if self.T is not None else math.nan


@dataclass(slots=True)
class CalibrationRun:
    board: Checkerboard
    image_size: tuple[int, int]
    selected: Candidate
    candidates: list[Candidate]
    fit_keys: list[str]
    validation_keys: list[str]
    views: list[ViewReport]
    warnings: list[str]
    stability: list[dict]  # calibración por sesión para medir estabilidad


# --- División ajuste / validación ---------------------------------------------------------


def split_views(
    fit_sessions: list[Session], validation_sessions: list[Session], every: int
) -> tuple[list[PairView], list[PairView]]:
    """Con sesiones de validación explícitas, se usan enteras. Si no, 1 de cada `every`.

    La elección es determinística (por posición), nunca por el error de la foto: elegir
    las fotos de validación mirando el resultado sería hacer trampa.
    """
    if validation_sessions:
        fit = [v for s in fit_sessions for v in s.views]
        val = [v for s in validation_sessions for v in s.views]
        return fit, val
    if every < 2:
        raise InvalidInput("validation_every tiene que ser >= 2")
    fit, val = [], []
    for session in fit_sessions:
        for position, view in enumerate(session.views):
            (val if position % every == every // 2 else fit).append(view)
    return fit, val


def _short_error(exc: Exception) -> str:
    """Mensaje de OpenCV sin la ruta del archivo C++: solo la condición que falló."""
    text = str(exc).strip().splitlines()[-1]
    if "error:" in text:
        text = text.split("error:", 1)[1].strip()
    return text[:160]


# --- Errores por foto ---------------------------------------------------------------------


def _rms(diff: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.sum(np.square(diff), axis=1))))


def _robust_threshold(values: np.ndarray, sigma: float, floor: float) -> float:
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median))) * 1.4826  # equivale a 1 sigma
    return max(floor, median + sigma * mad)


def view_errors(
    model: LensModel,
    objp: np.ndarray,
    view: PairView,
    left: Intrinsics,
    right: Intrinsics,
    R: np.ndarray,
    T: np.ndarray,
) -> dict[str, float]:
    """Errores de una foto con una calibración dada. No reajusta nada."""
    rl, tl = m.board_pose(model, objp, view.left, left)
    rr, tr = m.board_pose(model, objp, view.right, right)
    err_left = _rms(m.project(model, objp, rl, tl, left) - view.left)
    err_right = _rms(m.project(model, objp, rr, tr, right) - view.right)
    # Transferencia: la pose vista por un ojo, llevada al otro con R y T, tiene que caer
    # sobre las esquinas que ese otro ojo vio. Mide la geometría estéreo completa.
    Rl, _ = cv2.Rodrigues(rl)
    Rr, _ = cv2.Rodrigues(rr)
    to_right = m.project(model, objp, cv2.Rodrigues(R @ Rl)[0], R @ tl + T, right)
    to_left = m.project(model, objp, cv2.Rodrigues(R.T @ Rr)[0], R.T @ (tr - T), left)
    transfer = math.sqrt((_rms(to_right - view.right) ** 2 + _rms(to_left - view.left) ** 2) / 2)
    normal_z = abs(float(Rl[2, 2]))  # componente del eje del tablero sobre el eje óptico
    return {
        "left": err_left,
        "right": err_right,
        "transfer": transfer,
        "tilt": math.degrees(math.acos(min(1.0, normal_z))),
        "distance": float(np.linalg.norm(tl)),
    }


def rectified_errors(
    model: LensModel,
    board: Checkerboard,
    view: PairView,
    left: Intrinsics,
    right: Intrinsics,
    rect: Rectification,
) -> tuple[np.ndarray, float]:
    """(|fila izq - fila der| por esquina, error relativo de escala) tras rectificar."""
    pl = m.undistort_points(model, view.left, left, rect.R1, rect.P1)
    pr = m.undistort_points(model, view.right, right, rect.R2, rect.P2)
    vertical = np.abs(pl[:, 1] - pr[:, 1])
    X = cv2.triangulatePoints(rect.P1, rect.P2, pl.T, pr.T)
    X = (X[:3] / X[3]).T
    return vertical, similarity_scale(board.object_points().astype(np.float64), X) - 1


def similarity_scale(reference: np.ndarray, measured: np.ndarray) -> float:
    """Escala que mejor superpone `measured` sobre `reference` (método de Umeyama).

    Se ajusta el tablero entero (rotación + traslación + escala) en vez de medir el lado
    de cada cuadrado. Con 28 mm entre vecinos, el ruido de profundidad de cada punto
    siempre alarga en promedio esa distancia corta (sesgo positivo); el ajuste global usa
    la covarianza cruzada, en la que ese ruido no suma sesgo.
    """
    # Umeyama: measured ~ s * R @ reference + t. Con Σ = cov(measured, reference) = U D Vᵀ,
    # la escala es traza(D·signo) / var(reference).
    ref = reference - reference.mean(axis=0)
    mea = measured - measured.mean(axis=0)
    U, D, Vt = np.linalg.svd(mea.T @ ref / len(ref))
    sign = np.ones(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        sign[-1] = -1  # evitar que el mejor ajuste sea una reflexión
    variance_reference = float(np.mean(np.sum(ref**2, axis=1)))
    return float(np.sum(D * sign)) / variance_reference


# --- Ajuste de un modelo ------------------------------------------------------------------


def _fit(
    model: LensModel, objp: np.ndarray, views: list[PairView], size: tuple[int, int]
) -> tuple[Intrinsics, Intrinsics, float, np.ndarray, np.ndarray]:
    objects = [objp] * len(views)
    lefts = [v.left for v in views]
    rights = [v.right for v in views]
    intr_l, _, _ = m.calibrate_mono(model, objects, lefts, size)
    intr_r, _, _ = m.calibrate_mono(model, objects, rights, size)
    rms, intr_l, intr_r, R, T = m.calibrate_stereo(
        model, objects, lefts, rights, intr_l, intr_r, size, refine_intrinsics=False
    )
    return intr_l, intr_r, rms, R, T


def _clean(
    model: LensModel,
    objp: np.ndarray,
    views: list[PairView],
    size: tuple[int, int],
    opt: CalibrationOptions,
) -> tuple[list[PairView], dict[str, str]]:
    """Descarta fotos atípicas en rondas, registrando el motivo de cada una."""
    active = list(views)
    rejected: dict[str, str] = {}
    budget = int(opt.max_rejected_fraction * len(views))
    for _ in range(10):
        if len(active) < opt.min_views:
            break
        intr_l, intr_r, _, R, T = _fit(model, objp, active, size)
        errors = [view_errors(model, objp, v, intr_l, intr_r, R, T) for v in active]
        arr = {k: np.array([e[k] for e in errors]) for k in ("left", "right", "transfer")}
        thr = {k: _robust_threshold(arr[k], opt.outlier_sigma, opt.outlier_floor_px) for k in arr}
        flagged: list[tuple[float, PairView, str]] = []
        for view, e in zip(active, errors, strict=True):
            if e["tilt"] > opt.max_tilt_deg:
                flagged.append((math.inf, view, f"tablero inclinado {e['tilt']:.0f}°"))
            elif e["left"] > thr["left"]:
                reason = f"ojo izquierdo {e['left']:.2f} px (umbral {thr['left']:.2f})"
                flagged.append((e["left"] / thr["left"], view, reason))
            elif e["right"] > thr["right"]:
                reason = f"ojo derecho {e['right']:.2f} px (umbral {thr['right']:.2f})"
                flagged.append((e["right"] / thr["right"], view, reason))
            elif e["transfer"] > thr["transfer"]:
                reason = (
                    f"movimiento entre ojos: transferencia {e['transfer']:.2f} px "
                    f"(umbral {thr['transfer']:.2f}) con cada ojo bien"
                )
                flagged.append((e["transfer"] / thr["transfer"], view, reason))
        if not flagged:
            break
        flagged.sort(key=lambda item: -item[0])  # primero las peores
        room = budget - len(rejected)
        if room <= 0:
            break
        for _, view, reason in flagged[:room]:
            rejected[view.key] = reason
        active = [v for v in active if v.key not in rejected]
    return active, rejected


def _validate(
    cand: Candidate,
    board: Checkerboard,
    objp: np.ndarray,
    val: list[PairView],
    motion_px: float,
) -> dict[str, float]:
    """Métricas sobre fotos que no participaron del ajuste.

    Las fotos de validación no se limpian (sería elegir el examen mirando las respuestas).
    Pero una foto movida no mide la calibración sino el movimiento: se informa aparte
    cuáles parecen movidas (cada ojo bien, el par mal) y las métricas sin ellas.
    La elección usa la mediana por foto, que unas pocas fotos movidas no arrastran.
    """
    per_view = []
    for view in val:
        e = view_errors(cand.model, objp, view, cand.left, cand.right, cand.R, cand.T)
        v, s = rectified_errors(cand.model, board, view, cand.left, cand.right, cand.rect)
        moved = e["transfer"] > motion_px and max(e["left"], e["right"]) < motion_px
        per_view.append((view.key, e["transfer"], v, s, moved))

    def stats(rows: list) -> dict[str, float]:
        if not rows:
            return {}
        allv = np.concatenate([r[2] for r in rows])
        transfer = np.array([r[1] for r in rows])
        return {
            "transfer_median_px": float(np.median(transfer)),
            "transfer_rms_px": float(math.sqrt(np.mean(transfer**2))),
            "vertical_median_px": float(np.median(allv)),
            "vertical_p95_px": float(np.percentile(allv, 95)),
            "scale_error_median": float(np.median([r[3] for r in rows])),
        }

    out = {"n": float(len(per_view)), **stats(per_view)}
    clean = [r for r in per_view if not r[4]]
    out["n_moved"] = float(len(per_view) - len(clean))
    if out["n_moved"]:
        out.update({f"clean_{k}": v for k, v in stats(clean).items()})
    cand.moved_validation = [r[0] for r in per_view if r[4]]
    return out


def _calibrate_model(
    model: LensModel,
    board: Checkerboard,
    fit: list[PairView],
    val: list[PairView],
    size: tuple[int, int],
    opt: CalibrationOptions,
) -> list[Candidate]:
    objp = board.object_points()
    try:
        active, rejected = _clean(model, objp, fit, size, opt)
        if len(active) < opt.min_views:
            raise InvalidInput(f"quedan {len(active)} pares, mínimo {opt.min_views}")
        intr_l, intr_r, _, _, _ = _fit(model, objp, active, size)
    except (cv2.error, InvalidInput) as exc:
        return [Candidate(model, False, error=_short_error(exc))]

    out = []
    objects = [objp] * len(active)
    for refine in (False, True):
        cand = Candidate(model, refine, rejected=dict(rejected))
        cand.fit_keys = [v.key for v in active]
        try:
            rms, left, right, R, T = m.calibrate_stereo(
                model, objects, [v.left for v in active], [v.right for v in active],
                intr_l, intr_r, size, refine_intrinsics=refine,
            )  # fmt: skip
            cand.fit_rms_px, cand.left, cand.right, cand.R, cand.T = rms, left, right, R, T
            cand.rect = m.rectify(model, left, right, size, R, T, opt.alpha)
            if val:
                fit_transfer = np.array(
                    [view_errors(model, objp, v, left, right, R, T)["transfer"] for v in active]
                )
                motion_px = _robust_threshold(fit_transfer, opt.outlier_sigma, opt.outlier_floor_px)
                cand.validation = _validate(cand, board, objp, val, motion_px)
        except cv2.error as exc:
            cand.error = _short_error(exc)
        out.append(cand)
    return out


# --- Recorrido completo -------------------------------------------------------------------


def calibrate(
    fit_sessions: list[Session],
    board: Checkerboard,
    validation_sessions: list[Session] | None = None,
    options: CalibrationOptions | None = None,
) -> CalibrationRun:
    opt = options or CalibrationOptions()
    validation_sessions = validation_sessions or []
    fit, val = split_views(fit_sessions, validation_sessions, opt.validation_every)
    sizes = {v.image_size for v in fit + val}
    if len(sizes) != 1:
        raise InvalidInput(f"todas las fotos tienen que tener la misma resolución: {sizes}")
    size = sizes.pop()
    if len(fit) < opt.min_views:
        raise InvalidInput(f"hay {len(fit)} pares de ajuste; hacen falta al menos {opt.min_views}")
    warnings: list[str] = []
    if len(val) < 5:
        warnings.append(
            f"solo {len(val)} pares de validación: la elección de modelo es poco confiable"
        )

    candidates: list[Candidate] = []
    for model in opt.models:
        candidates.extend(_calibrate_model(model, board, fit, val, size, opt))
    ok = [c for c in candidates if not c.error and c.T is not None]
    if not ok:
        detail = "; ".join(f"{c.name}: {c.error}" for c in candidates)
        raise InvalidInput(f"ningún modelo pudo calibrar ({detail})")
    selected = _select(ok, opt.tie_tolerance)

    objp = board.object_points()
    reports = _view_reports(selected, board, objp, fit, val)
    warnings.extend(_sanity_warnings(selected, reports))
    stability = _stability(selected, board, fit_sessions, size, opt)
    return CalibrationRun(
        board=board,
        image_size=size,
        selected=selected,
        candidates=candidates,
        fit_keys=selected.fit_keys,
        validation_keys=[v.key for v in val],
        views=reports,
        warnings=warnings,
        stability=stability,
    )


def _select(ok: list[Candidate], tolerance: float) -> Candidate:
    """Elige por el error vertical mediano tras rectificar, en validación.

    Es lo que necesita el estéreo: el mismo punto en la misma fila de los dos ojos. La
    mediana sobre todas las fotos de validación es igual para todos los candidatos y no
    la arrastran unas pocas fotos movidas. El error de transferencia se informa, pero no
    decide: lo domina el ruido de estimar la distancia del tablero con un solo ojo.
    """

    def score(c: Candidate) -> float:
        return c.validation.get("vertical_median_px", c.fit_rms_px)

    best = min(score(c) for c in ok)
    near = [c for c in ok if score(c) <= best * (1 + tolerance)]
    return min(near, key=lambda c: (_COMPLEXITY[c.model], c.refine, score(c)))


def _view_reports(
    cand: Candidate,
    board: Checkerboard,
    objp: np.ndarray,
    fit: list[PairView],
    val: list[PairView],
) -> list[ViewReport]:
    reports = []
    fit_keys = set(cand.fit_keys)
    for view in fit + val:
        if view.key in fit_keys:
            role = "ajuste"
        elif view.key in cand.rejected:
            role = "descartada"
        else:
            role = "validación"
        try:
            e = view_errors(cand.model, objp, view, cand.left, cand.right, cand.R, cand.T)
            vertical, scale = rectified_errors(
                cand.model, board, view, cand.left, cand.right, cand.rect
            )
        except cv2.error:
            e = dict.fromkeys(("left", "right", "transfer", "tilt", "distance"), math.nan)
            vertical, scale = np.array([math.nan]), math.nan
        reports.append(
            ViewReport(
                key=view.key,
                role=role,
                tilt_deg=e["tilt"],
                distance_m=e["distance"],
                left_px=e["left"],
                right_px=e["right"],
                transfer_px=e["transfer"],
                vertical_px=float(np.median(vertical)),
                scale_error=scale,
                reason=cand.rejected.get(view.key, ""),
            )
        )
    return reports


def _sanity_warnings(cand: Candidate, reports: list[ViewReport]) -> list[str]:
    out = []
    T = cand.T.ravel()
    if T[0] > 0:
        out.append(
            "T_x es positivo: la cámara 'izquierda' está a la derecha. Probablemente los "
            "ojos están invertidos en el par lado a lado."
        )
    if math.hypot(T[1], T[2]) > 0.1 * abs(T[0]):
        out.append("la separación entre ojos no es horizontal (T_y o T_z grandes)")
    fx_l, fx_r = float(cand.left.K[0, 0]), float(cand.right.K[0, 0])
    if abs(fx_l - fx_r) > 0.03 * min(fx_l, fx_r):
        out.append(
            f"las focales de los ojos difieren mucho ({fx_l:.0f} vs {fx_r:.0f} px): "
            "calibración mal condicionada, probablemente por poca variedad de poses"
        )
    used = [r for r in reports if r.role == "ajuste"]
    tilted = sum(r.tilt_deg >= 20 for r in used)
    if used and tilted < 0.25 * len(used):
        out.append(
            f"solo {tilted} de {len(used)} fotos con el tablero inclinado >= 20°: "
            "la focal queda mal determinada. Sacar fotos inclinadas 30-45°."
        )
    return out


def _stability(
    cand: Candidate,
    board: Checkerboard,
    sessions: list[Session],
    size: tuple[int, int],
    opt: CalibrationOptions,
) -> list[dict]:
    """Recalibra con cada sesión sola: si la cámara es estable, f y B tienen que coincidir."""
    if len(sessions) < 2:
        return []
    objp = board.object_points()
    used = set(cand.fit_keys)
    rows = []
    for session in sessions:
        views = [v for v in session.views if v.key in used]
        row = {"session": session.name, "n": len(views)}
        if len(views) < opt.min_views:
            row["error"] = "pocas fotos"
            rows.append(row)
            continue
        try:
            intr_l, intr_r, rms, R, T = _fit(cand.model, objp, views, size)
            row.update(
                fx_left=float(intr_l.K[0, 0]),
                fx_right=float(intr_r.K[0, 0]),
                baseline_m=float(np.linalg.norm(T)),
                rms_px=rms,
            )
        except cv2.error as exc:
            row["error"] = _short_error(exc)
        rows.append(row)
    return rows
