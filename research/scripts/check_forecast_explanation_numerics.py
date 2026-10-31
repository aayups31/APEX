"""Numerical preflight only: compare batch2/batch128 on every frozen real checkpoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from apexsim.examples.forecast_explanation_study import _input_metadata
from apexsim.provenance import payload_sha256, write_manifest
from apexsim.research.forecast_benchmark import ForecastScaler
from apexsim.research.forecast_explanations import FrozenForecastPredictor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "evaluation", "cohort", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Numerical preflight output must be fresh")
    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    reference, _, _, _, _, _ = _input_metadata(args.reference, args.evaluation, cohort["profile"], payloads=True)
    payload = json.loads((args.reference/"scaler.json").read_text(encoding="utf-8"))
    scaler = ForecastScaler(*(np.array(payload[k]) for k in ("input_mean", "input_std", "target_mean", "target_std")))
    with np.load(args.evaluation/"windows.npz", allow_pickle=False) as data:
        indices = [c["origin_index"] for c in cohort["cases"]]
        x, static = data["dynamic"][indices], data["static"][indices]
    reports = {}
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        for record in reference["records"]:
            predictor = FrozenForecastPredictor(args.reference/record["checkpoint"], record, scaler, reference["vocabulary"])
            batch = predictor(x, static)
            separate = np.concatenate([predictor(np.repeat(x[i:i+1], 2, axis=0),
                                                np.repeat(static[i:i+1], 2, axis=0))[:1] for i in range(len(x))])
            report = {"maximum_batch_difference_kj": float(np.max(abs(batch-separate))),
                      "failed_cells": int(np.sum(~np.isclose(batch, separate, rtol=1e-6, atol=1e-7)))}
            reports[record["name"]] = report
            print(record["name"], report, flush=True)
    finally:
        torch.set_num_threads(threads)
    result = {"schema_version": "apex-forecast-explanation-numerical-preflight-v1", "origins": len(x),
              "cohort_sha256": cohort["content_sha256"], "models": reports,
              "passed": all(r["failed_cells"] == 0 for r in reports.values()),
              "scientific_outcomes_used": False, "rtol": 1e-6, "atol_kj": 1e-7}
    result["content_sha256"] = payload_sha256(result)
    write_manifest(args.output, result)
    if not result["passed"]:
        raise ValueError("Frozen-model numerical preflight failed; do not run explanations")


if __name__ == "__main__":
    main()
