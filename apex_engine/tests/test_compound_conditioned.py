import numpy as np
import pytest

from apexsim.research.compound_conditioned import feature_vector, fit_conditioned, predict_conditioned
from apexsim.research.compound_reference import COMPOUNDS


def window(compound="HARD", driver=0):
    return dict(session=9912, driver=driver, stints=[1, 2], ages=list(range(2, 14)),
                compounds=["SOFT", compound], current_prefix_s=[90., 90.1, 90.2],
                current_target_s=[90.3, 90.4, 90.5], reference_target_s=[91., 91.1, 91.2],
                prefix_s=-.2, reference_end_s=100., forecast_at_s=200.)


def test_conditioned_hand_features_and_forecast_ignore_future_targets():
    row = window()
    assert feature_vector(row) == pytest.approx([0., 0., 1., 1.2, .9, -.2])
    model = {"feature_level": 3, "coefficients": [0., 0., .1, .2, 0., .5],
             "support": {"HARD": {"radius_s": .2}}}
    prediction = predict_conditioned(model, row)
    assert prediction["predicted_s"] == pytest.approx(.76)
    assert predict_conditioned(model, {**row, "current_target_s": [120.]*3}) == prediction
    with pytest.raises(ValueError, match="unavailable"):
        predict_conditioned(model, {**row, "reference_end_s": 201.})


def test_conditioned_ridge_matches_independent_augmented_least_squares():
    rows = [window(compound, 3*j+i) for j, compound in enumerate(COMPOUNDS) for i in range(3)]
    model = fit_conditioned(rows)
    x = np.asarray([feature_vector(r) for r in rows])
    # An independent augmented system gives ridge without normal equations.
    expected = np.linalg.lstsq(np.vstack([x, np.sqrt(10.)*np.eye(6)]),
                               np.concatenate([np.full(9, .3), np.zeros(6)]), rcond=None)[0]
    assert model["coefficients"] == pytest.approx(expected)
    repeated = [{**r, "stints": [0, 2]} for r in rows]
    assert fit_conditioned(rows+repeated)["coefficients"] == pytest.approx(expected)
