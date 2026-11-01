"""Independent sorted-array quantiles and scalar box scores for R038."""
from __future__ import annotations

import math

import numpy as np


def quantile(values, probability):
    values = sorted(float(v) for v in values)
    point = probability*(len(values)-1)
    left = math.floor(point)
    fraction = point-left
    return values[left]*(1-fraction)+values[min(left+1, len(values)-1)]*fraction


def audit_detector(training: np.ndarray, validation: np.ndarray, model: dict) -> dict:
    floors = [.05, .02, .02, .005, .005, .02, .01, .01]
    pairs = [(quantile(training[:, j], .005), quantile(training[:, j], .995)) for j in range(8)]
    centers = [(a+b)/2 for a, b in pairs]
    widths = [max((b-a)/2, floor) for (a, b), floor in zip(pairs, floors, strict=True)]
    scores = [max(abs((float(row[j])-centers[j])/widths[j]) for j in range(8)) for row in validation]
    cutoff = max(1.25, 1.1*quantile(scores, .995))
    independent = np.r_[centers, widths, cutoff]
    primary = np.r_[model["center"], model["half_range"], model["cutoff"]]
    difference = float(np.max(abs(independent-primary)))
    if not np.allclose(independent, primary, atol=1e-12, rtol=1e-10):
        raise ValueError("R038 independent detector fit disagreement")
    return {"verified": True, "method": "INDEPENDENT_SORTED_LINEAR_QUANTILES_SCALAR_BOX", "maximum_parameter_difference": difference,
            "validation_exceedance_fraction": sum(v > cutoff for v in scores)/len(scores)}
