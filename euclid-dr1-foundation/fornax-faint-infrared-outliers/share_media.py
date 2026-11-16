"""Prepare a compact shareable image from the registered observed cutouts."""
from pathlib import Path
import argparse
from PIL import Image


def build(results, share):
    rows = []
    for rank in range(1,4):
        path = results / "audit" / f"F{rank:02}" / "cutouts.png"
        with Image.open(path) as source:
            row = source.convert("RGB")
        row.save(path.with_suffix(".webp"),quality=88)
        row.thumbnail((1250,300))
        rows.append(row)
    panel = Image.new("RGB",(1250,sum(row.height for row in rows)+4),"white")
    y = 0
    for row in rows:
        panel.paste(row,((1250-row.width)//2,y))
        y += row.height
    panel.save(results/"observed_targets.webp",quality=88)
    if share:
        panel.save(share,quality=91,optimize=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results",type=Path,default=Path("results"))
    p.add_argument("--share",type=Path)
    args = p.parse_args()
    build(args.results,args.share)
