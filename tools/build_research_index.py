"""Build a repository-level research index for the daily astronomy notebooks.

The index is intentionally independent of the dashboard catalogue. The dashboard
is a browsing interface; this file is a reproducibility and portfolio audit:
how many notebooks exist, where the evidence lives, what archive each analysis
uses, which claims are validated, and which reusable products carry checksums.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIRS = {
    "sdss": "Sloan Digital Sky Survey",
    "mast": "MAST",
    "gaia": "ESA Gaia",
    "exoplanet-archive": "NASA Exoplanet Archive",
}
JSON_OUT = ROOT / "RESEARCH_INDEX.json"
MD_OUT = ROOT / "RESEARCH_INDEX.md"


@dataclass(frozen=True)
class NotebookRecord:
    ident: str
    title: str
    archive_dir: str
    archive: str
    date: str
    question: str
    sample_size: int | None
    research_level: str
    claim_type: str
    notebook: str
    readme: str
    hero: str | None
    figures: tuple[str, ...]
    artifacts: tuple[str, ...]
    provenance_count: int
    quality_check_count: int
    limitation_count: int
    has_result_json: bool


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def notebook_title(folder: Path, result: dict[str, Any] | None) -> str:
    if result and result.get("title"):
        return str(result["title"]).strip()
    readme = folder / "README.md"
    if readme.exists():
        for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("# "):
                return line.removeprefix("# ").strip()
    return folder.name


def safe_relative(path: Path | str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        try:
            return str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")
    return str(p).replace("\\", "/")


def as_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).replace("\\", "/") for item in value if str(item).strip())


def record_from_folder(archive_dir: str, folder: Path) -> NotebookRecord | None:
    notebook = folder / "notebook.ipynb"
    if not notebook.exists():
        return None

    result_path = folder / "result.json"
    result = read_json(result_path) if result_path.exists() else None
    date = folder.name[:10]

    if result:
        ident = str(result.get("id") or folder.name)
        question = str(result.get("question") or "")
        sample_size = result.get("sample_size")
        sample_size = int(sample_size) if isinstance(sample_size, (int, float)) else None
        research_level = str(result.get("research_level") or "Dense")
        claim_type = str(result.get("claim_type") or "Measured result")
        hero = safe_relative(result.get("hero"))
        figures = as_tuple(result.get("figures"))
        artifacts = as_tuple(result.get("artifacts"))
        provenance_count = len(result.get("provenance", []) if isinstance(result.get("provenance"), list) else [])
        quality_check_count = len(result.get("quality_checks", []) if isinstance(result.get("quality_checks"), list) else [])
        limitation_count = len(result.get("limitations", []) if isinstance(result.get("limitations"), list) else [])
    else:
        ident = folder.name
        question = "Legacy real-data notebook awaiting full result.json audit metadata."
        sample_size = None
        research_level = "Legacy"
        claim_type = "Exploratory analysis"
        images = sorted(
            p for p in folder.iterdir()
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}
        )
        hero = safe_relative(images[0].relative_to(ROOT)) if images else None
        figures = tuple(safe_relative(p.relative_to(ROOT)) or "" for p in images[:3])
        artifacts = ()
        provenance_count = 0
        quality_check_count = 0
        limitation_count = 0

    return NotebookRecord(
        ident=ident,
        title=notebook_title(folder, result),
        archive_dir=archive_dir,
        archive=ARCHIVE_DIRS[archive_dir],
        date=date,
        question=question,
        sample_size=sample_size,
        research_level=research_level,
        claim_type=claim_type,
        notebook=str(notebook.relative_to(ROOT)).replace("\\", "/"),
        readme=str((folder / "README.md").relative_to(ROOT)).replace("\\", "/"),
        hero=hero,
        figures=tuple(item for item in figures if item),
        artifacts=tuple(item for item in artifacts if item),
        provenance_count=provenance_count,
        quality_check_count=quality_check_count,
        limitation_count=limitation_count,
        has_result_json=result is not None,
    )


def collect_notebooks() -> list[NotebookRecord]:
    records: list[NotebookRecord] = []
    for archive_dir in ARCHIVE_DIRS:
        for folder in sorted((ROOT / archive_dir).glob("20*-*")):
            record = record_from_folder(archive_dir, folder)
            if record:
                records.append(record)
    return records


def artifact_record(relative: str, notebook_id: str) -> dict[str, Any]:
    path = ROOT / relative
    return {
        "path": relative,
        "notebook_id": notebook_id,
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256(path) if path.is_file() else None,
    }


def build_payload(records: list[NotebookRecord]) -> dict[str, Any]:
    by_archive = Counter(record.archive for record in records)
    by_level = Counter(record.research_level for record in records)
    by_claim = Counter(record.claim_type for record in records)
    by_date = Counter(record.date for record in records)
    samples_by_archive: dict[str, int] = defaultdict(int)
    for record in records:
        if record.sample_size is not None:
            samples_by_archive[record.archive] += record.sample_size

    artifacts: list[dict[str, Any]] = []
    seen_artifacts: set[str] = set()
    for record in records:
        for relative in record.artifacts:
            if relative in seen_artifacts:
                continue
            seen_artifacts.add(relative)
            artifacts.append(artifact_record(relative, record.ident))

    indexed = [
        {
            "id": record.ident,
            "title": record.title,
            "archive": record.archive,
            "archive_dir": record.archive_dir,
            "date": record.date,
            "question": record.question,
            "sample_size": record.sample_size,
            "research_level": record.research_level,
            "claim_type": record.claim_type,
            "notebook": record.notebook,
            "readme": record.readme,
            "hero": record.hero,
            "figures": list(record.figures),
            "artifacts": list(record.artifacts),
            "provenance_count": record.provenance_count,
            "quality_check_count": record.quality_check_count,
            "limitation_count": record.limitation_count,
            "has_result_json": record.has_result_json,
        }
        for record in sorted(records, key=lambda item: (item.date, item.archive, item.title), reverse=True)
    ]

    return {
        "schema": "daily-astro-research-index-v1",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "notebooks": len(records),
            "archives": len(by_archive),
            "with_result_json": sum(record.has_result_json for record in records),
            "with_provenance": sum(record.provenance_count > 0 for record in records),
            "with_quality_checks": sum(record.quality_check_count > 0 for record in records),
            "with_limitations": sum(record.limitation_count > 0 for record in records),
            "reusable_artifacts": len(artifacts),
            "missing_artifacts": sum(1 for artifact in artifacts if not artifact["exists"]),
        },
        "by_archive": dict(sorted(by_archive.items())),
        "sample_size_by_archive": dict(sorted(samples_by_archive.items())),
        "by_research_level": dict(sorted(by_level.items())),
        "by_claim_type": dict(sorted(by_claim.items())),
        "by_date": dict(sorted(by_date.items())),
        "artifacts": sorted(artifacts, key=lambda item: item["path"]),
        "notebooks": indexed,
    }


def markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Daily Astro Notebooks Research Index",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "This index is a repository-level audit of notebook provenance, archive coverage, claim type, validation maturity, and reusable evidence products.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Notebooks | {summary['notebooks']} |",
        f"| Archive families | {summary['archives']} |",
        f"| Notebooks with result.json | {summary['with_result_json']} |",
        f"| Notebooks with provenance metadata | {summary['with_provenance']} |",
        f"| Notebooks with quality checks | {summary['with_quality_checks']} |",
        f"| Notebooks with explicit limitations | {summary['with_limitations']} |",
        f"| Reusable artifacts with checksums | {summary['reusable_artifacts']} |",
        f"| Missing declared artifacts | {summary['missing_artifacts']} |",
        "",
        "## Archive Coverage",
        "",
        "| Archive | Notebooks | Indexed sample size |",
        "| --- | ---: | ---: |",
    ]

    for archive, count in payload["by_archive"].items():
        sample_size = payload["sample_size_by_archive"].get(archive, 0)
        lines.append(f"| {archive} | {count} | {sample_size:,} |")

    lines.extend(["", "## Research Maturity", "", "| Level | Notebooks |", "| --- | ---: |"])
    for level, count in payload["by_research_level"].items():
        lines.append(f"| {level} | {count} |")

    lines.extend(["", "## Claim Types", "", "| Claim Type | Notebooks |", "| --- | ---: |"])
    for claim_type, count in payload["by_claim_type"].items():
        lines.append(f"| {claim_type} | {count} |")

    lines.extend(["", "## Recent Notebooks", ""])
    for record in payload["notebooks"][:20]:
        lines.append(
            f"- `{record['date']}` [{record['title']}]({record['readme']}) "
            f"- {record['archive']} - {record['research_level']} - {record['claim_type']}"
        )

    lines.extend([
        "",
        "## Machine-Readable Index",
        "",
        "The full record, including artifacts and SHA-256 checksums, is stored in [`RESEARCH_INDEX.json`](RESEARCH_INDEX.json).",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    records = collect_notebooks()
    if not records:
        raise SystemExit("No notebooks found under archive/date folders.")
    payload = build_payload(records)
    JSON_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    MD_OUT.write_text(markdown(payload) + "\n", encoding="utf-8")
    print(
        "Research index: "
        f"{payload['summary']['notebooks']} notebooks, "
        f"{payload['summary']['reusable_artifacts']} reusable artifacts, "
        f"{payload['summary']['missing_artifacts']} missing artifacts"
    )


if __name__ == "__main__":
    main()
