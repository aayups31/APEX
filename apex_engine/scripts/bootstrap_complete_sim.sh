#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,real-data]'
pytest -q
python -m apexsim.examples.complete_sim_demo --output artifacts/complete_sim_demo

echo
printf 'APEX complete-simulation vertical slice is ready.\n'
printf 'Open artifacts/complete_sim_demo/standings.csv and telemetry.csv.\n'
