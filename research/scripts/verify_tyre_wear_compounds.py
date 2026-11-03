"""Run the frozen R040/R041 research protocol against local sealed inputs."""
import argparse
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.examples.recovery_study import load_recovery
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.aero_bicycle import aero_bicycle_rhs
from apexsim.research.bicycle import BicycleControl, BicycleState
from apexsim.research.evidence import (
    check_seal,
    finish_run,
    read_json,
    verify_inventory,
)
from apexsim.research.transparent_driver import AERO, CAR
from apexsim.research.tyre_wear import wear_step
from scipy.optimize import lsq_linear

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")
TRAIN = (1, 3, 6)
TEST = (16, 18)


def wear_replay(recovery, thermal):
    parent, results = load_recovery(recovery)
    inventory = verify_inventory(thermal, "apex-tyre-thermal-v1")
    summary = read_json(thermal/"summary.json")
    check_seal(summary)
    if (not parent["task_closure_eligible"] or not summary["passed"]
            or summary["recovery_sha256"] != parent["content_sha256"]
            or inventory["summary_sha256"] != summary["content_sha256"]):
        raise ValueError("Wear requires bound, passing recovery and thermal artifacts")
    cases = [c["case_id"] for c in results["cases"] if c["actor"] == "learned"
             and c["scenario"] == "nominal" and c["max_step_s"] == .02]
    rows, paths = [], {}
    with (np.load(recovery/"trajectories.npz", allow_pickle=False) as src,
          np.load(thermal/"thermal_trajectories.npz", allow_pickle=False) as temp):
        if len(cases) != 4 or set(cases) != set(temp.files):
            raise ValueError("Wear requires the complete four-case thermal catalog")
        for key in cases:
            states, actions, times = (src[key+"__"+field] for field in ("states", "controls", "time_s"))
            temperatures = temp[key]
            energy = []
            for i, dt in enumerate(np.diff(times)):
                _, diag = aero_bicycle_rhs(BicycleState.from_array(states[i]), BicycleControl(*actions[i]), CAR, AERO)
                w = diag.wrench
                work = -dt*np.array([w.front.fy_n*w.front_wheel_vy_mps, w.rear.fy_n*w.rear_wheel_vy_mps])
                if np.any(work < -1e-9):
                    raise ValueError("Positive lateral mechanical work")
                energy.append(np.maximum(work, 0))
            energy = np.array(energy)
            tread = temperatures[:-1, :, 0]
            wear = np.zeros((len(times), 2))
            for i, (work, temperature) in enumerate(zip(energy, tread, strict=True)):
                wear[i+1] = [wear_step(wear[i, j], work[j], temperature[j]) for j in range(2)]
            dose = np.cumsum(1e-7*energy*np.exp((tread-333.15)/40), axis=0)
            error = float(np.max(abs(wear[1:] + np.expm1(-dose))))
            if (error > 1e-12 or np.any(np.diff(wear, axis=0) < 0)
                    or np.any(wear > 1) or not np.all(-np.expm1(-dose[-1]*2) > wear[-1])
                    or not np.all(-np.expm1(-dose[-1]*np.exp(.25)) > wear[-1])):
                raise ValueError("Wear replay violated dose, bounds, or sensitivity")
            paths[key+"__wear"] = wear
            paths[key+"__sliding_j"] = energy
            rows.append({"case_id": key, "intervals": len(energy), "maximum_dose_difference": error,
                         "sliding_j": energy.sum(axis=0).tolist(), "final_wear": wear[-1].tolist()})
    return {"thermal_sha256": summary["content_sha256"], "cases": rows, "passed": True}, paths


def design(compound, age, separate):
    indicators = np.array([compound == c for c in COMPOUNDS], dtype=float)
    return np.r_[indicators[:2], indicators*age if separate else age]


def fit(groups, separate):
    matrices, targets = [], []
    for observations in groups.values():
        x = np.stack([design(c, a, separate) for c, a, _ in observations])
        y = np.array([y for _, _, y in observations])
        weight = np.sqrt(len(y))
        matrices.append((x-x.mean(axis=0))/weight)
        targets.append((y-y.mean())/weight)
    x, y = np.concatenate(matrices), np.concatenate(targets)
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError("Training compound contrasts are not identifiable")
    solution = lsq_linear(x, y, bounds=([-np.inf]*2+[0.]*(x.shape[1]-2), np.inf))
    if not solution.success:
        raise ValueError("Compound prior optimization failed")
    return solution.x


def crossovers(ages, values):
    """Midpoint of adjacent contiguous three-age windows with opposite median signs."""
    crossings = []
    for i in range(3, len(ages)-2):
        if ages[i+2]-ages[i-3] != 5:
            continue
        left, right = np.median(values[i-3:i]), np.median(values[i:i+3])
        if left*right < 0 and min(abs(left), abs(right)) > .15:
            crossings.append((ages[i-1]+ages[i])/2)
    return crossings


def compound_study(dataset):
    for event in TRAIN+TEST:
        assert_development_event(2024, event)
    data = read_json(dataset)
    check_seal(data)
    groups = defaultdict(list)
    for segment in data["segments"]:
        event = segment["round_number"]
        assert_development_event(segment["season"], event, event_id=segment["event_id"])
        if segment["season"] != 2024 or event not in TRAIN+TEST:
            raise ValueError("Unexpected compound study event")
        for row in segment["rows"]:
            age, pace = row["tyre_age"], row["corrected_s"]
            if not np.isfinite([age, pace]).all() or age < 0 or age != int(age) or segment["compound"] not in COMPOUNDS:
                raise ValueError("Invalid compound observation")
            groups[event, segment["driver"]].append((segment["compound"], age, pace))
    training = {k: v for k, v in groups.items() if k[0] in TRAIN}
    coefficients, baseline = fit(training, True), fit(training, False)
    cases, metrics = [], []
    for event in TEST:
        errors, shared_errors, matched, observed, directions = [], [], 0, 0, []
        for (round_number, driver), rows in sorted(groups.items()):
            if round_number != event:
                continue
            values = defaultdict(list)
            for compound, age, pace in rows:
                values[compound, age].append(pace)
            for a, b in combinations(COMPOUNDS, 2):
                ages = sorted({age for c, age in values if c == a and (b, age) in values})
                if not ages:
                    continue
                actual = np.array([np.median(values[a, age])-np.median(values[b, age]) for age in ages])
                pred = np.array([(design(a, age, True)-design(b, age, True))@coefficients for age in ages])
                shared = (design(a, 0, False)-design(b, 0, False))@baseline
                errors.extend(abs(pred-actual))
                shared_errors.extend(abs(shared-actual))
                directions.extend(np.sign(pred)==np.sign(actual))
                crossings = crossovers(ages, actual)
                predicted = crossovers(ages, pred)
                hits = sum(any(abs(x-y) <= 5 for y in predicted) for x in crossings)
                observed += len(crossings)
                matched += hits
                cases.append({"round": event, "driver": driver, "compounds": [a, b], "ages": ages,
                              "observed_s": actual.tolist(), "predicted_s": pred.tolist(),
                              "observed_crossovers": crossings, "predicted_crossovers": predicted})
        mae = float(np.mean(errors)) if errors else None
        shared_mae = float(np.mean(shared_errors)) if shared_errors else None
        metrics.append({"round": event, "contrasts": len(errors), "observed_crossovers": observed, "matched": matched,
                        "mae_s": mae, "shared_slope_mae_s": shared_mae,
                        "direction_agreement": float(np.mean(directions)) if directions else None,
                        "passed": observed > 0 and 2*matched >= observed and mae <= shared_mae})
    return {"dataset_sha256": data["content_sha256"], "train_rounds": TRAIN, "test_rounds": TEST,
            "compound_order": COMPOUNDS, "offsets_s": [*coefficients[:2].tolist(), 0.],
            "age_slopes_s_per_lap": coefficients[2:].tolist(), "baseline": baseline.tolist(),
            "truth": "EFFECTIVE_FUEL_CORRECTED_PACE_PROXY", "events": metrics, "cases": cases,
            "passed": all(r["passed"] for r in metrics)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery", type=Path, required=True)
    parser.add_argument("--thermal", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    wear, arrays = wear_replay(args.recovery, args.thermal)
    compounds = compound_study(args.dataset)
    write_manifest(args.output/"wear.json", wear)
    write_manifest(args.output/"compounds.json", compounds)
    np.savez_compressed(args.output/"wear.npz", **arrays)
    print(finish_run(args.output, "apex-wear-compound-v1", {
        "wear_passed": wear["passed"], "compound_passed": compounds["passed"],
        "source_sha256": file_sha256(Path(__file__)), "production_promotion": False,
    }))


if __name__ == "__main__":
    main()
