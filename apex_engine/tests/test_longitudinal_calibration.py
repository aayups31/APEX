from dataclasses import replace

import numpy as np
import pytest

from apexsim.research.longitudinal_calibration import (
    ROLLING_PRIOR,
    SpecificPowerDrag,
    fit_cell,
    identification_arrays,
    integrate_speed,
    replay_section,
)
from apexsim.research.longitudinal_data import LongitudinalSection
from apexsim.research.longitudinal_scores import aggregate_errors, paired_lap_interval, section_errors


def simulated_section(index=0, *, drs=0, euler=True):
    model = SpecificPowerDrag(900., .0005, .0002)
    time = np.arange(13)*.25
    v0 = 40+index*3
    if euler:
        speed = [float(v0)]
        for dt in np.diff(time):
            speed.append(speed[-1]+dt*model.acceleration(speed[-1], 1., drs))
        speed = np.array(speed)
    else:
        speed = integrate_speed(v0, time, np.ones(13), np.full(13, drs), model.acceleration)
    warmup = np.arange(-4, 1)*.25
    return LongitudinalSection(
        {"event_id": "F1_2023_R01", "track_id": "bahrain", "driver_id": "4", "role": "train",
         "lap_id": f"sim_lap{index}", "section_id": f"sim_{index}", "fixture_source": "SIMULATED"},
        time, speed, np.ones(13), np.full(13, drs, dtype=np.int64), np.arange(13, dtype=np.int64)+index*20,
        np.arange(13, dtype=np.int64), warmup, v0+.4*warmup,
    )


def test_hand_force_balance_units_drag_and_drs_direction():
    model = SpecificPowerDrag(900., .0005, .0002)
    assert model.acceleration(50., 1., 0) == pytest.approx(16.10285)
    assert model.acceleration(50., 1., 1)-model.acceleration(50., 1., 0) == pytest.approx(.5)
    assert model.acceleration(70., 1., 0) < model.acceleration(50., 1., 0)
    assert model.acceleration(50., .5, 0) < model.acceleration(50., 1., 0)
    assert SpecificPowerDrag(1000., .0005, .0002).acceleration(50., 1., 0) > model.acceleration(50., 1., 0)
    assert abs(ROLLING_PRIOR-.14715) < 1e-12


def test_analytic_state_and_parameter_derivatives_match_finite_differences():
    model = SpecificPowerDrag(900., .0005, .0002)
    state, parameters = model.derivatives(60., .99, 0)
    assert state == pytest.approx((model.acceleration(60.0001, .99, 0)-model.acceleration(59.9999, .99, 0))/.0002, rel=1e-7)
    for i, (field, eps) in enumerate(zip(("power_per_mass", "open_drag_per_mass", "extra_closed_drag_per_mass"), (1e-3, 1e-8, 1e-8), strict=True)):
        plus = replace(model, **{field: getattr(model, field)+eps})
        minus = replace(model, **{field: getattr(model, field)-eps})
        numerical = (plus.acceleration(60., .99, 0)-minus.acceleration(60., .99, 0))/(2*eps)
        assert parameters[i] == pytest.approx(numerical, rel=1e-7)


def test_noiseless_increment_coefficients_recovered_and_conditioning_reported():
    training = [simulated_section(i, drs=i % 2) for i in range(12)]
    fit = fit_cell(training, "drs_drag")
    assert fit["parameters"]["power_per_mass"] == pytest.approx(900., rel=1e-9)
    assert fit["parameters"]["open_drag_per_mass"] == pytest.approx(.0005, rel=1e-9)
    assert fit["parameters"]["extra_closed_drag_per_mass"] == pytest.approx(.0002, rel=1e-9)
    assert fit["normalized_condition_number"] < 1e4
    assert fit["increment_rmse_mps"] < 1e-12
    assert not any(fit["active_bounds"])


def test_drs_without_state_variation_is_unidentifiable_not_imputed():
    training = [simulated_section(i, drs=0) for i in range(12)]
    with pytest.raises(ValueError, match="unidentifiable"):
        fit_cell(training, "drs_drag")
    assert fit_cell(training, "shared_drag")["kind"] == "shared_drag"


def test_validation_events_cannot_fit_coefficients():
    original = simulated_section()
    metadata = dict(original.metadata, event_id="F1_2024_R01", role="validation")
    validation = replace(original, metadata=metadata)
    with pytest.raises(ValueError, match="training events only"):
        identification_arrays([validation], "shared_drag")


def test_constant_acceleration_exact_limit_and_rk4_refinement():
    time = np.array([0., .2, .44, .8, 1.3])
    result = integrate_speed(40., time, np.ones(5), np.zeros(5), lambda v, u, z: 2.)
    np.testing.assert_allclose(result, 40+2*time, atol=1e-12, rtol=0)
    model = SpecificPowerDrag(900., .0005, .0002)
    coarse = integrate_speed(40., time, np.ones(5), np.zeros(5), model.acceleration, max_step_s=.05)
    fine = integrate_speed(40., time, np.ones(5), np.zeros(5), model.acceleration, max_step_s=.025)
    assert np.max(abs(coarse-fine)) < 1e-6


def test_replay_does_not_teacher_force_or_read_future_speed_targets():
    section = simulated_section()
    changed = replace(section, speed_mps=np.r_[section.speed_mps[0], section.speed_mps[1:]+1.])
    for method in ("constant_speed", "constant_acceleration", "physical_prior"):
        np.testing.assert_array_equal(replay_section(section, method), replay_section(changed, method))


def test_nonfinite_controls_and_unphysical_state_fail_without_clipping():
    with pytest.raises(ValueError, match="no clipping"):
        SpecificPowerDrag(900., .0005).acceleration(0., 1., 0)
    with pytest.raises(ValueError, match="state/times/controls"):
        integrate_speed(40., np.array([0., .25]), np.ones(2), np.array([0., .5]), lambda v, u, z: 1.)
    with pytest.raises(ValueError, match="bounded speed"):
        integrate_speed(119., np.array([0., .25]), np.ones(2), np.zeros(2), lambda v, u, z: 100.)


def test_equal_driver_lap_metrics_differ_from_frame_weighting_hand_fixture():
    section = simulated_section()
    other = replace(section, metadata=dict(section.metadata, driver_id="44", lap_id="other_driver_lap"))
    sections = [section, section, section, other]
    predictions = [np.r_[s.speed_mps[0], s.speed_mps[1:]+e] for s, e in zip(sections, [3., 3., 3., 1.], strict=True)]
    baseline = aggregate_errors(sections, predictions)
    assert baseline["mse_m2ps2"] == pytest.approx(5.)
    assert baseline["frame_weighted_rmse_mps"]**2 == pytest.approx(7.)
    perfect = aggregate_errors(sections, [s.speed_mps.copy() for s in sections])
    paired = paired_lap_interval(perfect, baseline, sections, resamples=20)
    np.testing.assert_allclose(paired["interval_95_m2ps2"], [-5., -5.], atol=1e-12, rtol=0)
    bad = section.speed_mps.copy()
    bad[0] += 1
    with pytest.raises(ValueError, match="finite matched"):
        section_errors(section, bad)
