"""R027 black-box temporal diagnostics; frozen models, SI histories and proxy kJ.

Block splices are diagnostic perturbations, not feasible or causal trajectories.
The preregistered protocol defines the support and reliability boundaries.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from scipy.stats import rankdata

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import payload_sha256
from apexsim.research.forecast_benchmark import (
    EVENTS,
    ForecastScaler,
    ForecastWindows,
    NativeBoostRegressor,
    flat_features,
    neural_model,
    neural_prediction,
    project_nonnegative,
    statistical_prediction,
    transparent_prediction,
)

Predictor = Callable[[np.ndarray, np.ndarray], np.ndarray]


@dataclass(frozen=True)
class TemporalPlayer:
    """A complete feature group in a half-open native-sample window."""

    name: str
    start: int
    stop: int
    fields: tuple[int, ...]


PLAYERS = tuple(
    TemporalPlayer(f"{name}_{start}:{start+2}", start, start+2, fields)
    for name, fields in (
        ("kinematics", (0, 3, 4, 5, 6, 7)),
        ("controls", (1, 2)),
        ("past_energy", (10, 11, 12, 13)),
    )
    for start in (0, 2, 4, 6)
)


def source_key(row: dict) -> tuple[str, str, str, int]:
    """Native origin identity; never includes a target or model outcome."""
    return row["event_id"], row["driver_id"], row["sequence_id"], row["origin_native_row"]


def guard_origins(metadata: list[dict]) -> None:
    """Fail closed on protected events and mixed/duplicate native identities."""
    identities: dict[str, tuple] = {}
    keys = set()
    events = set()
    for row in metadata:
        if row["event_id"] not in events:
            match = re.fullmatch(r"F1_(\d{4})_R(\d{2})", row["event_id"])
            if match is None:
                raise ValueError("Explanation requires canonical event identity")
            assert_development_event(int(match[1]), int(match[2]), event_id=row["event_id"])
            events.add(row["event_id"])
        key = source_key(row)
        identity = row["event_id"], row["driver_id"], row["compound"], row.get("track_id")
        if (type(key[3]) is not int or key[3] < 7 or key in keys
                or identities.get(row["sequence_id"], identity) != identity):
            raise ValueError("Explanation source identity/continuity contract failed")
        keys.add(key)
        identities[row["sequence_id"]] = identity


def select_origins(metadata: list[dict], per_cell: int = 16) -> tuple[list[int], list[int], dict]:
    """Metadata-only hashed cohort, paired with same-sequence next native origins."""
    guard_origins(metadata)
    if type(per_cell) is not int or not 1 <= per_cell <= 16:
        raise ValueError("Explanation per-cell budget must be in [1,16]")
    lookup = {source_key(m): i for i, m in enumerate(metadata)}
    cells: dict[tuple, list[int]] = {}
    for i, row in enumerate(metadata):
        cells.setdefault((row["event_id"], row["driver_id"]), []).append(i)
    selected, nearby, coverage = [], [], {}
    for cell, indices in sorted(cells.items()):
        chosen: dict[str, list[int]] = {}
        count = 0
        for i in sorted(indices, key=lambda j: payload_sha256([2728, source_key(metadata[j])])):
            row = metadata[i]
            sequence, native = row["sequence_id"], row["origin_native_row"]
            following = (*source_key(row)[:3], native+1)
            prior = chosen.setdefault(sequence, [])
            if following not in lookup or len(prior) >= 2 or any(abs(native-v) < 8 for v in prior):
                continue
            selected.append(i)
            nearby.append(lookup[following])
            prior.append(native)
            count += 1
            if count == per_cell:
                break
        coverage["/".join(cell)] = {"available": len(indices), "selected": count, "requested": per_cell}
    return selected, nearby, coverage


def donor_indices(training_metadata: list[dict], origin: dict, count: int = 8) -> list[int]:
    """Disjoint-sequence, training-only donors matching driver and compound."""
    if not training_metadata or {m["event_id"] for m in training_metadata} != set(EVENTS[:2]):
        raise ValueError("Explanation donors require exactly frozen training events")
    if type(count) is not int or count < 2:
        raise ValueError("Invalid explanation donor count")
    candidates = [i for i, row in enumerate(training_metadata)
                  if (row["driver_id"], row["compound"]) == (origin["driver_id"], origin["compound"])]
    ordered = sorted(candidates, key=lambda i: payload_sha256([2728, source_key(origin), source_key(training_metadata[i])]))
    chosen, sequences = [], set()
    for i in ordered:
        sequence = training_metadata[i]["sequence_id"]
        if sequence not in sequences:
            chosen.append(i)
            sequences.add(sequence)
            if len(chosen) == count:
                break
    return chosen if len(chosen) == count else []


class FrozenForecastPredictor:
    """Load one saved model once; inference inputs cannot contain future targets."""

    def __init__(self, path: Path | None, record: dict, scaler: ForecastScaler, vocabulary: dict):
        self.kind, self.scaler, self.vocabulary = record["kind"], scaler, vocabulary
        self.model = None
        if self.kind in ("persistence", "trend"):
            return
        if path is None:
            raise ValueError("Frozen prediction requires a checkpoint")
        if self.kind in ("linear", "ridge"):
            with np.load(path, allow_pickle=False) as data:
                self.coef, self.intercept = data["coef"].copy(), data["intercept"].copy()
        elif self.kind == "xgboost":
            self.model = NativeBoostRegressor()
            self.model.load_model(path)
        elif self.kind in ("gru", "lstm", "tft"):
            widths = tuple(len(vocabulary[k]) for k in ("driver_id", "compound", "track_id"))
            with torch.random.fork_rng(devices=[]):
                self.model = neural_model(self.kind, widths, record["hidden"])
                self.model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
            self.model.eval()
        else:
            raise ValueError("Unknown frozen explanation model family")

    def __call__(self, dynamic: np.ndarray, static: np.ndarray) -> np.ndarray:
        """Raw direct-horizon forecasts; no fitting, projection or target argument."""
        n = len(dynamic)
        data = ForecastWindows(dynamic, static, np.zeros((n, 3, 4)), [{} for _ in range(n)], self.vocabulary)
        if self.kind in ("persistence", "trend"):
            return transparent_prediction(data, self.kind)
        if self.kind in ("linear", "ridge"):
            result = flat_features(data, self.scaler) @ self.coef.T + self.intercept
            return self.scaler.inverse(result.reshape(n, 3, 4))
        if self.kind == "xgboost":
            return statistical_prediction(self.model, data, self.scaler)
        return neural_prediction(self.model, self.kind, data, self.scaler)


def replace_players(history: np.ndarray, donor: np.ndarray, indices: tuple[int, ...]) -> np.ndarray:
    """Copy diagnostic blocks; timing/static fields and inputs are never mutated."""
    if (history.shape != (8, 14) or donor.shape != (8, 14)
            or not np.isfinite(history).all() or not np.isfinite(donor).all()
            or len(set(indices)) != len(indices) or any(i not in range(len(PLAYERS)) for i in indices)):
        raise ValueError("Invalid finite temporal perturbation/history")
    result = history.copy()
    for i in indices:
        player = PLAYERS[i]
        result[player.start:player.stop, player.fields] = donor[player.start:player.stop, player.fields]
    return result


def rank_correlation(first: np.ndarray, second: np.ndarray) -> float | None:
    """Spearman with average tied ranks; constant vectors have no correlation."""
    if first.shape != second.shape or first.ndim != 1 or not np.isfinite([first, second]).all():
        raise ValueError("Invalid explanation ranking vectors")
    a, b = rankdata(first), rankdata(second)
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _order(scores: np.ndarray) -> np.ndarray:
    return np.argsort(-scores, kind="stable")


def temporal_explanation(predict: Predictor, history: np.ndarray, static: np.ndarray,
                         donors: np.ndarray, nearby: np.ndarray) -> tuple[dict, dict[str, np.ndarray]]:
    """Rank four donors, audit four independent donors and 16 random joint masks.

    Returns auditable diagnostics and raw prediction tensors. A ranking is issued
    as reliable only when the frozen independent-donor gate passes.
    """
    if donors.shape != (8, 8, 14) or nearby.shape != (8, 14):
        raise ValueError("Temporal explanations require eight complete donor histories")

    def evaluate(values: list[np.ndarray] | np.ndarray) -> np.ndarray:
        x = np.asarray(values, dtype=np.float32)
        result = predict(x, np.repeat(static[None], len(x), axis=0))
        if result.shape != (len(x), 3, 4) or not np.isfinite(result).all():
            raise ValueError("Invalid finite explanation predictor output")
        return result

    base_raw = evaluate([history, nearby])
    base, _ = project_nonnegative(base_raw)
    perturb_raw = evaluate([replace_players(history, d, (p,)) for d in donors for p in range(12)]).reshape(8, 12, 3, 4)
    delta = np.maximum(perturb_raw, 0)-base[0]
    scores = np.mean(abs(delta[:4]), axis=0)
    audit_scores = np.mean(abs(delta[4:]), axis=0)
    rank, audit_rank = _order(scores.mean(axis=(1, 2))), _order(audit_scores.mean(axis=(1, 2)))
    top, bottom = tuple(rank[:3]), tuple(rank[-3:])
    heldout = audit_scores.mean(axis=(1, 2))
    correlation = rank_correlation(scores.mean(axis=(1, 2)), heldout)
    rng = np.random.default_rng(2728)
    masks = [tuple(rng.choice(12, size=3, replace=False)) for _ in range(16)]
    joint = []
    for donor in donors[4:]:
        all_replaced = replace_players(history, donor, tuple(range(12)))
        joint.extend([all_replaced, replace_players(history, donor, top),
                      replace_players(all_replaced, history, top)])
        for mask in masks:
            joint.extend([replace_players(history, donor, mask), replace_players(all_replaced, history, mask)])
    joint_raw = evaluate(joint).reshape(4, 35, 3, 4)
    joint_effect = np.mean(abs(np.maximum(joint_raw, 0)-base[0]), axis=(2, 3))
    deletion, random_deletion = float(joint_effect[:, 1].mean()), float(joint_effect[:, 3::2].mean())
    insertion = float((joint_effect[:, 0]-joint_effect[:, 2]).mean())
    random_insertion = float((joint_effect[:, 0, None]-joint_effect[:, 4::2]).mean())
    nearby_raw = evaluate([replace_players(nearby, d, (p,)) for d in donors[:4] for p in range(12)]).reshape(4, 12, 3, 4)
    nearby_scores = np.mean(abs(np.maximum(nearby_raw, 0)-base[1]), axis=(0, 2, 3))
    reliable = bool(scores.max() > 1e-6 and correlation is not None and correlation >= .5
                    and heldout[list(top)].mean() > heldout.mean()+1e-6 and deletion >= random_deletion)
    report = {
        "status": "RELIABLE_MODEL_DIAGNOSTIC" if reliable else "ABSTAIN_UNSTABLE_OR_UNFAITHFUL",
        "ranking": rank.tolist(), "audit_ranking": audit_rank.tolist(),
        "importance_kj_by_player_horizon_wheel": scores.tolist(),
        "audit_importance_kj_by_player_horizon_wheel": audit_scores.tolist(),
        "signed_delta_kj_by_player_horizon_wheel": delta[:4].mean(axis=0).tolist(),
        "rank_audit_spearman": correlation,
        "heldout_top_mean_kj": float(heldout[list(top)].mean()),
        "heldout_random_expectation_kj": float(heldout.mean()),
        "heldout_bottom_mean_kj": float(heldout[list(bottom)].mean()),
        "joint_top_deletion_kj": deletion, "joint_random_deletion_kj": random_deletion,
        "joint_top_insertion_gain_kj": insertion, "joint_random_insertion_gain_kj": random_insertion,
        "nearby_top_three_overlap": len(set(top) & set(_order(nearby_scores)[:3]))/3,
        "donor_top_three_overlap": len(set(top) & set(audit_rank[:3]))/3,
    }
    arrays = {"base_raw": base_raw, "perturb_raw": perturb_raw, "joint_raw": joint_raw, "nearby_raw": nearby_raw}
    _, report["output_projection"] = project_nonnegative(np.concatenate([v.ravel() for v in arrays.values()]))
    return report, arrays
