"""Build the dashboard catalogue from notebook folders and result metadata."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "dashboard" / "public" / "data"
IMAGES = PUBLIC / "images"
ARCHIVES = {"mast": "MAST", "gaia": "Gaia", "sdss": "SDSS", "exoplanet-archive": "Exoplanets"}


def clean_markdown(text: str) -> str:
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`#]", "", text)
    return " ".join(text.split())


def legacy_entry(folder: Path) -> dict:
    readme = folder / "README.md"
    body = readme.read_text(encoding="utf-8") if readme.exists() else ""
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    title_line = next((line for line in lines if line.startswith("# ")), folder.name)
    title = clean_markdown(title_line.removeprefix("# "))
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip() and not p.lstrip().startswith("#")]
    summary = clean_markdown(paragraphs[0])[:280] if paragraphs else "Real public-archive astronomy analysis."
    archive_dir = folder.parent.name
    date = folder.name[:10]
    images = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    return {
        "id": folder.name,
        "title": title,
        "archive": ARCHIVES[archive_dir],
        "family": ARCHIVES[archive_dir],
        "date": date,
        "date_display": datetime.strptime(date, "%Y-%m-%d").strftime("%d %b %Y"),
        "summary": summary,
        "question": summary,
        "notebook": str((folder / "notebook.ipynb").relative_to(ROOT)),
        "results": [],
        "validation": "See the notebook and README for the archive query and interpretation.",
        "tags": [ARCHIVES[archive_dir], "real data"],
        "dense": False,
        "hero_source": images[0] if images else None,
    }


def dense_entry(folder: Path, result_path: Path) -> dict:
    data = json.loads(result_path.read_text(encoding="utf-8"))
    family = ARCHIVES[folder.parent.name]
    date = data.get("date", folder.name[:10])
    readme = folder / "README.md"
    body = readme.read_text(encoding="utf-8") if readme.exists() else ""
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip() and not p.lstrip().startswith("#")]
    readme_summary = clean_markdown(paragraphs[0])[:280] if paragraphs else "Real public-archive astronomy analysis."
    question = data.get("question") or readme_summary

    sample_size = data.get("sample_size")
    if not isinstance(sample_size, (int, float)):
        population_counts = [
            value for key, value in data.items()
            if key.startswith("n_") and isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        sample_size = max(population_counts, default=0)

    results = data.get("results")
    if not isinstance(results, list):
        excluded = {"id", "title", "archive", "date", "target", "question", "claim_type"}
        scalar_results = [
            f"{key.replace('_', ' ')}: {value:,}" if isinstance(value, int) else f"{key.replace('_', ' ')}: {value}"
            for key, value in data.items()
            if key not in excluded and isinstance(value, (int, float, str)) and not isinstance(value, bool)
        ]
        results = scalar_results[:4]

    image_sources = sorted(
        (path for path in folder.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg"}),
        key=lambda path: path.name,
    )
    hero_value = data.get("hero")
    hero_source = ROOT / hero_value if hero_value else (image_sources[0] if image_sources else None)
    figure_values = data.get("figures")
    figure_sources = [ROOT / path for path in figure_values] if isinstance(figure_values, list) else image_sources
    return {
        **data,
        "family": family,
        "date": date,
        "date_display": datetime.strptime(date,"%Y-%m-%d").strftime("%d %b %Y"),
        "summary": question,
        "question": question,
        "results": results,
        "sample_size": sample_size,
        "sample_size_display": f"{sample_size:,} samples",
        "dense": True,
        "hero_source": hero_source,
        "research_level":data.get("research_level","Dense"),
        "claim_type":data.get("claim_type","Measured result"),
        "provenance":data.get("provenance",[]),"artifacts":data.get("artifacts",[]),
        "quality_checks":data.get("quality_checks",[]),"limitations":data.get("limitations",[]),
        "figure_sources": figure_sources,
        "validation": data.get("validation", "See the notebook and README for method checks, caveats, and interpretation."),
        "tags": data.get("tags", [family, "real data"]),
    }



EUCLID_REPORTS = (
    (
        "edf-north-halpha",
        "Deep Field North",
        "analysis/euclid_vis_targets.png",
        "report/Euclid_EDF_North_Halpha.pdf",
        "The direct VIS radius contrast spans zero. Fourteen warning-inclusive dual-grism detections yield five candidates that survive peak-bin removal.",
        "Observed Euclid VIS stamps of the seven galaxy sources analysed in Deep Field North",
    ),
    (
        "ngc4236-uv-optical",
        "NGC 4236",
        "analysis/outer_uv_vis.png",
        "report/NGC4236_UV_VIS.pdf",
        "Gaia identifies a foreground star at the optical counterpart of one of 23 exterior UV peaks. SINGS imaging covers 10 of the 23 positions in both bands, and the link to extraplanar ionised gas remains unresolved.",
        "GALEX far-ultraviolet image of NGC 4236 with marked candidates and four observed Euclid VIS cutouts",
    ),
)


def euclid_reports():
    reports = []
    for entry, label, figure, pdf, finding, alt in EUCLID_REPORTS:
        folder = ROOT / "euclid-dr1-foundation" / entry
        title = (folder / "README.md").read_text(encoding="utf-8").splitlines()[0].removeprefix("# ")
        image = IMAGES / f"euclid-{entry}.png"
        destination = PUBLIC / Path(pdf).name
        shutil.copy2(folder / figure, image)
        shutil.copy2(folder / pdf, destination)
        reports.append({
            "id": entry, "label": label, "title": title, "finding": finding,
            "alt": alt, "image": f"data/images/{image.name}",
            "pdf": f"data/{destination.name}", "folder": folder.relative_to(ROOT).as_posix(),
        })
    return reports


def main():
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    IMAGES.mkdir(parents=True)
    shutil.copy2(ROOT / "assets" / "banner.png", IMAGES / "banner.png")
    for entry, day in (("2026-11-14-day01", 1), ("2026-11-15-day02", 2), ("day03-cross-grism", 3)):
        filename = f"Euclid_Day_{day}.pdf"
        archived = ROOT / "euclid-dr1-foundation" / entry / "report" / filename
        shutil.copy2(archived, PUBLIC / filename)


    notebooks = []
    for archive in ARCHIVES:
        for folder in sorted((ROOT / archive).glob("20*-*"), reverse=True):
            if not (folder / "notebook.ipynb").exists():
                continue
            result = folder / "result.json"
            entry = dense_entry(folder, result) if result.exists() else legacy_entry(folder)
            source = entry.pop("hero_source", None)
            figure_sources=entry.pop("figure_sources",[])
            source_path=Path(source).resolve() if source else None
            if source and Path(source).exists():
                target = IMAGES / f"{entry['id']}{Path(source).suffix.lower()}"
                shutil.copy2(source, target)
                entry["hero_local"] = f"data/images/{target.name}"
            else:
                entry["hero_local"] = None
            entry["figures_local"]=[]
            for index,figure in enumerate(figure_sources):
                if not figure.exists(): continue
                if source_path and figure.resolve()==source_path and entry["hero_local"]:
                    entry["figures_local"].append(entry["hero_local"]); continue
                target=IMAGES/f"{entry['id']}--figure-{index+1}{figure.suffix.lower()}"
                shutil.copy2(figure,target); entry["figures_local"].append(f"data/images/{target.name}")
            if not entry["figures_local"] and entry["hero_local"]: entry["figures_local"]=[entry["hero_local"]]
            notebooks.append(entry)

    notebooks.sort(key=lambda item: (item["date"], item["dense"], item["title"]), reverse=True)
    payload = {
        "generated": max(item["date"] for item in notebooks),
        "stats": {
            "total": len(notebooks),
            "archives": len({item["family"] for item in notebooks}),
            "dense": sum(item["dense"] for item in notebooks),
        },
        "notebooks": notebooks,
        "euclid_reports": euclid_reports(),
    }
    (PUBLIC / "notebooks.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Dashboard catalogue: {len(notebooks)} notebooks, {payload['stats']['dense']} dense")


if __name__ == "__main__":
    main()
