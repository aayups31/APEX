import copy

import numpy as np
import pytest

from apexsim.research.forecast_benchmark import EVENTS, ForecastScaler
from apexsim.research.forecast_explanations import (
    PLAYERS,
    FrozenForecastPredictor,
    donor_indices,
    guard_origins,
    rank_correlation,
    replace_players,
    select_origins,
    temporal_explanation,
)


def sparse_predictor(dynamic, static):
    # Exactly two relevant players: newest kinematics and controls at samples4:6.
    return np.broadcast_to((2*dynamic[:, -1, 0]+.5*dynamic[:, -3, 1])[:, None, None], (len(dynamic), 3, 4)).copy()


def test_hand_sparse_temporal_recovery_independent_audit_and_no_mutation():
    x, donors = np.ones((8, 14), np.float32), np.zeros((8, 8, 14), np.float32)
    before = x.copy()
    result, raw = temporal_explanation(sparse_predictor, x, np.ones(3), donors, x)
    assert result["status"] == "RELIABLE_MODEL_DIAGNOSTIC"
    assert result["ranking"][:2] == [3, 6]
    scores = np.array(result["importance_kj_by_player_horizon_wheel"])
    np.testing.assert_array_equal(scores[3], np.full((3, 4), 2.))
    np.testing.assert_array_equal(scores[6], np.full((3, 4), .5))
    assert np.count_nonzero(scores) == 24
    assert result["rank_audit_spearman"] == pytest.approx(1)
    assert result["joint_top_deletion_kj"] == pytest.approx(2.5)
    assert result["joint_top_insertion_gain_kj"] == pytest.approx(2.5)
    assert result["nearby_top_three_overlap"] == 1
    assert raw["perturb_raw"].shape == (8, 12, 3, 4)
    np.testing.assert_array_equal(x, before)


def test_constant_predictor_abstains_and_irrelevant_variables_stay_zero():
    result, _ = temporal_explanation(lambda x, s: np.ones((len(x), 3, 4)), np.ones((8, 14)),
                                     np.ones(3), np.zeros((8, 8, 14)), np.ones((8, 14)))
    assert result["status"] == "ABSTAIN_UNSTABLE_OR_UNFAITHFUL"
    assert result["rank_audit_spearman"] is None
    assert np.count_nonzero(result["importance_kj_by_player_horizon_wheel"]) == 0


def test_disjoint_audit_catches_deliberately_misleading_ranking_donors():
    donors = np.zeros((8, 8, 14), np.float32)
    donors[:4, :, 1] = 1  # Ranking donors identify only speed, audit donors only throttle.
    donors[4:, :, 0] = 1
    result, _ = temporal_explanation(sparse_predictor, np.ones((8, 14)), np.ones(3), donors, np.ones((8, 14)))
    assert result["status"] == "ABSTAIN_UNSTABLE_OR_UNFAITHFUL"


def test_player_partition_timing_immutability_and_invalid_values():
    x, donor = np.zeros((8, 14)), np.ones((8, 14))
    out = replace_players(x, donor, tuple(range(12)))
    assert len(PLAYERS) == 12
    np.testing.assert_array_equal(out[:, 8:10], x[:, 8:10])
    assert out.sum() == 8*12
    with pytest.raises(ValueError, match="Invalid finite"):
        replace_players(x, donor, (0, 0))
    with pytest.raises(ValueError, match="Invalid finite"):
        replace_players(x, donor*np.nan, (0,))


def origins(event=EVENTS[0]):
    return [{"event_id": event, "driver_id": "4", "compound": "HARD", "track_id": "bahrain",
             "sequence_id": f"{event}_{seq}", "origin_native_row": i}
            for seq in range(10) for i in range(7, 32)]


def test_metadata_cohort_is_deterministic_spaced_and_has_nearby_origin():
    metadata = origins()
    first, nearby, coverage = select_origins(metadata)
    assert (first, nearby, coverage) == select_origins(copy.deepcopy(metadata))
    assert len(first) == 16
    for i, j in zip(first, nearby, strict=True):
        assert metadata[j]["sequence_id"] == metadata[i]["sequence_id"]
        assert metadata[j]["origin_native_row"] == metadata[i]["origin_native_row"]+1
    for seq in {metadata[i]["sequence_id"] for i in first}:
        rows = [metadata[i]["origin_native_row"] for i in first if metadata[i]["sequence_id"] == seq]
        assert len(rows) <= 2
        assert len(rows) < 2 or abs(rows[1]-rows[0]) >= 8


def test_training_only_distinct_sequence_donors_and_missing_compound_abstention():
    train = origins()+origins(EVENTS[1])
    selected = donor_indices(train, origins("F1_2023_R01")[0])
    assert len(selected) == 8
    assert len({train[i]["sequence_id"] for i in selected}) == 8
    assert donor_indices(train, dict(train[0], compound="SOFT")) == []
    with pytest.raises(ValueError, match="frozen training"):
        donor_indices(train+origins(EVENTS[3]), train[0])


@pytest.mark.parametrize("mutation", ["duplicate", "mixed", "protected"])
def test_guard_native_source_identity_and_permanent_benchmarks(mutation):
    rows = origins()
    if mutation == "duplicate":
        rows.append(rows[0])
    elif mutation == "mixed":
        rows[0] = dict(rows[0], driver_id="44")
    else:
        rows[0] = dict(rows[0], event_id="F1_2023_R04")
    with pytest.raises(ValueError, match=r"identity|Permanent benchmark"):
        guard_origins(rows)


def test_tied_spearman_and_undefined_constant_rank():
    assert rank_correlation(np.array([1., 1., 2.]), np.array([2., 2., 4.])) == pytest.approx(1)
    assert rank_correlation(np.ones(3), np.arange(3)) is None


def test_linear_checkpoint_is_bitwise_invariant_to_inference_batch_size(tmp_path):
    rng = np.random.default_rng(2728)
    vocabulary = {"driver_id": ["UNKNOWN"], "compound": ["UNKNOWN"], "track_id": ["UNKNOWN"]}
    scaler = ForecastScaler(np.zeros(14), np.ones(14), np.zeros((3, 4)), np.ones((3, 4)))
    path = tmp_path/"linear.npz"
    np.savez(path, coef=rng.normal(size=(12, 115)).astype(np.float32),
             intercept=rng.normal(size=12).astype(np.float32))
    predictor = FrozenForecastPredictor(path, {"kind": "linear"}, scaler, vocabulary)
    x, static = rng.normal(size=(128, 8, 14)).astype(np.float32), np.ones((128, 3), np.float32)
    together = predictor(x, static)
    separate = np.concatenate([predictor(x[i:i+1], static[i:i+1]) for i in range(128)])
    np.testing.assert_array_equal(together, separate)
