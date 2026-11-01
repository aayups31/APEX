import numpy as np
import pytest

from apexsim.research.aero_bicycle import integrate_aero_bicycle
from apexsim.research.bicycle import BicycleControl, BicycleState
from apexsim.research.imitation_driver import fit_policy, observation, policy_command
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve
from apexsim.research.support_audit import audit_detector, audit_switches
from apexsim.research.support_fallback import RuntimeController, Supervisor, fit_envelope, support_score
from apexsim.research.transparent_driver import AERO, CAR, DriverMap, command, speed_profile


def envelope():
    x = np.tile(np.array([[-1.]*8, [1.]*8]), (12, 1))
    return fit_envelope(x, x)


def test_hand_box_score_and_train_only_ranges_validation_only_cutoff():
    model = envelope()
    assert model["center"] == [0.]*8 and model["half_range"] == [1.]*8
    assert model["cutoff"] == 1.25 and support_score(model, np.ones(8)*2) == 2
    x = np.tile(np.array([[-1.]*8, [1.]*8]), (12, 1))
    other = fit_envelope(x, x*3)
    assert other["center"] == model["center"] and other["half_range"] == model["half_range"]
    assert other["cutoff"] == pytest.approx(3.3)
    assert not model["statistical_coverage_guarantee"] and not model["test_outcomes_used"]


def test_each_feature_axis_rejects_both_sides_and_discloses_in_box_blind_spot():
    model = envelope()
    for index in range(8):
        for sign in (-1, 1):
            row = np.zeros(8)
            row[index] = sign*1.251
            assert support_score(model, row) > model["cutoff"]
    assert support_score(model, np.full(8, 1.2)) < model["cutoff"]


def test_immediate_fallback_ten_consecutive_good_commands_and_no_chatter():
    monitor = Supervisor(envelope())
    state = BicycleState()
    assert monitor.decide(state, 0., np.ones(8)*2, 0.)["mode"] == "fallback"
    for _ in range(9):
        assert monitor.decide(state, 0., np.zeros(8), 0.)["mode"] == "fallback"
    assert monitor.decide(state, 0., np.ones(8)*1.1, 0.)["mode"] == "fallback"
    assert monitor.good_commands == 0
    for _ in range(9):
        assert monitor.decide(state, 0., np.zeros(8), 0.)["mode"] == "fallback"
    assert monitor.decide(state, 0., np.zeros(8), 0.)["mode"] == "learned"


@pytest.mark.parametrize("residual", [float("nan"), float("inf"), .20001, -.20001])
def test_invalid_raw_action_is_caught_before_projection(residual):
    row = Supervisor(envelope()).decide(BicycleState(), 0., np.zeros(8), residual)
    assert row["mode"] == "fallback" and row["reason"] == "INVALID_LEARNED_ACTION"


def test_nonfinite_learner_features_fallback_only_with_trusted_independent_state():
    bad = np.full(8, np.nan)
    assert support_score(envelope(), bad) is None
    monitor = Supervisor(envelope())
    assert monitor.decide(BicycleState(), 0., bad, 0.)["mode"] == "fallback"
    assert monitor.decide(BicycleState(), 0., bad, 0., state_trusted=False)["mode"] == "abstain"
    assert monitor.decide(BicycleState(), 0., np.zeros(8), 0.)["mode"] == "abstain"


@pytest.mark.parametrize("kwargs", [{"map_valid": False}, {"context_valid": False}, {"state_trusted": False}])
def test_hard_context_loss_latches_abstention(kwargs):
    monitor = Supervisor(envelope())
    assert monitor.decide(BicycleState(), 0., np.zeros(8), 0., **kwargs)["mode"] == "abstain"


def test_invalid_scaler_and_nonfinite_calibration_do_not_create_a_detector():
    with pytest.raises(ValueError, match="finite separate"):
        fit_envelope(np.ones((12, 8)), np.full((12, 8), np.nan))
    bad = dict(envelope(), half_range=[0.]*8)
    with pytest.raises(ValueError, match="parameters"):
        support_score(bad, np.zeros(8))


def test_independent_quantiles_do_not_call_primary_numpy_fit(monkeypatch):
    x = np.random.default_rng(118).normal(size=(75, 8))
    validation = x*1.2
    model = fit_envelope(x, validation)
    def forbidden(*args, **kwargs):
        raise AssertionError("Primary quantile called")
    monkeypatch.setattr(np, "quantile", forbidden)
    assert audit_detector(x, validation, model)["maximum_parameter_difference"] < 1e-12
    changed = dict(model, cutoff=model["cutoff"]+1)
    with pytest.raises(ValueError, match="independent detector"):
        audit_detector(x, validation, changed)


def test_fallback_uses_trusted_feedback_and_preserves_actual_actuator_memory(monkeypatch):
    track = DriverMap.from_curve(ReferenceCurve(np.array([[0., 0.], [25., 0.], [0., 25.]]), GeometryConfig(1, 0.), "SIMULATED"))
    profile = speed_profile(track, .65, 60.)
    xy, heading, _ = track.at(1.3*track.length_m)
    state = BicycleState(*xy, heading, 10., 0., 0.)
    x = np.random.default_rng(119).normal(size=(24, 8))
    model = fit_policy(x, np.zeros(24), np.ones(24), 1, 1e-8)
    previous = .04
    row = observation(state, track, 1.3*track.length_m, .1, previous, .1)
    action, _, log = policy_command(state, track, profile, 1.3*track.length_m, .1, previous, .1, "learned", model)
    controller = RuntimeController("guarded", "residual_bias", envelope(), model)
    def forbidden(*args, **kwargs):
        raise AssertionError("Corrupt learner features entered fallback")
    monkeypatch.setattr("apexsim.research.support_fallback.baseline_raw", forbidden)
    fallback, decision = controller(state, track, profile, 1.3*track.length_m, .1, previous, 0, action, row, log)
    expected, _ = command(state, track, profile, 1.3*track.length_m, .1, previous)
    assert decision["mode"] == "fallback" and decision["first_fault_command"]
    assert fallback == expected and abs(fallback.steering_rad-previous) <= .15+1e-14


def test_finite_but_unrepresentable_score_is_unavailable_and_reverts():
    model = dict(envelope(), half_range=[.005]*8)
    row = np.full(8, 1e308)
    assert support_score(model, row) is None
    decision = Supervisor(model).decide(BicycleState(), 0., row, 0.)
    assert decision["mode"] == "fallback" and decision["score"] is None


def test_switch_audit_selects_both_sides_and_detects_wrong_physical_endpoint():
    times = np.arange(6)*.1
    commands = [BicycleControl() for _ in range(5)]
    path = integrate_aero_bicycle(BicycleState(vx_mps=20.), times, commands, CAR, AERO, max_step_s=.02)
    arrays = {"case__states": path.states, "case__time_s": times, "case__controls": np.zeros((5, 4))}
    case = {"case_id": "case", "actor": "guarded", "max_step_s": .02,
            "decisions": [{"mode": mode} for mode in ("learned", "fallback", "fallback", "learned", "learned")]}
    result = audit_switches([case], arrays)
    assert result["passed"] and result["switches_checked"] == 2
    assert [r["interval_index"] for r in result["checks"]] == [0, 1, 2, 3]
    assert not result["primary_rhs_reused"]
    arrays["case__states"] = path.states.copy()
    arrays["case__states"][2, 0] += .1
    assert not audit_switches([case], arrays)["passed"]
