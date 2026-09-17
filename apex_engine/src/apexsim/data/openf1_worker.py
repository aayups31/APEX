"""Fresh-process OpenF1 replay; consumes JSON only and never constructs an HTTP client."""
from __future__ import annotations

import sys
from pathlib import Path

from apexsim.data.openf1_archive import _build_tables, verify_openf1_archive
from apexsim.provenance import write_manifest


def install_network_guard() -> list[str]:
    """Permanently reject Python DNS and socket connection/send events in this worker."""
    attempts = []

    def audit(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "socket.sendmsg"}:
            attempts.append(event)
            raise RuntimeError("Network access forbidden during OpenF1 offline replay")

    sys.addaudithook(audit)
    return attempts


def run_worker(archive: Path, output: Path) -> None:
    """Revalidate and reconstruct after installing the permanent network guard."""
    attempts = install_network_guard()
    manifest = verify_openf1_archive(archive)
    snapshot = _build_tables(archive, manifest["requests"], manifest["query"]["session_key"], output)
    write_manifest(output / "snapshot.json", snapshot)
    write_manifest(output / "worker_result.json", {"network_attempts": len(attempts)})
    if attempts:
        raise RuntimeError("Network attempted during OpenF1 replay")


if __name__ == "__main__":
    run_worker(Path(sys.argv[1]), Path(sys.argv[2]))
