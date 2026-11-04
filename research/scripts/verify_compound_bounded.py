"""Offline R041 v9 artifact verification; accuracy acceptance remains separate."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.compound_bounded import fit_bounded, predict_bounded
from apexsim.research.compound_crossover_head import fit_event, predict_event
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_bounded import audit as audit_development
from audit_compound_bounded_confirmation import audit as audit_confirmation
from audit_compound_context import audit as audit_context
from confirm_compound_bounded import BASE, calibrate, evaluate, verify_frozen
from confirm_compound_multiseason import canonical_file_sha


def verify(archive: Path, *, development_replay: Path | None = None) -> dict:
    """Refit coefficients, audit native associations, replay and mutate targets.

    Exact refitting/replay requires the recorded numerical environment. The
    optional development replay is a second complete nested run, not training
    fit predictions. This command makes no network requests.
    """
    root = BASE/"docs/verification"
    frozen, data, results = [read_json(root/name) for name in (
        "compound-v9-calibration.json", "compound-v9-development-data.json", "compound-v9-results.json")]
    development = json.loads(gzip.decompress((root/"compound-v9-development.json.gz").read_bytes()))
    for item in (frozen, data, results, development):
        check_seal(item)
    verify_frozen(frozen)
    bounded = fit_bounded(data["cases"], **development["selected_setting"])
    bounded["radius_s"] = frozen["pace_head"]["radius_s"]
    event = fit_event(data["cases"], development["selected_event_head"]["c"])
    event["threshold"] = development["selected_event_head"]["threshold"]
    if bounded != frozen["pace_head"] or event != frozen["event_head"] or calibrate() != frozen:
        raise ValueError("Frozen coefficient refit differs; check recorded numerical environment")
    if evaluate(frozen, archive) != results:
        raise ValueError("Frozen prospective result replay differs")
    development_audit = audit_development(data, development)
    native_context = audit_context(data, archive.parent)
    confirmation_audit = audit_confirmation(frozen, results, archive)
    for row in results["cases"]:
        before = predict_bounded(frozen["pace_head"], row), predict_event(frozen["event_head"], row)
        changed = {**row, "actual_s": 10000., "pairwise_actual_s": -10000., "current_target_s": [9999.]*3}
        if before != (predict_bounded(frozen["pace_head"], changed), predict_event(frozen["event_head"], changed)):
            raise ValueError("Future current-stint targets affected a frozen forecast")
    replay_exact = None
    if development_replay is not None:
        second = read_json(development_replay)
        check_seal(second)
        replay_exact = second == development
        if not replay_exact:
            raise ValueError("Full nested development replay differs")
    return seal({"schema_version": "apex-compound-bounded-offline-verification-v9",
                 "verification_source_sha256_lf": canonical_file_sha(Path(__file__)),
                 "calibration_sha256": frozen["content_sha256"], "dataset_sha256": data["content_sha256"],
                 "results_sha256": results["content_sha256"], "development_sha256": development["content_sha256"],
                 "bounded_coefficients_refit_exact": True, "event_coefficients_refit_exact": True,
                 "calibration_refit_exact": True, "prospective_replay_exact": True,
                 "full_nested_development_replay_exact": replay_exact,
                 "development_scalar_cases_audited": development_audit["cases_audited"],
                 "development_native_context_cases_audited": native_context["cases_audited"],
                 "development_field_contributions_audited": native_context["field_contributions_audited"],
                 "prospective_native_scalar_cases_audited": confirmation_audit["cases_audited"],
                 "prospective_field_contributions_audited": confirmation_audit["field_contributions_audited"],
                 "future_target_mutation_cases": len(results["cases"]), "artifact_verification_passed": True,
                 "candidate_accepted": results["passed"], "production_promotion": False,
                 "audit_scope": "ALL_PUBLISHED_CASES_AND_CONTEXT_NOT_FULL_EXCLUDED_COHORT_ENUMERATION"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--development-replay", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, verify(args.archive, development_replay=args.development_replay))
