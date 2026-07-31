"""Create a checksummed manifest of reusable notebook data products."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    products = []
    notebooks = []
    seen = set()
    for result_path in sorted(ROOT.glob("*/20*-*/result.json")):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        notebooks.append({
            "id": result["id"],
            "archive": result["archive"],
            "research_level": result.get("research_level", "Dense"),
            "claim_type": result.get("claim_type", "Measured result"),
            "provenance": result.get("provenance", []),
        })
        for relative in result.get("artifacts", []):
            path = ROOT / relative
            if not path.is_file() or relative in seen:
                continue
            seen.add(relative)
            products.append({
                "path": relative,
                "notebook_id": result["id"],
                "bytes": path.stat().st_size,
                "sha256": checksum(path),
            })
    payload = {
        "schema_version": "1.0",
        "generated": "2026-07-31",
        "description": "Checksums and provenance for reusable outputs named by scientifically audited notebooks.",
        "notebooks": notebooks,
        "products": products,
    }
    (ROOT / "DATA_PRODUCTS.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {len(notebooks)} dense notebooks, {len(products)} reusable products")


if __name__ == "__main__":
    main()
