"""Check dense notebook folders before publishing the dashboard."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_RESULT_FIELDS = {
    "id", "title", "archive", "date", "question", "sample_size",
    "results", "validation", "notebook", "hero",
}
AUDIT_FIELDS = {
    "figures", "research_level", "claim_type", "provenance", "artifacts",
    "quality_checks", "limitations",
}
RESEARCH_INDEX_FIELDS = {
    "schema", "generated_utc", "summary", "by_archive", "by_research_level",
    "by_claim_type", "artifacts", "notebooks",
}


def main() -> None:
    failures: list[str] = []
    dense_count = 0
    compact_count = 0
    audit_count = 0

    for result_path in sorted(ROOT.glob("*/20*-*/result.json")):
        folder = result_path.parent
        data = json.loads(result_path.read_text(encoding="utf-8"))
        dense_schema = REQUIRED_RESULT_FIELDS <= data.keys()
        if dense_schema:
            dense_count += 1
        else:
            compact_count += 1
            compact_missing = {"id", "title"} - data.keys()
            if compact_missing:
                failures.append(f"{result_path.relative_to(ROOT)}: compact record missing {sorted(compact_missing)}")

        notebook_path = ROOT / data.get("notebook", "") if data.get("notebook") else folder / "notebook.ipynb"
        hero_path = ROOT / data.get("hero", "") if data.get("hero") else next(
            (path for path in folder.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}),
            None,
        )
        if not notebook_path.is_file():
            failures.append(f"{folder.relative_to(ROOT)}: notebook path is invalid")
            continue
        if dense_schema and (hero_path is None or not hero_path.is_file()):
            failures.append(f"{folder.relative_to(ROOT)}: hero path is invalid")

        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        cells = notebook.get("cells", [])
        code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
        markdown_words = sum(
            len("".join(cell.get("source", [])).split())
            for cell in cells
            if cell.get("cell_type") == "markdown"
        )
        errors = [
            output
            for cell in code_cells
            for output in cell.get("outputs", [])
            if output.get("output_type") == "error"
        ]
        if dense_schema and len(code_cells) < 6:
            failures.append(f"{notebook_path.relative_to(ROOT)}: fewer than 6 code cells")
        if dense_schema and markdown_words < 400:
            failures.append(f"{notebook_path.relative_to(ROOT)}: fewer than 400 markdown words")
        if dense_schema and not any(cell.get("outputs") for cell in code_cells):
            failures.append(f"{notebook_path.relative_to(ROOT)}: no saved code output")
        if errors:
            failures.append(f"{notebook_path.relative_to(ROOT)}: saved error output found")
        if dense_schema and not data.get("results"):
            failures.append(f"{result_path.relative_to(ROOT)}: results list is empty")

        # New scientific-audit records carry a richer, machine-checkable
        # contract. Legacy dense notebooks remain valid while they are upgraded
        # in later batches.
        if "research_level" in data:
            audit_count += 1
            missing_audit = AUDIT_FIELDS - data.keys()
            if missing_audit:
                failures.append(f"{result_path.relative_to(ROOT)}: missing audit fields {sorted(missing_audit)}")
            if len(data.get("figures", [])) < 2:
                failures.append(f"{result_path.relative_to(ROOT)}: audit needs at least two evidence figures")
            for relative in data.get("figures", []) + data.get("artifacts", []):
                if not (ROOT / relative).is_file():
                    failures.append(f"{result_path.relative_to(ROOT)}: missing declared file {relative}")
            checks = data.get("quality_checks", [])
            if not checks or any(not {"name", "status"} <= item.keys() for item in checks):
                failures.append(f"{result_path.relative_to(ROOT)}: malformed quality checks")
            if not data.get("provenance") or not data.get("limitations"):
                failures.append(f"{result_path.relative_to(ROOT)}: provenance or limitations are empty")

    index_path = ROOT / "RESEARCH_INDEX.json"
    index_md_path = ROOT / "RESEARCH_INDEX.md"
    notebook_count = len(list(ROOT.glob("*/20*-*/notebook.ipynb")))
    if not index_path.is_file() or not index_md_path.is_file():
        failures.append("research index is missing; run tools/build_research_index.py")
    else:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        missing_index = RESEARCH_INDEX_FIELDS - index.keys()
        if missing_index:
            failures.append(f"RESEARCH_INDEX.json: missing {sorted(missing_index)}")
        if index.get("schema") != "daily-astro-research-index-v1":
            failures.append("RESEARCH_INDEX.json: unexpected schema")
        summary = index.get("summary", {})
        if summary.get("notebooks") != notebook_count:
            failures.append(
                "RESEARCH_INDEX.json: notebook count is stale "
                f"({summary.get('notebooks')} indexed, {notebook_count} found)"
            )
        if summary.get("missing_artifacts") != 0:
            failures.append("RESEARCH_INDEX.json: declared reusable artifacts are missing")

    if failures:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(failures))
    print(
        f"Validated {dense_count} dense notebooks, {compact_count} compact records, "
        f"including {audit_count} scientific audits"
    )


if __name__ == "__main__":
    main()
