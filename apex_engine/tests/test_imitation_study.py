import numpy as np
import pytest

from apexsim.examples.imitation_study import (
    VERSION,
    guard_dataset,
    improvement_gate,
    initial_speed,
    training_arrays,
)
from apexsim.provenance import write_manifest
from apexsim.research.imitation_audit import independent_fit, scalar_label
from apexsim.research.imitation_driver import expert_residual, fit_policy


def episode(event, driver, count, number=0):
    result = {"event_id": event, "driver_id": driver, "role": "train", "lap_id": event+driver, "case_id": event+driver+str(number),
              "collection_round": number, "completed": True}
    x = np.tile(np.array([.25, .1, .2, .01, .02, .03, .04, .05]), (count, 1))
    return result, {"features": x}


def test_equal_episode_round_weighting_is_independent_of_native_row_density():
    pairs = [episode("F1_2023_R01", "4", 12), episode("F1_2023_R14", "44", 36),
             episode("F1_2023_R01", "4", 24, 1), episode("F1_2023_R14", "44", 120, 1)]
    data, ledger = training_arrays(pairs)
    assert sum(r["rows"] for r in ledger) == len(data["y"]) == 192
    np.testing.assert_allclose([r["total_weight"] for r in ledger], [.25]*4)
    assert data["weights"].sum() == pytest.approx(1)
    assert scalar_label(data["x"][0]) == pytest.approx(expert_residual(data["x"][0]), abs=1e-14)


@pytest.mark.parametrize("event,role", [("F1_2024_R01", "validation"), ("F1_2024_R16", "test")])
def test_validation_and_test_states_cannot_enter_training_or_aggregation(event, role):
    result, arrays = episode(event, "4", 12)
    result["role"] = role
    with pytest.raises(ValueError, match="forbids validation and test"):
        training_arrays([(result, arrays)])


def test_test_payload_is_rejected_before_any_parquet_read(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Test payload accessed")

    monkeypatch.setattr("apexsim.examples.imitation_study.pd.read_parquet", forbidden)
    with pytest.raises(ValueError, match="forbidden event role"):
        initial_speed(tmp_path, {"profile": "research"}, {"event_id": "F1_2024_R16", "role": "test"}, ("train",))


def test_actual_reserved_event_is_guarded_before_missing_source_files(tmp_path):
    write_manifest(tmp_path/"inputs.json", {"schema_version": VERSION+"-inputs", "cases": [{"event_id": "F1_2024_R04"}]})
    with pytest.raises(ValueError, match="Permanent benchmark event"):
        guard_dataset(tmp_path)


def comparison_cases():
    rows = []
    for driver, lap in (("4", "a"), ("44", "b")):
        for actor in ("transparent", "final"):
            for scenario in ("nominal", "disturbed"):
                rows.append({"actor": actor, "driver_id": driver, "lap_id": lap, "scenario": scenario, "max_step_s": .02,
                             "passed": True, "station_weighted_mse_m2": 1. if actor == "transparent" else .64,
                             "p95_lateral_error_m": 1. if actor == "transparent" else .8,
                             "completion_time_s": 100., "final_lateral_error_m": .1})
    return rows


def test_matched_gate_requires_improvement_complete_catalog_stability_recovery_and_pace():
    rows = comparison_cases()
    assert improvement_gate(rows, {"a", "b"}, "research")["passed"]
    assert improvement_gate(rows, {"a", "b"}, "research")["macro_rmse_ratio"] == pytest.approx(.8)
    assert not improvement_gate(rows[:-1], {"a", "b"}, "research")["passed"]
    for field, value in (("passed", False), ("completion_time_s", 102.), ("station_weighted_mse_m2", 1.5), ("p95_lateral_error_m", 2.)):
        changed = [dict(row) for row in rows]
        next(row for row in changed if row["actor"] == "final" and row["scenario"] == "nominal")[field] = value
        assert not improvement_gate(changed, {"a", "b"}, "research")["passed"]
    changed = [dict(row) for row in rows]
    next(row for row in changed if row["actor"] == "final" and row["scenario"] == "disturbed")["final_lateral_error_m"] = .5
    assert not improvement_gate(changed, {"a", "b"}, "research")["passed"]


def test_qr_oracle_reconstructs_real_fitted_policy_and_rejects_changed_weights():
    x = np.random.default_rng(101).normal(size=(150, 8))
    y = .03*x[:, 0]*x[:, 2]-.01*x[:, 1]
    weights = np.linspace(1, 2, len(x))
    model = fit_policy(x, y, weights, 2, 1e-8)
    assert independent_fit(x, y, weights, model) < 1e-10
    corrupted = dict(model, coefficients=[v+.01 for v in model["coefficients"]])
    with pytest.raises(ValueError, match="QR ridge"):
        independent_fit(x, y, weights, corrupted)
