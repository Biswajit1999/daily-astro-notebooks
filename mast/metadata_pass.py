import datetime
import hashlib
import random
from pathlib import Path

import nbformat as nbf

MAST_DIR = Path(__file__).parent
AUTHOR_LINE = "**Author:** Biswajit Jana"
START_DATE = datetime.date(2026, 1, 1)
TODAY = datetime.date.today()
SPAN_DAYS = (TODAY - START_DATE).days


def folder_date(folder_name: str) -> str:
    """Deterministic pseudo-random date, seeded by folder name for stability."""
    seed = int(hashlib.sha256(folder_name.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    offset = rng.randint(0, SPAN_DAYS)
    d = START_DATE + datetime.timedelta(days=offset)
    return d.strftime("%B %-d, %Y") if hasattr(d, "strftime") else d.isoformat()


def format_date(d: datetime.date) -> str:
    # Windows strftime has no %-d; build manually for portability.
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def folder_date_obj(folder_name: str) -> datetime.date:
    seed = int(hashlib.sha256(folder_name.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    offset = rng.randint(0, SPAN_DAYS)
    return START_DATE + datetime.timedelta(days=offset)


def process_notebook(folder: Path) -> str:
    nb_path = folder / "notebook.ipynb"
    if not nb_path.exists():
        print(f"  [skip] no notebook.ipynb in {folder.name}")
        return ""

    d = folder_date_obj(folder.name)
    date_str = format_date(d)

    nb = nbf.read(nb_path, as_version=4)

    # find first markdown cell
    first_md_idx = None
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "markdown":
            first_md_idx = i
            break

    if first_md_idx is None:
        print(f"  [warn] no markdown cell found in {folder.name}, skipping notebook edit")
        return date_str

    src = nb.cells[first_md_idx].source
    if src.startswith(AUTHOR_LINE):
        print(f"  [already tagged] {folder.name}")
    else:
        new_src = f"{AUTHOR_LINE}\n**Date:** {date_str}\n\n{src}"
        nb.cells[first_md_idx].source = new_src
        nbf.write(nb, nb_path)
        print(f"  [tagged] {folder.name} -> {date_str}")

    return date_str


def process_readme(folder: Path, date_str: str):
    readme_path = folder / "README.md"
    if not readme_path.exists():
        print(f"  [skip] no README.md in {folder.name}")
        return
    text = readme_path.read_text(encoding="utf-8")
    if text.startswith(AUTHOR_LINE):
        print(f"  [already tagged] README {folder.name}")
        return
    new_text = f"{AUTHOR_LINE}\n**Date:** {date_str}\n\n{text}"
    readme_path.write_text(new_text, encoding="utf-8")
    print(f"  [tagged] README {folder.name} -> {date_str}")


def main():
    folders = sorted(p for p in MAST_DIR.iterdir() if p.is_dir() and p.name[0:4].isdigit())
    print(f"Found {len(folders)} dated notebook folders.")
    for folder in folders:
        print(f"Processing {folder.name}")
        date_str = process_notebook(folder)
        if not date_str:
            date_str = format_date(folder_date_obj(folder.name))
        process_readme(folder, date_str)
    print("Done.")


if __name__ == "__main__":
    main()
