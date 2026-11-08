"""Download R041 driving observations with optional private local OpenF1 sign-in."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

import requests
from apexsim.data.openf1_http import DownloadPolicy, OpenF1Client
from apexsim.provenance import write_manifest
from compound_driving_data import prepare
from diagnose_compound_decision import ROOT


def obtain_token(username: str, password: str) -> str:
    """Exchange local credentials for a token, without persisting or logging secrets."""
    if not username.strip() or not password:
        raise ValueError("OpenF1 username and password are required")
    try:
        response = requests.post(
            "https://api.openf1.org/token",
            data={"username": username, "password": password},
            timeout=(10, 60),
            allow_redirects=False,
        )
    except requests.RequestException:
        raise RuntimeError("OpenF1 sign-in connection failed") from None
    if response.status_code != 200:
        raise RuntimeError(f"OpenF1 sign-in failed with HTTP {response.status_code}")
    try:
        token = response.json()["access_token"]
    except (ValueError, KeyError, TypeError):
        raise RuntimeError("OpenF1 returned an invalid sign-in response") from None
    if (
        not isinstance(token, str)
        or not token.strip()
        or any(c.isspace() for c in token)
    ):
        raise RuntimeError("OpenF1 returned an invalid access token")
    return token


def acquire(
    root: Path, snapshots: Path, output: Path, token: str | None = None
) -> None:
    """Use an in-memory bearer header with the existing bounded archival downloader."""
    if token is not None and (not token or any(c.isspace() for c in token)):
        raise ValueError("Invalid OpenF1 access token")
    client = OpenF1Client(DownloadPolicy())
    if token is not None:
        client.session.headers["Authorization"] = f"Bearer {token}"
    try:
        write_manifest(output, prepare(root, snapshots, client))
    finally:
        client.session.headers.pop("Authorization", None)
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument(
        "--sign-in",
        action="store_true",
        help="Prompt for OpenF1 username and hidden password locally",
    )
    auth.add_argument(
        "--token-env",
        metavar="NAME",
        help="Read an existing bearer token from this environment variable",
    )
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument(
        "--snapshots",
        type=Path,
        required=True,
        help="A fresh directory for immutable source responses",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = None
    if args.sign_in:
        token = obtain_token(
            input("OpenF1 username: ").strip(), getpass.getpass("OpenF1 password: ")
        )
    if args.token_env:
        token = os.environ.get(args.token_env)
        if not token:
            parser.error("The requested token environment variable is empty")
    acquire(args.native_root, args.snapshots, args.output, token)
