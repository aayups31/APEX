"""R026 equal-event scores and hierarchical event/sequence uncertainty; no fitting."""
from __future__ import annotations

import numpy as np

COHORT = {
    "F1_2023_R01": "bahrain", "F1_2023_R03": "albert_park",
    "F1_2023_R14": "monza", "F1_2023_R15": "marina_bay",
}
EVENTS = tuple(COHORT)
REFERENCE_SEAL = "c8f538d7ae46ec06a46d9af1b37fb9e4fe7429ac3c942845976fe2ccf189fe9f"
CALENDAR_SEAL = "62f7dad20cf71d1a5b00a5c9476d95f7ca0972d4b16bdbae369f03cc034162c8"
PROXY_CONFIG_SEAL = "d0c1f651630c93e555369b1cf55ed73a40c93c32e16fc535231244d5b40c58c1"


def classify_tracks(metadata: list[dict], training_tracks: list[str]) -> dict[str, list[str]]:
    """Circuit novelty derives from actual training vocabulary, never test labels."""
    membership = {}
    for row in metadata:
        event, track = row["event_id"], row["track_id"]
        if event in membership and membership[event] != track:
            raise ValueError("An evaluation event changes circuit identity")
        membership[event] = track
    strata = {name: sorted(e for e, t in membership.items() if (t in training_tracks) == (name == "seen"))
              for name in ("seen", "unseen")}
    if any(len(events) < 2 or len({membership[e] for e in events}) < 2 for events in strata.values()):
        raise ValueError("Generalization requires two distinct event/circuit identities per stratum")
    return strata


def generalization_scores(actual: np.ndarray, predictions: dict[str, np.ndarray], metadata: list[dict],
                          training_tracks: list[str], family_members: dict[str, list[str]], *,
                          resamples: int = 500, seed: int = 2026) -> dict:
    """Frame metrics plus equal-event MSE with paired hierarchical cluster bootstrap.

    Family statistics average per-seed losses on the same examples, not predictions
    or resampled seeds. Intervals describe this small development cohort only.
    """
    if (actual.shape != (len(metadata), 3, 4) or not np.isfinite(actual).all()
            or np.any(actual < 0) or "persistence" not in predictions
            or type(resamples) is not int or resamples < 20):
        raise ValueError("Invalid matched generalization targets/bootstrap settings")
    strata = classify_tracks(metadata, training_tracks)
    losses = {}
    for name, values in predictions.items():
        if values.shape != actual.shape or not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError("Invalid finite nonnegative matched generalization predictions")
        error = values - actual
        losses[name] = np.column_stack((np.mean(error**2, axis=(1, 2)), np.mean(abs(error), axis=(1, 2)),
                                      np.mean(200*abs(error)/(abs(values)+abs(actual)+.001), axis=(1, 2))))
    for family, members in family_members.items():
        if not members or len(set(members)) != len(members) or not set(members).issubset(predictions):
            raise ValueError("Generalization family must list unique actual checkpoint members")
        losses[family + "_family"] = np.mean([losses[name] for name in members], axis=0)
    names = sorted(losses)
    cube = np.stack([losses[name] for name in names])
    clusters = {}
    identities = {}
    for index, row in enumerate(metadata):
        sequence = row["sequence_id"]
        identity = row["event_id"], row["track_id"], row["driver_id"], row["compound"]
        if sequence in identities and identities[sequence] != identity:
            raise ValueError("A bootstrap sequence crosses event/driver/compound identity")
        identities[sequence] = identity
        clusters.setdefault(row["event_id"], {}).setdefault(sequence, []).append(index)
    sufficient = {}
    points = {}
    for event, sequences in sorted(clusters.items()):
        sums = np.stack([cube[:, indices, 0].sum(axis=1) for _, indices in sorted(sequences.items())], axis=1)
        counts = np.array([len(indices) for _, indices in sorted(sequences.items())])
        sufficient[event] = sums, counts
        points[event] = sums.sum(axis=1)/counts.sum()
    rng = np.random.default_rng(seed)
    bootstrap = {}
    reports = {}
    base = names.index("persistence")
    for stratum, events in strata.items():
        samples = []
        for _ in range(resamples):
            event_values = []
            for event_index in rng.integers(0, len(events), len(events)):
                sums, counts = sufficient[events[event_index]]
                selection = rng.integers(0, len(counts), len(counts))
                event_values.append(sums[:, selection].sum(axis=1)/counts[selection].sum())
            samples.append(np.mean(event_values, axis=0))
        bootstrap[stratum] = np.array(samples)
        macro = np.mean([points[event] for event in events], axis=0)
        selected = np.array([i for i, row in enumerate(metadata) if row["event_id"] in events])
        reports[stratum] = {"events": events, "event_count": len(events),
                            "sequence_clusters": sum(len(clusters[event]) for event in events),
                            "origins": len(selected), "methods": {}}
        for i, name in enumerate(names):
            errors = cube[i, selected].mean(axis=0)
            interval = np.quantile(np.sqrt(bootstrap[stratum][:, i]), [.025, .975])
            difference = bootstrap[stratum][:, i]-bootstrap[stratum][:, base]
            paired = np.quantile(difference, [.025, .975])
            reports[stratum]["methods"][name] = {
                "frame_weighted": {"rmse_kj": float(np.sqrt(errors[0])), "mae_kj": float(errors[1]), "smape_percent": float(errors[2])},
                "equal_event_mse_kj2": float(macro[i]), "equal_event_rmse_kj": float(np.sqrt(macro[i])),
                "equal_event_rmse_interval_95_kj": interval.tolist(),
                "equal_event_mse_minus_persistence_kj2": float(macro[i]-macro[base]),
                "paired_mse_minus_persistence_interval_95_kj2": paired.tolist(),
                "relative_equal_event_rmse_improvement": float(1-np.sqrt(macro[i]/macro[base])) if macro[base]>0 else None,
                "aggregation": "average seed losses; not ensemble predictions" if name.endswith("_family") else "single checkpoint/control",
            }
    gap = {}
    for i, name in enumerate(names):
        intervals = np.quantile(bootstrap["unseen"][:, i]-bootstrap["seen"][:, i], [.025, .975])
        gap[name] = {"unseen_minus_seen_equal_event_mse_kj2":
                     reports["unseen"]["methods"][name]["equal_event_mse_kj2"]-reports["seen"]["methods"][name]["equal_event_mse_kj2"],
                     "interval_95_kj2": intervals.tolist(), "causal_track_effect": False}
    return {"strata": reports, "unseen_minus_seen": gap,
            "bootstrap": {"resamples": resamples, "seed": seed, "unit": "events then whole sequence clusters",
                          "paired_controls": True, "seeds_resampled": False,
                          "scope": "Only two events/circuits per stratum; descriptive cohort uncertainty, not broad population coverage"}}


def frozen_family_decision(scores: dict, selected_family: str) -> str:
    key = selected_family+"_family" if selected_family not in ("persistence", "trend") else selected_family
    supported = all(
        scores["strata"][stratum]["methods"][key]["relative_equal_event_rmse_improvement"] is not None
        and scores["strata"][stratum]["methods"][key]["relative_equal_event_rmse_improvement"] >= .01
        and scores["strata"][stratum]["methods"][key]["paired_mse_minus_persistence_interval_95_kj2"][1] < 0
        for stratum in ("seen", "unseen")
    )
    return "SUPPORTED_IN_FROZEN_DEVELOPMENT_COHORT" if supported else "NO_CROSS_TRACK_PROMOTION"
