"""Check dense notebook folders before publishing the dashboard."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_RESULT_FIELDS = {
    "id", "title", "archive", "date", "question", "sample_size",
    "results", "validation", "notebook", "hero",
}


def main() -> None:
    failures: list[str] = []
    dense_count = 0

    for result_path in sorted(ROOT.glob("*/20*-*/result.json")):
        dense_count += 1
        folder = result_path.parent
        data = json.loads(result_path.read_text(encoding="utf-8"))
        missing = REQUIRED_RESULT_FIELDS - data.keys()
        if missing:
            failures.append(f"{result_path.relative_to(ROOT)}: missing {sorted(missing)}")

        notebook_path = ROOT / data.get("notebook", "")
        hero_path = ROOT / data.get("hero", "")
        if not notebook_path.is_file():
            failures.append(f"{folder.relative_to(ROOT)}: notebook path is invalid")
            continue
        if not hero_path.is_file():
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
        if len(code_cells) < 6:
            failures.append(f"{notebook_path.relative_to(ROOT)}: fewer than 6 code cells")
        if markdown_words < 400:
            failures.append(f"{notebook_path.relative_to(ROOT)}: fewer than 400 markdown words")
        if not any(cell.get("outputs") for cell in code_cells):
            failures.append(f"{notebook_path.relative_to(ROOT)}: no saved code output")
        if errors:
            failures.append(f"{notebook_path.relative_to(ROOT)}: saved error output found")
        if not data.get("results"):
            failures.append(f"{result_path.relative_to(ROOT)}: results list is empty")

    if failures:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(failures))
    print(f"Validated {dense_count} dense notebook folders")


if __name__ == "__main__":
    main()
