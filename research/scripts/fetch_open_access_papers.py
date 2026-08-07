"""Fetch explicitly listed open-access paper PDFs and record hashes.

Run from the kit root. This script intentionally contains only direct sources
known to offer an open version; it does not scrape paywalled publishers.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import requests

SOURCES = {
    "FIENI_2025": "https://arxiv.org/pdf/2512.21570",
    "FIENI_2026_MULTI": "https://arxiv.org/pdf/2602.23056",
    "WUTHRICH_2026_RLMPC": "https://arxiv.org/pdf/2604.00826",
    "CAPPELLO_2025": "https://arxiv.org/pdf/2512.00640",
    "THOMAS_2025": "https://arxiv.org/pdf/2501.04068",
    "BOTTINGER_2023": "https://arxiv.org/pdf/2306.16088",
}

def main() -> None:
    out = Path(__file__).resolve().parents[1] / "open_access_papers"
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for paper_id, url in SOURCES.items():
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        path = out / f"{paper_id}.pdf"
        path.write_bytes(response.content)
        manifest.append({"paper_id": paper_id, "url": url, "bytes": len(response.content), "sha256": hashlib.sha256(response.content).hexdigest()})
        print(path)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
