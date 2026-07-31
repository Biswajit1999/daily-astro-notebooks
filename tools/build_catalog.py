"""Build the dashboard catalogue from notebook folders and result metadata."""

from __future__ import annotations

import json
import re
import shutil
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
    images = [p for p in folder.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    return {
        "id": folder.name,
        "title": title,
        "archive": ARCHIVES[archive_dir],
        "family": ARCHIVES[archive_dir],
        "date": date,
        "date_display": f"{date[8:10]} Jul 2026",
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
    family = "Exoplanets" if "Exoplanet" in data["archive"] else data["archive"].split()[0].replace("·", "").strip()
    if family == "Gaia": family = "Gaia"
    if family == "MAST": family = "MAST"
    if family == "SDSS": family = "SDSS"
    return {
        **data,
        "family": family,
        "date_display": "31 Jul 2026",
        "summary": data["question"],
        "sample_size_display": f"{data['sample_size']:,} samples",
        "dense": True,
        "hero_source": ROOT / data["hero"],
    }


def main():
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    IMAGES.mkdir(parents=True)
    shutil.copy2(ROOT / "assets" / "banner.png", IMAGES / "banner.png")

    notebooks = []
    for archive in ARCHIVES:
        for folder in sorted((ROOT / archive).glob("20*-*"), reverse=True):
            if not (folder / "notebook.ipynb").exists():
                continue
            result = folder / "result.json"
            entry = dense_entry(folder, result) if result.exists() else legacy_entry(folder)
            source = entry.pop("hero_source", None)
            if source and Path(source).exists():
                target = IMAGES / f"{entry['id']}{Path(source).suffix.lower()}"
                shutil.copy2(source, target)
                entry["hero_local"] = f"data/images/{target.name}"
            else:
                entry["hero_local"] = None
            notebooks.append(entry)

    notebooks.sort(key=lambda item: (item["date"], item["dense"], item["title"]), reverse=True)
    payload = {
        "generated": "2026-07-31",
        "stats": {
            "total": len(notebooks),
            "archives": len({item["family"] for item in notebooks}),
            "dense": sum(item["dense"] for item in notebooks),
        },
        "notebooks": notebooks,
    }
    (PUBLIC / "notebooks.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Dashboard catalogue: {len(notebooks)} notebooks, {payload['stats']['dense']} dense")


if __name__ == "__main__":
    main()
