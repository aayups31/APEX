from pathlib import Path
from runpy import run_path

import numpy as np
import pytest

STUDY = run_path(str(Path(__file__).resolve().parents[2]/"research/scripts/verify_tyre_wear_compounds.py"))


def test_group_intercepts_do_not_bias_recovered_compound_priors():
    coefficients = np.array([-.8, -.4, .13, .08, .03])
    groups = {}
    for group, intercept in enumerate((80., 104.)):
        groups[group] = [
            (compound, age, intercept + STUDY["design"](compound, age, True) @ coefficients)
            for compound in STUDY["COMPOUNDS"] for age in range(2, 15)
        ]
    np.testing.assert_allclose(STUDY["fit"](groups, True), coefficients, atol=1e-10)


def test_crossover_requires_observed_contiguous_support_and_sustained_signs():
    assert STUDY["crossovers"](list(range(2, 8)), [-.4, -.3, -.2, .2, .3, .4]) == [4.5]
    assert STUDY["crossovers"]([2, 3, 4, 6, 7, 8], [-.4, -.3, -.2, .2, .3, .4]) == []
    assert STUDY["crossovers"](list(range(2, 8)), [-.4, .1, -.1, .2, .3, .4]) == []


def test_unidentifiable_compound_fit_rejects():
    with pytest.raises(ValueError, match="not identifiable"):
        STUDY["fit"]({0: [("HARD", i, float(i)) for i in range(5)]}, True)
