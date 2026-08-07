import numpy as np

from apexsim.contracts import MODEL_INPUT_COLUMNS
from apexsim.simulation import Scenario, apply_scenario


def test_scenario_changes_only_intended_fields():
    values = np.ones((4, len(MODEL_INPUT_COLUMNS)), dtype=np.float32) * 0.5
    modified = apply_scenario(values, Scenario(throttle_scale=1.2, brake_scale=0.8, rain_delta=0.2))
    index = {name: i for i, name in enumerate(MODEL_INPUT_COLUMNS)}
    assert np.allclose(modified[:, index["throttle"]], 0.6)
    assert np.allclose(modified[:, index["brake"]], 0.4)
    assert np.allclose(modified[:, index["rainfall"]], 0.7)
