import numpy as np
import pandas as pd

from apexsim.research.tyre_energy import (
    TyreEnergyInputs,
    augment_with_proxy_tyre_energy,
    estimate_wheel_tyre_energy,
)


def test_tyre_energy_nonnegative_and_left_right_symmetric_on_straight():
    result = estimate_wheel_tyre_energy(
        TyreEnergyInputs(
            speed_mps=70.0,
            longitudinal_accel_mps2=4.0,
            lateral_accel_mps2=0.0,
            steering_rad=0.0,
            throttle=1.0,
            brake=0.0,
            dt_s=0.1,
        )
    ).as_array()
    assert np.all(result >= 0)
    assert np.isclose(result[0], result[1])
    assert np.isclose(result[2], result[3])
    assert result[2] > result[0]


def test_outside_tyre_energy_increases_in_corner():
    straight = estimate_wheel_tyre_energy(
        TyreEnergyInputs(60, 0, 0, 0, 0.5, 0, 0.1)
    ).as_array()
    corner = estimate_wheel_tyre_energy(
        TyreEnergyInputs(60, 0, 18, 0.12, 0.5, 0, 0.1)
    ).as_array()
    assert corner.sum() > straight.sum()
    assert corner[0] > corner[1]  # positive lateral acceleration loads left side


def test_augment_proxy_targets():
    frame = pd.DataFrame(
        {
            "speed_mps": [50.0, 51.0],
            "acceleration_mps2": [1.0, -2.0],
            "lateral_acceleration_mps2": [0.0, 10.0],
            "steering": [0.0, 0.08],
            "throttle": [0.8, 0.1],
            "brake": [0.0, 0.7],
            "dt_s": [0.1, 0.1],
        }
    )
    out = augment_with_proxy_tyre_energy(frame)
    assert out.filter(like="tyre_energy_").shape[1] == 5
    assert set(out["tyre_energy_target_quality"]) == {"PROXY_NOT_MEASURED"}
