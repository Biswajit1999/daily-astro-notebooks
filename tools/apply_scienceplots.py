"""Apply the shared SciencePlots style to every plotting notebook.

This mechanical migration changes source cells only.  Run the notebook runner
afterward to refresh embedded and exported figures where data are available.
"""

from __future__ import annotations

import re
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
STYLE = 'plt.style.use(["science", "no-latex"])'


def migrate_notebook(path: Path) -> bool:
    notebook = nbformat.read(path, as_version=4)
    changed = False
    plotting_cell = None
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        if "matplotlib.pyplot" in cell.source and plotting_cell is None:
            plotting_cell = cell
        updated = re.sub(r"plt\.style\.use\([^\n]+\)", STYLE, cell.source)
        if updated != cell.source:
            cell.source = updated
            changed = True

    if plotting_cell is not None and not any(
        "import scienceplots" in cell.source
        for cell in notebook.cells if cell.cell_type == "code"
    ):
        lines = plotting_cell.source.splitlines()
        insert_at = next(
            (index + 1 for index, line in enumerate(lines) if "matplotlib.pyplot" in line),
            len(lines),
        )
        lines.insert(insert_at, "import scienceplots")
        plotting_cell.source = "\n".join(lines)
        changed = True

    if plotting_cell is not None and STYLE not in "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    ):
        plotting_cell.source += f"\n{STYLE}"
        changed = True

    if changed:
        nbformat.write(notebook, path)
    return changed


def main() -> None:
    plotting = 0
    changed = 0
    for path in sorted(ROOT.glob("*/20*-*/notebook.ipynb")):
        text = path.read_text(encoding="utf-8")
        if "matplotlib.pyplot" not in text:
            continue
        plotting += 1
        changed += migrate_notebook(path)
    print(f"SciencePlots present in {plotting} plotting notebooks; modified {changed}")


if __name__ == "__main__":
    main()
