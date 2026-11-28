"""Fit and validate R048 cause-specific competing retirement hazards."""

import argparse
import csv
import io
from collections import defaultdict
from math import log
from pathlib import Path
from zipfile import ZipFile

from apexsim.data.benchmark_guard import protected_events
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import seal
from calibrate_pit_timing import BASE, canonical_file_sha

ARCHIVE_SHA256 = "8c33f41f7e095e995634305a33b28bd8638366056f877109ffc290d06d341950"
PROTOCOL = BASE / "research/protocols/CAUSE_HAZARDS_R048.md"
RELIABILITY_PROTOCOL = BASE / "research/protocols/CAUSE_HAZARD_RELIABILITY_R048.md"
OUTCOMES = ("stay", "incident", "mechanical")
TRAIN = (2022, 2023)
TEST = (2024, 2025)
INCIDENT = frozenset(
    {"accident", "collision", "collision damage", "crash", "spun off", "spin"}
)
MECHANICAL = frozenset(
    {
        "mechanical",
        "engine",
        "power unit",
        "gearbox",
        "transmission",
        "clutch",
        "hydraulics",
        "electrical",
        "electronics",
        "battery",
        "suspension",
        "brakes",
        "brake",
        "driveshaft",
        "differential",
        "exhaust",
        "turbo",
        "turbocharger",
        "fuel pump",
        "fuel pressure",
        "oil pressure",
        "oil leak",
        "water leak",
        "water pressure",
        "overheating",
        "ERS".lower(),
        "cooling",
        "coolant leak",
        "steering",
        "throttle",
        "fuel system",
        "fuel leak",
    }
)


def classify(row):
    """Map explicit published retirement causes and preserve unresolved cases."""
    status = row["positionText"].strip().upper()
    reason = row["reasonRetired"].strip().casefold()
    if status in {"DNS", "DNQ", "DNP", "DNPQ", "EX"}:
        return "excluded"
    if reason in INCIDENT:
        return "incident"
    if reason in MECHANICAL:
        return "mechanical"
    if reason or status in {"DNF", "NC"}:
        return "unknown"
    if status.isdigit() or status == "DSQ":
        return "censored"
    return "excluded"


def classify_corrected(row):
    status = row["positionText"].strip().upper()
    reason = row["reasonRetired"].strip().casefold()
    original = classify(row)
    if original == "excluded" or "formation lap" in reason:
        return "excluded"
    if status == "DSQ":
        return "censored"
    if reason == "accident damage":
        return "incident"
    if reason in {"cooling system", "power loss"}:
        return "mechanical"
    return original


def extract(results, reserved, classifier=classify):
    events = defaultdict(
        lambda: {
            "first": dict.fromkeys(OUTCOMES, 0),
            "later": dict.fromkeys(OUTCOMES, 0),
            "unknown": {},
            "excluded": 0,
            "labels": {},
        }
    )
    seen = set()
    for row in results:
        year, number = int(row["year"]), int(row["round"])
        if year not in (*TRAIN, *TEST) or (year, number) in reserved:
            continue
        identity = f"F1_{year}_R{number:02}"
        key = identity, row["driverId"]
        if key in seen:
            raise ValueError("Duplicate race-driver result")
        seen.add(key)
        event = events[identity]
        status = classifier(row)
        laps = row["laps"].strip()
        if status == "excluded" or not laps.isdigit():
            event["excluded"] += 1
            continue
        completed = int(laps)
        if completed:
            event["first"]["stay"] += 1
            event["later"]["stay"] += completed - 1
        if status in ("incident", "mechanical"):
            event["first" if not completed else "later"][status] += 1
        if status in ("unknown", "incident", "mechanical"):
            reason = row["reasonRetired"].strip() or "<missing cause>"
            event["labels"][row["driverId"]] = {
                "cause": status,
                "reason": reason,
                "completed_laps": completed,
            }
            if status == "unknown":
                event["unknown"][reason] = event["unknown"].get(reason, 0) + 1
    return dict(events)


def hazards(counts):
    total = sum(counts.values()) + 1.5
    return {k: (counts[k] + 0.5) / total for k in OUTCOMES}


def totals(events, band):
    return {k: sum(row[band][k] for row in events.values()) for k in OUTCOMES}


def coverage(events):
    known = sum(
        sum(r[b][k] for b in ("first", "later") for k in OUTCOMES[1:])
        for r in events.values()
    )
    unknown = sum(sum(r["unknown"].values()) for r in events.values())
    return {"known": known, "unknown": unknown, "fraction": known / (known + unknown)}


def project_reliability(train, model):
    rates = {}
    for year in TRAIN:
        season = {e: row for e, row in train.items() if int(e[3:7]) == year}
        counts = [totals(season, band) for band in ("first", "later")]
        rates[year] = (sum(n["mechanical"] for n in counts) + 0.5) / (
            sum(sum(n.values()) for n in counts) + 1
        )
    ratio = rates[TRAIN[-1]] / rates[TRAIN[0]]
    forecasts = {}
    for year in TEST:
        mechanical = rates[TRAIN[-1]] * ratio ** (year - TRAIN[-1])
        forecasts[year] = {
            band: {
                "stay": 1 - mechanical - risk["incident"],
                "incident": risk["incident"],
                "mechanical": mechanical,
            }
            for band, risk in model.items()
        }
        if any(
            not 0 < value < 1
            for risk in forecasts[year].values()
            for value in risk.values()
        ):
            raise ValueError("Invalid extrapolated R048 hazard")
    return forecasts, {
        "training_rates": {str(y): p for y, p in rates.items()},
        "annual_rate_ratio": ratio,
    }


def score(events, *, reliability=False):
    train = {e: r for e, r in events.items() if int(e[3:7]) in TRAIN}
    test = {e: r for e, r in events.items() if int(e[3:7]) in TEST}
    if len(train) < 20 or len(test) < 20:
        raise ValueError("Incomplete R048 season inventory")
    a, b = (totals(train, band) for band in ("first", "later"))
    const = hazards({k: a[k] + b[k] for k in OUTCOMES})
    model = {"first": hazards(a), "later": hazards(b)}
    by_year = dict.fromkeys(TEST, model)
    trend = None
    if reliability:
        by_year, trend = project_reliability(train, model)
    folds = {}
    for event, row in sorted(test.items()):
        event_model = by_year[int(event[3:7])]
        candidate_loss = pooled_loss = 0.0
        observed = dict.fromkeys(OUTCOMES[1:], 0)
        expected = dict.fromkeys(OUTCOMES[1:], 0.0)
        for band in ("first", "later"):
            n = sum(row[band].values())
            for k in OUTCOMES:
                count = row[band][k]
                candidate_loss -= count * log(event_model[band][k])
                pooled_loss -= count * log(const[k])
                if k != "stay":
                    observed[k] += count
                    expected[k] += n * event_model[band][k]
        folds[event] = {
            "observed": observed,
            "expected_given_exposure": expected,
            "split_nll": candidate_loss,
            "constant_nll": pooled_loss,
        }

    def aggregate(rows):
        return {
            "observed": {k: sum(r["observed"][k] for r in rows) for k in OUTCOMES[1:]},
            "expected_given_exposure": {
                k: sum(r["expected_given_exposure"][k] for r in rows)
                for k in OUTCOMES[1:]
            },
            "split_nll": sum(r["split_nll"] for r in rows),
            "constant_nll": sum(r["constant_nll"] for r in rows),
        }

    result = aggregate(list(folds.values()))
    by_season = {
        str(y): aggregate([r for e, r in folds.items() if int(e[3:7]) == y])
        for y in TEST
    }
    label_coverage = {"training": coverage(train), "held_out": coverage(test)}
    ratios = {
        k: result["observed"][k] / result["expected_given_exposure"][k]
        for k in OUTCOMES[1:]
    }
    checks = {
        "label_coverage": all(r["fraction"] >= 0.90 for r in label_coverage.values()),
        "cause_support": all(v >= 20 for v in result["observed"].values()),
        "lower_log_loss": result["split_nll"] < result["constant_nll"],
        "aggregate_cause_calibration": all(
            0.67 <= ratio <= 1.50 for ratio in ratios.values()
        ),
    }
    return {
        "hazards": model,
        **(
            {
                "hazards_by_year": {str(y): v for y, v in by_year.items()},
                "reliability_trend": trend,
            }
            if reliability
            else {}
        ),
        "constant": const,
        "training_exposure": {"first": a, "later": b},
        "training_races": sorted(train),
        "held_out_races": sorted(test),
        "label_coverage": label_coverage,
        "folds": folds,
        "seasons": by_season,
        "observed_expected_ratios": ratios,
        "aggregate": result,
        "checks": checks,
        "passed": all(checks.values()),
    }


def run(archive, *, reliability=False):
    if file_sha256(archive) != ARCHIVE_SHA256:
        raise ValueError("F1DB release checksum mismatch")
    with ZipFile(archive) as file, file.open("f1db-races-race-results.csv") as raw:
        events = extract(
            csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig")),
            protected_events(),
            classify_corrected if reliability else classify,
        )
    return seal(
        {
            "schema": f"apex-r048-cause-hazards-v{2 if reliability else 1}",
            "archive_sha256": ARCHIVE_SHA256,
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(
                RELIABILITY_PROTOCOL if reliability else PROTOCOL
            ),
            "events": events,
            "result": score(events, reliability=reliability),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reliability-trend", action="store_true")
    args = parser.parse_args()
    write_manifest(args.output, run(args.archive, reliability=args.reliability_trend))
