"""Run the registered, archive-verified R050 green traffic evaluation."""

import argparse
from bisect import bisect_left
from collections import defaultdict
from itertools import pairwise, product
from math import isfinite, log, log1p
from pathlib import Path
from statistics import mean, median

import pandas as pd
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.green_traffic import fit_green_traffic
from archive_r050_overtakes import cohort, validate_passes
from calibrate_pit_timing import BASE
from confirm_compound_crossover import timestamp
from fit_traffic_drs_proxy import drs_history

LAP_FIELDS = [
    "DriverNumber",
    "LapNumber",
    "Time",
    "LapStartTime",
    "LapTime",
    "TyreLife",
    "Stint",
    "TrackStatus",
    "IsAccurate",
    "PitInTime",
    "PitOutTime",
    "Deleted",
    "FastF1Generated",
]


def lap_timing(table):
    laps, clean = defaultdict(dict), defaultdict(dict)
    for row in table.itertuples(index=False):
        lap, driver = int(row.LapNumber), str(row.DriverNumber)
        if driver in laps[lap]:
            raise ValueError(f"Duplicate timing of car {driver} on lap {lap}")
        laps[lap][driver] = row.Time.total_seconds()
        if (
            row.TrackStatus == "1"
            and row.IsAccurate
            and not row.Deleted
            and not row.FastF1Generated
            and pd.isna(row.PitInTime)
            and pd.isna(row.PitOutTime)
            and pd.notna(row.LapStartTime)
            and pd.notna(row.LapTime)
            and row.Time > row.LapStartTime
        ):
            clean[lap][driver] = row
    return laps, clean


def load_drs(tables):
    telemetry = {}
    for file in sorted((tables / "car_data").glob("*.parquet")):
        samples = pd.read_parquet(file, columns=["SessionTime", "DRS"])
        samples = samples.dropna(subset=["SessionTime"]).sort_values("SessionTime", kind="stable")
        telemetry[file.stem] = (
            samples.SessionTime.dt.total_seconds().to_numpy(),
            samples.DRS.astype(float).to_numpy(),
        )
    return telemetry


def extract(table, telemetry, overtakes, utc_origin):
    laps, clean = lap_timing(table.dropna(subset=["DriverNumber", "LapNumber", "Time"]))
    exchange = defaultdict(list)
    for row in overtakes:
        pair = (str(row["overtaken_driver_number"]), str(row["overtaking_driver_number"]))
        exchange[pair].append(timestamp(row["date"]) - utc_origin)
    for clocks in exchange.values():
        clocks.sort()
    ordered = {
        lap: dict((follower, leader) for leader, follower in pairwise(sorted(field, key=field.__getitem__)))
        for lap, field in laps.items()
    }

    def has_exchange(leader, follower, start, end):
        clocks = exchange.get((leader, follower), ())
        i = bisect_left(clocks, start)
        return i < len(clocks) and clocks[i] <= end

    def drs(driver, row):
        if driver not in telemetry:
            return None
        return drs_history(*telemetry[driver], row.LapStartTime.total_seconds(), row.Time.total_seconds())

    transitions, pace = [], defaultdict(list)
    for lap in sorted(ordered):
        if lap < 3:
            continue
        for follower, leader in ordered[lap].items():
            next_clean = clean.get(lap + 1, {})
            if follower not in next_clean or leader not in next_clean:
                continue
            gap = laps[lap][follower] - laps[lap][leader]
            if not 0 < gap <= 4:
                continue
            current, previous = clean.get(lap, {}), clean.get(lap - 1, {})
            if follower not in current or leader not in current:
                continue
            start = laps[lap][follower]
            end = max(laps[lap + 1][follower], laps[lap + 1][leader])
            if end <= start or min(laps[lap + 1][follower], laps[lap + 1][leader]) <= start:
                continue
            logged = has_exchange(leader, follower, start, end + 2)
            next_gap = laps[lap + 1][follower] - laps[lap + 1][leader]
            if gap <= 2 and follower in previous and leader in previous:
                transitions.append(
                    {
                        "lap": lap,
                        "leader": leader,
                        "follower": follower,
                        "gap_s": gap,
                        "pace_delta_s": (current[follower].LapTime - current[leader].LapTime).total_seconds(),
                        "prior_drs": drs(follower, current[follower]),
                        "next_gap_s": next_gap,
                        "logged": logged,
                        "pass": logged and next_gap < 0,
                    }
                )
            if (
                ordered[lap + 1].get(follower) != leader
                or logged
                or has_exchange(follower, leader, start, end + 2)
                or 1 < gap < 2
            ):
                continue
            row = next_clean[follower]
            opened = drs(follower, row)
            if opened is None or (gap >= 2 and opened):
                continue
            if not isfinite(row.Stint) or not isfinite(row.TyreLife) or current[follower].Stint != row.Stint:
                continue
            state = "drs" if opened else ("close" if gap <= 1 else "clear")
            pace[(follower, int(row.Stint))].append(
                (state, lap + 1, row.TyreLife, row.LapTime.total_seconds())
            )
    return transitions, pace


def matched_pace(groups):
    contrasts = {"following": [], "drs": []}
    for rows in groups.values():
        for term, treated, control in (("following", "close", "clear"), ("drs", "drs", "close")):
            a = (r for r in rows if r[0] == treated)
            b = (r for r in rows if r[0] == control)
            candidates = sorted(
                (abs(t[2] - c[2]), t[1], c[1], t[3] - c[3], t[2] - c[2])
                for t, c in product(a, b)
                if abs(t[2] - c[2]) <= 5
            )
            seen_t, seen_c = set(), set()
            for _, lap_t, lap_c, diff, age in candidates:
                if lap_t in seen_t or lap_c in seen_c:
                    continue
                seen_t.add(lap_t)
                seen_c.add(lap_c)
                contrasts[term].append((diff, age))
    return contrasts


def score(model, rows):
    if not rows:
        raise ValueError("No eligible clean green transitions")
    scored = [
        (
            row,
            model.forecast(row["gap_s"], row["pace_delta_s"], row["prior_drs"]),
        )
        for row in rows
    ]
    metrics = {
        "cases": len(rows),
        "passes": sum(r["pass"] for r in rows),
        "timing_reversals": sum(r["next_gap_s"] < 0 for r in rows),
        "logged_without_reversal": sum(r["logged"] and r["next_gap_s"] >= 0 for r in rows),
        "unknown_prior_drs": sum(r["prior_drs"] is None for r in rows),
        "gap_model_mae_s": mean(abs(p.signed_gap_s - r["next_gap_s"]) for r, p in scored),
        "gap_persistence_mae_s": mean(abs(r["gap_s"] - r["next_gap_s"]) for r in rows),
        "gap_pace_extrapolation_mae_s": mean(
            abs(r["gap_s"] + r["pace_delta_s"] - r["next_gap_s"]) for r in rows
        ),
    }
    for label, probabilities in (
        ("model", [p.corroborated_pass_probability for _, p in scored]),
        ("pooled", [model.pooled_pass_probability] * len(rows)),
    ):
        outcomes = [r["pass"] for r in rows]
        metrics[f"pass_{label}_expected"] = sum(probabilities)
        metrics[f"pass_{label}_brier"] = mean(
            (p - y) ** 2 for p, y in zip(probabilities, outcomes, strict=True)
        )
        metrics[f"pass_{label}_log_loss"] = mean(
            -log(p) if y else -log1p(-p) for p, y in zip(probabilities, outcomes, strict=True)
        )
    return metrics


def pace_summary(by_race):
    result = {}
    for term in ("following", "drs"):
        races = {}
        for event, contrasts in by_race.items():
            values = contrasts[term]
            races[event] = {
                "pairs": len(values),
                "median_s": median(diff for diff, _ in values) if values else None,
                "mean_age_difference_laps": mean(age for _, age in values) if values else None,
            }
        medians = [v["median_s"] for v in races.values() if v["median_s"] is not None]
        result[term] = {
            "pairs": sum(v["pairs"] for v in races.values()),
            "median_race_effect_s": median(medians) if medians else None,
            "observed_race_effect_range_s": [min(medians), max(medians)] if medians else None,
            "races": races,
        }
    return result


def evaluate(training, evaluation, training_pace, evaluation_pace):
    train = [row for rows in training.values() for row in rows]
    holdout = [row for rows in evaluation.values() for row in rows]
    selection = {}
    for drs in (False, True):
        selection[drs] = {
            event: score(
                fit_green_traffic(
                    [row for other, fold in training.items() if other != event for row in fold],
                    use_prior_drs=drs,
                ),
                rows,
            )["pass_model_brier"]
            for event, rows in training.items()
        }
    use_prior = mean(selection[True].values()) < mean(selection[False].values())
    model = fit_green_traffic(train, use_prior_drs=use_prior)
    challenger = fit_green_traffic(train, use_prior_drs=not use_prior)
    folds = {event: score(model, rows) for event, rows in evaluation.items()}
    pooled = score(model, holdout)
    pace_train = pace_summary(training_pace)
    pace_test = pace_summary(evaluation_pace)
    gates = {
        "pass_support": (
            sum(r["pass"] for r in train) >= 25
            and pooled["passes"] >= 25
            and all(f["passes"] >= 1 for f in folds.values())
            and pooled["passes"] * 2 > pooled["timing_reversals"]
        ),
        "pass_score": (
            pooled["pass_model_brier"] < pooled["pass_pooled_brier"]
            and pooled["pass_model_log_loss"] < pooled["pass_pooled_log_loss"]
        ),
        "gap_score": (
            pooled["gap_model_mae_s"]
            < min(pooled["gap_persistence_mae_s"], pooled["gap_pace_extrapolation_mae_s"])
            and sum(f["gap_model_mae_s"] < f["gap_persistence_mae_s"] for f in folds.values()) >= 3
        ),
    }
    for term, expected_sign in (("following", 1), ("drs", -1)):
        effect = pace_train[term]["median_race_effect_s"]
        gates[f"{term}_pace"] = (
            min(pace_train[term]["pairs"], pace_test[term]["pairs"]) >= 25
            and effect is not None
            and effect * expected_sign > 0
            and sum(
                r["median_s"] is not None and r["median_s"] * expected_sign > 0
                for r in pace_test[term]["races"].values()
            )
            >= 3
        )
    return {
        "calibration": model.to_dict(),
        "training_pass_selection_brier": {"gap_pace": selection[False], "gap_pace_drs": selection[True]},
        "training": score(model, train),
        "held_out": pooled,
        "alternate_pass_held_out": score(challenger, holdout),
        "held_out_races": folds,
        "training_pace": pace_train,
        "held_out_pace": pace_test,
        "gates": gates,
        "qualified": all(gates.values()),
    }


def run(native_root, pass_root):
    manifest = read_json(pass_root / "manifest.json")
    check_seal(manifest)
    transitions, pace, sources = {}, {}, {}
    for event, year, native, expected in cohort(native_root):
        archive = verify_fastf1_archive(native)
        metadata = manifest["events"][event]
        identity = metadata["identity"]
        origin = archive["identity"]["t0_date"]
        path = pass_root / f"{event}-overtakes.json"
        if (
            archive["content_sha256"] != expected
            or identity["year"] != year
            or identity["session_name"] != "Race"
            or identity["date_start"][:10] != origin[:10]
            or path.name != metadata["filename"]
            or file_sha256(path) != metadata["file_sha256"]
        ):
            raise ValueError(f"R050 source mismatch for {event}")
        overtakes = read_json(path)
        validate_passes(overtakes, identity)
        tables = native / "tables"
        laps = pd.read_parquet(tables / "laps.parquet", columns=LAP_FIELDS)
        rows, groups = extract(laps, load_drs(tables), overtakes, timestamp(f"{origin}+00:00"))
        transitions[event] = rows
        pace[event] = matched_pace(groups)
        sources[event] = {
            "fastf1_sha256": expected,
            "openf1_sha256": metadata["file_sha256"],
            "openf1_session_key": identity["session_key"],
            "openf1_log_rows": len(overtakes),
        }

    def partition(data, season):
        return {event: values for event, values in data.items() if event.startswith(f"F1_{season}_")}

    return seal(
        {
            "schema": "apex-r050-green-traffic-v1",
            "sources": sources,
            "openf1_archive_sha256": manifest["content_sha256"],
            **evaluate(
                partition(transitions, 2023),
                partition(transitions, 2024),
                partition(pace, 2023),
                partition(pace, 2024),
            ),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--pass-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root, args.pass_archive))
