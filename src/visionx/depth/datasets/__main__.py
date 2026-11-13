"""Datos públicos (T04): descargar con hash, auditar y escribir el manifiesto.

    uv run python -m visionx.depth.datasets descargar middeval3
    uv run python -m visionx.depth.datasets auditar middeval3 --hojas 10
    uv run python -m visionx.depth.datasets manifiesto middeval3
    uv run python -m visionx.depth.datasets verificar middeval3   # en otra computadora

Carpetas (todas fuera de Git salvo el manifiesto):
    data/descargas/<nombre>/ archivos comprimidos tal como se bajaron
    data/raw/<nombre>/       contenido extraído, lo que leen los adaptadores
    outputs/datos/<nombre>/  auditoría: auditoria.yaml y hojas de contacto PNG
    datasets/<nombre>.yaml   manifiesto con hashes, licencia y partición (va a Git)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import yaml

from visionx.depth.datasets.audit import audit_sample, contact_sheet, dataset_verdict
from visionx.depth.datasets.catalog import CATALOG, DatasetInfo
from visionx.depth.datasets.manifest import (
    file_entry,
    load_manifest,
    save_manifest,
    sha256_file,
    verify_files,
)
from visionx.shared.errors import InvalidInput

USER_AGENT = "visionx-datos"  # cliente genérico; no mandamos datos personales


def _download(info: DatasetInfo, data: Path) -> None:
    """Baja (o toma los bajados a mano), controla el hash y extrae en data/raw/<nombre>/."""
    if not info.downloads:
        raise InvalidInput(f"{info.name}: sin archivos en el catálogo. {info.manual_download}")
    folder = data / "descargas" / info.name
    folder.mkdir(parents=True, exist_ok=True)
    target = data / "raw" / info.name
    missing = []
    for item in info.downloads:
        path = folder / item.filename
        if path.exists() and path.stat().st_size == item.bytes and sha256_file(path) == item.sha256:
            print(f"ya estaba: {path.name}")
        elif not item.url:  # descarga manual: solo se controla lo que dejó la persona
            missing.append(path.name if not path.exists() else f"{path.name} (hash distinto)")
            continue
        else:
            print(f"bajando {item.url} ({item.bytes / 1e6:.1f} MB)...")
            partial = path.with_suffix(path.suffix + ".parcial")
            request = urllib.request.Request(item.url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request) as response, partial.open("wb") as f:
                shutil.copyfileobj(response, f)
            got = sha256_file(partial)
            if got != item.sha256:
                raise InvalidInput(f"{path.name}: hash {got} distinto del catálogo; no se usa")
            partial.replace(path)  # solo queda con el nombre final si el hash coincide
        dest = target / item.extract_to
        dest.mkdir(parents=True, exist_ok=True)
        print(f"extrayendo {path.name} en {dest}")
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as z:
                z.extractall(dest)
        else:
            # .7z: bsdtar (incluido en macOS y en Windows 10+) lo extrae sin dependencias.
            subprocess.run(["tar", "-xf", str(path), "-C", str(dest)], check=True)
    if missing:
        raise InvalidInput(
            f"faltan en {folder}: {', '.join(missing)}. Se bajan a mano: {info.manual_download}"
        )
    print(f"extraído en {target}")


def _spread(items: list, n: int) -> list:
    """n elementos repartidos a lo largo de la lista (todos si n <= 0 o alcanza)."""
    if n <= 0 or n >= len(items):
        return list(items)
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)] if n > 1 else items[:1]


def _audit(info: DatasetInfo, data: Path, out: Path, count: int, sheets: int) -> int:
    refs = info.index(data / "raw" / info.name)
    chosen = _spread(refs, count)
    with_sheet = {r.sample_id for r in _spread(chosen, sheets)} if sheets > 0 else set()
    out.mkdir(parents=True, exist_ok=True)
    reports = []
    for ref in chosen:
        sample = ref.load()  # de a una: no acumular imágenes en memoria
        report = audit_sample(sample)
        reports.append(report)
        if ref.sample_id in with_sheet:
            contact_sheet(sample, out / f"{ref.sample_id.replace('/', '_')}.png")
        f = report["fotometrico"]
        print(f"{ref.sample_id:22s} GT {report['gt_valida_pct']:5.1f} %  "
              f"mínimo en {f['minimo_en_px']} px ({f['minimo_subpx']})  "
              f"cociente {f['cociente']}  {f['veredicto']}")  # fmt: skip
    result = dataset_verdict(reports)
    summary = {"dataset": info.name, "muestras_total": len(refs), "auditadas": len(chosen),
               "escenas": len({r.scene_id for r in refs}), "veredicto": result,
               "detalle": reports}  # fmt: skip
    path = out / "auditoria.yaml"
    path.write_text(yaml.safe_dump(summary, allow_unicode=True, sort_keys=False), "utf-8")
    print(f"{len(chosen)} de {len(refs)} muestras auditadas, {summary['escenas']} escenas: "
          f"{result['alineadas']} alineadas, no concluyentes {result['no_concluyentes'] or 0}, "
          f"desalineadas {result['desalineadas'] or 0}; "
          f"corrimiento mediano {result['corrimiento_mediano_px']} px")  # fmt: skip
    print("GT bien leída" if result["ok"] else f"PROBLEMAS: {'; '.join(result['problemas'])}")
    print(f"guardado en {path}")
    return 0 if result["ok"] else 1


def _manifest(info: DatasetInfo, data: Path, out: Path) -> None:
    root = data / "raw" / info.name
    refs = info.index(root)
    manifest = {
        "nombre": info.name,
        "rol": info.role,
        "fuente": info.source,
        "licencia": info.license,
        "cita": info.citation,
        "descargas": [{"url": d.url, "bytes": d.bytes, "sha256": d.sha256} for d in info.downloads],
        "descarga_manual": info.manual_download or None,
        "reglas_gt": list(info.gt_rules),
        "notas": list(info.notes),
        "particion": info.partition(refs),  # grupo -> escenas; nunca una escena en dos grupos
        "muestras": [
            {
                "id": r.sample_id,
                "escena": r.scene_id,
                "grupo_oficial": r.group,
                "archivos": [file_entry(root / f, root) for f in r.files],
            }
            for r in refs
        ],
    }
    print(f"manifiesto en {save_manifest(out / f'{info.name}.yaml', manifest)}")


def _verify(info: DatasetInfo, data: Path, manifests: Path) -> int:
    """Compara los archivos extraídos con el manifiesto versionado (bytes y SHA-256)."""
    manifest = load_manifest(manifests / f"{info.name}.yaml")
    entries = [f for m in manifest["muestras"] for f in m["archivos"]]
    problems = verify_files(entries, data / "raw" / info.name)
    for problem in problems:
        print(problem)
    print(f"{len(entries)} archivos; {len(problems)} problemas")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m visionx.depth.datasets")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("descargar", "auditar", "manifiesto", "verificar"):
        p = sub.add_parser(name)
        p.add_argument("dataset", choices=sorted(CATALOG))
        p.add_argument("--datos", type=Path, default=Path("data"))
    sub.choices["auditar"].add_argument("--salida", type=Path, default=Path("outputs/datos"))
    sub.choices["auditar"].add_argument("--hojas", type=int, default=10)
    sub.choices["auditar"].add_argument(
        "--muestras", type=int, default=0, help="cuántas auditar, repartidas (0 = todas)"
    )
    for name in ("manifiesto", "verificar"):
        sub.choices[name].add_argument("--manifiestos", type=Path, default=Path("datasets"))
    args = parser.parse_args(argv)
    info = CATALOG[args.dataset]
    try:
        if args.cmd == "descargar":
            _download(info, args.datos)
        elif args.cmd == "auditar":
            return _audit(info, args.datos, args.salida / info.name, args.muestras, args.hojas)
        elif args.cmd == "verificar":
            return _verify(info, args.datos, args.manifiestos)
        else:
            _manifest(info, args.datos, args.manifiestos)
    except (InvalidInput, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
