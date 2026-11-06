"""Rescore frozen v11 drift predictions; preserve every original primary pace estimate."""
import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.compound_readiness import LABELS, assess_event, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_decision import ROOT, contrasts


def replay() -> dict:
    folder = ROOT / "docs/verification"
    data = read_json(folder / "compound-v11-development-data.json")
    result = json.loads(gzip.decompress((folder / "compound-v11-development.json.gz").read_bytes()))
    for document in (data, result):
        check_seal(document)
    if result["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Unbound v11 checkpoint predictions")
    reports = {}
    for name, model in result["recipes"].items():
        scores = defaultdict(list)
        for i, (case, old) in enumerate(zip(data["cases"], model["predictions"], strict=True)):
            if old["case_index"] != i:
                raise ValueError("Mismatched case index")
            ref = case["reference_target_s"]
            prefix = case["current_prefix_s"]
            projected = [time - old["applied_correction_s"] for time in prefix]
            values = contrasts(ref, projected)
            if abs(old["predicted_s"] - values[0]) > 1e-12:
                raise ValueError("Changed historical primary pace")
            for j, (start, target) in enumerate(LABELS):
                scored = {**case, "predicted_s": values[j], "reference_persistence_s": old["reference_persistence_s"],
                          "predicted_crossover": crossing(case[start], values[j]),
                          "own_error": abs(contrasts(ref, prefix)[j] - case[target])}
                scores[str(case["session"]), j].append(scored)
        folds, failed = [], []
        for event in sorted(data["sources"]):
            labels = []
            for j in range(2):
                items = scores[event, j]
                if items:
                    metric = assess_event(items)["labels"][j]
                    metric["label_reference_mae_s"] = sum(r["own_error"] for r in items) / len(items)
                    if metric["mae_s"] > metric["label_reference_mae_s"] + 1e-12:
                        metric["passed"] = False
                        metric["failure_codes"].append("PACE_WORSE_THAN_LABEL_REFERENCE")
                    labels.append(metric)
            folds.append({"event": event, "labels": labels})
            if any(not m["passed"] for m in labels):
                failed.append(event)
        reports[name] = {"folds": folds, "failed_supported_events": failed}
    return seal({"scope": "RETROSPECTIVE_RESCORING_ONLY", "result_sha256": result["content_sha256"],
                 "models": reports, "candidate_accepted": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, replay())
