"""Cache and verify Stanford SDR v3 telemetry without redistributing the source."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1
from pathlib import Path

import requests
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import seal

METADATA = "https://purl.stanford.edu/hh613qz0317.json"
FILES = "https://stacks.stanford.edu/file/druid:hh613qz0317/"


def files(catalog):
    if (
        catalog["externalIdentifier"] != "druid:hh613qz0317"
        or catalog["version"] != 3
        or catalog["access"]["download"] != "world"
        or catalog["access"]["license"] != "https://creativecommons.org/licenses/by-sa/4.0/legalcode"
    ):
        raise ValueError("Unexpected Stanford dataset version or access terms")
    seen = set()
    for group in catalog["structural"]["contains"]:
        for entry in group["structural"]["contains"]:
            folder, session, name = entry["filename"].split("/")
            if folder != "VehicleDynamicsDataset" or session not in ("Oct2023", "Nov2023"):
                raise ValueError("Unexpected Stanford telemetry layout")
            if entry["access"]["download"] != "world" or not name.endswith(".csv"):
                raise ValueError("Unexpected Stanford telemetry file")
            expected = next(item["digest"] for item in entry["hasMessageDigests"] if item["type"] == "sha1")
            if expected not in seen:
                seen.add(expected)
                yield entry["filename"], entry["size"], expected


def acquire(root):
    root.mkdir(parents=True, exist_ok=True)
    catalog_path = root / "catalog.json"
    response = requests.get(METADATA, timeout=30)
    response.raise_for_status()
    catalog = response.json()
    plan = list(files(catalog))
    if len(plan) != 20:
        raise ValueError("Unexpected number of unique Stanford telemetry runs")
    catalog_path.write_bytes(response.content)

    def download(spec):
        name, size, expected = spec
        path = root / Path(name).name
        if not path.is_file():
            staged = path.with_suffix(".partial")
            try:
                checksum, length = sha1(usedforsecurity=False), 0
                with requests.get(
                    FILES + name, params={"download": "true"}, timeout=(15, 60), stream=True
                ) as raw:
                    raw.raise_for_status()
                    with staged.open("wb") as handle:
                        for block in raw.iter_content(chunk_size=1024 * 1024):
                            length += len(block)
                            if length > size:
                                raise ValueError(f"Stanford response exceeds declared size for {name}")
                            checksum.update(block)
                            handle.write(block)
                if length != size or checksum.hexdigest() != expected:
                    raise ValueError(f"Stanford publication digest mismatch for {name}")
                staged.replace(path)
            finally:
                staged.unlink(missing_ok=True)
        with path.open("rb") as handle:
            checksum = sha1(usedforsecurity=False)
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                checksum.update(block)
        if path.stat().st_size != size or checksum.hexdigest() != expected:
            raise ValueError(f"Stanford cached file mismatch for {name}")
        return path.name, {"bytes": size, "sha256": file_sha256(path), "publisher_sha1": expected}

    with ThreadPoolExecutor(max_workers=4) as pool:
        recorded = dict(pool.map(download, plan))
    write_manifest(
        root / "manifest.json",
        seal({"dataset": METADATA, "catalog_sha256": file_sha256(catalog_path), "runs": recorded}),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    acquire(parser.parse_args().archive)
