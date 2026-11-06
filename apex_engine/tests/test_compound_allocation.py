from copy import deepcopy
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from apexsim.research.compound_allocation import features, fit, forecast_laps, inventory
from apexsim.research.evidence import read_json

FOLDER = Path(__file__).resolve().parents[2] / "docs/verification"


def inputs():
    data = read_json(FOLDER / "compound-v11-development-data.json")
    sources = [
        s
        for name in ("compound-nomination-inventory.json", "compound-v13-nomination-additions.json")
        for s in read_json(FOLDER / name)["sources"]
    ]
    return data["cases"], sources, set(data["sources"])


def test_nomination_coverage_and_calendar_precedence():
    rows, sources, events = inputs()
    nominations = inventory(sources, events)
    assert len(nominations) == 28
    with pytest.raises(ValueError, match="Duplicate"):
        inventory([*sources, sources[0]], events)
    with pytest.raises(ValueError, match="coverage"):
        inventory(sources[:-1], events)
    event = str(rows[0]["session"])
    nominations[event] = (date(2099, 1, 1), nominations[event][1])
    with pytest.raises(ValueError, match="known before"):
        features(rows[0], nominations, True)


def test_joint_forecast_ignores_future_and_uses_checkpoint_equations():
    rows, sources, events = inputs()
    nominations = inventory(sources, events)
    row = rows[0]
    train = [r for r in rows if r["session"] != row["session"]][:50]
    x = features(row, nominations, True)
    assert x == features(
        {**row, "actual_s": 999.0, "pairwise_actual_s": 999.0, "current_target_s": [999.0] * 3},
        nominations,
        True,
    )
    assert x[: len(x) - 48] == features(row, nominations, False)
    model = fit(train, np.asarray([features(r, nominations, True) for r in train]))
    laps, _ = forecast_laps(model, x, row["current_prefix_s"])
    assert len(laps) == 3 and np.max(np.abs(np.array(laps) - row["current_prefix_s"])) <= 2.0
    changed = deepcopy(model)
    changed["intercept"] = [v + 1000 for v in model["intercept"]]
    bounded, hits = forecast_laps(changed, x, row["current_prefix_s"])
    assert hits == 3 and bounded == pytest.approx([p + 2 for p in row["current_prefix_s"]])
