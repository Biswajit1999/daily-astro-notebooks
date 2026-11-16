"""Retrieve and check the archived FITS files used in the NGC 4236 pilot."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def download(item, destination):
    target = destination / item["filename"]
    if target.is_file():
        with target.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        if target.stat().st_size == item["bytes"] and checksum == item["sha256"]:
            return
        raise OSError(f"Cached file differs from the manifest: {target}")
    temporary = target.with_suffix(".part")
    checksum = hashlib.sha256()
    count = 0
    try:
        with urlopen(item["url"], timeout=100) as response, temporary.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
                checksum.update(block)
                count += len(block)
        if count != item["bytes"] or checksum.hexdigest() != item["sha256"]:
            raise OSError(f"Archive file differs from the manifest: {item['url']}")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    target = parser.parse_args().destination
    target.mkdir(parents=True, exist_ok=True)
    manifest = Path(__file__).with_name("inputs.json")
    for item in json.loads(manifest.read_text()):
        download(item, target)


if __name__ == "__main__":
    main()
