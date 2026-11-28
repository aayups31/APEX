"""Screen R050 sector traffic adjustments against the R041 crossover gates."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from statistics import median

from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.green_traffic import SectorTrafficCalibration
from audit_compound_outlap_support import EVENTS
from audit_compound_race_context import check_result
from compound_driving_data import car_snapshot, sample_matrix
from compound_field_evolution import score
from compound_sector_traffic import feature_vectors, load_sources
from confirm_compound_multiseason import canonical_file_sha
from fit_green_traffic_r050 import load_drs
from fit_sector_traffic_r050 import sector_drs
from prepare_compound_pit_exit import BASE, FOLDER

PROTOCOL = BASE / "research/protocols/COMPOUND_SECTOR_PACE_V33.md"


def calibration(traffic, cases):
    """Fit the fixed terms from the 2022 panel, outside every R041 fold."""
    archive_events = {"F1_2022_R03", "F1_2022_R05", "F1_2022_R17"}
    if traffic["schema"] != "apex-r050-sector-traffic-v1" or any(
        datetime.fromtimestamp(row["forecast_at_s"], timezone.utc).year <= 2022 for row in cases
    ):
        raise ValueError("R041 traffic correction requires a disjoint 2022 calibration")
    effects = {}
    for term in ("following", "drs"):
        races = traffic["panels"]["2022"][term]["races"]
        if set(races) != archive_events:
            raise ValueError("R050 calibration race inventory changed")
        effects[term] = median(race["median_s"] for race in races.values())
    if (
        not all(isfinite(value) for value in effects.values())
        or not effects["following"] > 0 > effects["drs"]
    ):
        raise ValueError("R050 calibration terms are outside historical support")
    return SectorTrafficCalibration(effects["following"], effects["drs"])


def archive_telemetry(event, source, native_root, telemetry_source, drivers):
    """Reload the exact verified native archive or v24 car-data receipts."""
    if source["archive_sha256"] != telemetry_source["archive_sha256"]:
        raise ValueError("R041 lap and telemetry archive identities differ")
    if source["provider"] == "FASTF1":
        _, year, label = event.split("_")
        number = int(label[1:])
        folder = (
            f"fastf1-2024-r{number}-race-20261011"
            if year == "2024"
            else f"r026-fastf1-2023-r{number}-race-20261013"
        )
        path = native_root / folder
        archive = verify_fastf1_archive(path)
        if archive["content_sha256"] != source["archive_sha256"]:
            raise ValueError("FastF1 car data differs from the R041 cohort")
        origin = datetime.fromisoformat(archive["identity"]["t0_date"]).replace(tzinfo=timezone.utc)
        return origin.timestamp(), load_drs(path / "tables")

    traces = {}
    for driver in sorted(drivers):
        expected = telemetry_source["drivers"][str(driver)]
        cache = "r041-v23-native-car" if expected["reused_v23"] else "r041-v24-native-car"
        root = native_root / cache
        receipt = read_json(root / f"{event}-{driver}.receipt.json")
        check_seal(receipt)
        if receipt["content_sha256"] != expected["sha256"]:
            raise ValueError("R041 telemetry receipt differs from the frozen inventory")
        rows, _ = car_snapshot(root, event, driver, receipt["query"], None)
        samples = sample_matrix(rows, event, driver)
        traces[str(driver)] = samples[:, 0], samples[:, 4]
    return 0.0, traces


def states(row, groups, trace, origin):
    """Classify the six eligible sector slots per history window."""
    feature_vectors(row, groups)
    cutoff = row["forecast_at_s"]
    history = []
    for laps in groups:
        window = []
        for lap in laps:
            if len(lap) != 3 or trace is None:
                window.extend((None, None))
                continue
            finish, one, two = lap
            for (start, ahead), (end, after) in ((one, two), (two, finish)):
                if not start < end <= cutoff:
                    raise ValueError("Sector observation exceeds the R041 forecast cutoff")
                if ahead is None or after is None or ahead[1] != after[1]:
                    window.append(None)
                    continue
                gap = start - ahead[0]
                if not (0 < gap <= 1 or 2 <= gap <= 4):
                    window.append(None)
                    continue
                opened = sector_drs(trace, start - origin, end - origin)
                if opened is None or (gap >= 2 and opened):
                    window.append(None)
                elif gap >= 2:
                    window.append("reference")
                else:
                    window.append("drs" if opened else "close")
        history.append(window)
    return history


def features(history, model):
    values = {"reference": 0.0, "close": model.close_following_s, "drs": model.adjustment(0.5, drs_open=True)}
    shifts = [sum(values[s] for s in window if s is not None) / 3 for window in history]
    support = [sum(s is not None for s in window) / 6 for window in history]
    return shifts, support


def evaluate(data, control, base, histories, model):
    inputs = [features(history, model) for history in histories]
    support_only = score(data, [x + support for x, (_, support) in zip(base, inputs, strict=True)])
    result = score(data, [x + shifts + support for x, (shifts, support) in zip(base, inputs, strict=True)])
    baseline = control["results"]["nomination_practice_ridge"]
    failed = set(result["failed_events"])
    prior_failed = set(baseline["failed_events"])
    repaired = sorted(set(EVENTS) - failed)
    flags = {
        "development_qualified": result["qualified"],
        "new_holdout_acquisition_allowed": result["qualified"],
    }
    return {
        "result": result,
        "support_only": support_only,
        "gained_events": sorted(prior_failed - failed),
        "lost_events": sorted(failed - prior_failed),
        "persistent_failures_passing": repaired,
        "continue_direction": (
            len(failed) < len(prior_failed)
            and bool(repaired)
            and result["macro_mae_s"] < support_only["macro_mae_s"]
        ),
        "audit": check_result(data, seal({"result": result, **flags})),
        **flags,
    }


def run(root):
    data, control, base = load_sources()
    timing, inventory, traffic = [
        read_json(FOLDER / name)
        for name in (
            "compound-v30-development.json",
            "compound-v24-telemetry.json",
            "r050-sector-traffic.json",
        )
    ]
    for source in (timing, inventory, traffic):
        check_seal(source)
    if (
        data["content_sha256"] != timing["dataset_sha256"]
        or data["content_sha256"] != inventory["dataset_sha256"]
        or control["content_sha256"] != timing["control_sha256"]
    ):
        raise ValueError("R041 traffic study parents describe a different cohort")
    model = calibration(traffic, data["cases"])
    cohorts = defaultdict(list)
    for i, row in enumerate(data["cases"]):
        cohorts[str(row["session"])].append((i, row))
    histories, coverage = [None] * len(data["cases"]), {}
    for event, cases in sorted(cohorts.items()):
        origin, traces = archive_telemetry(
            event,
            data["sources"][event],
            root,
            inventory["sources"][event],
            {row["driver"] for _, row in cases},
        )
        support = Counter()
        for i, row in cases:
            history = states(row, timing["links"][i], traces.get(str(row["driver"])), origin)
            histories[i] = history
            observed = {s for window in history for s in window if s is not None}
            support.update(observed)
            support["any"] += bool(observed)
            support["close_or_drs"] += bool(observed & {"close", "drs"})
        coverage[event] = {"cases": len(cases), **support}
    return seal(
        {
            "schema": "compound-sector-pace-v33",
            "dataset_sha256": data["content_sha256"],
            "control_sha256": control["content_sha256"],
            "timing_sha256": timing["content_sha256"],
            "telemetry_sha256": inventory["content_sha256"],
            "traffic_sha256": traffic["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "traffic_coefficients_s": {"following": model.close_following_s, "drs": model.drs_delta_s},
            "coverage": coverage,
            "histories": histories,
            **evaluate(data, control, base, histories, model),
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
