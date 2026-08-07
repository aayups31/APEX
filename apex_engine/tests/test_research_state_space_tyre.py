import numpy as np

from apexsim.research.state_space_tyre import LatentTyreDegradationFilter


def test_latent_tyre_filter_tracks_degradation_and_resets():
    laps = np.arange(12)
    fuel = 30 - 1.5 * laps
    latent = 0.08 * laps
    times = 90.0 + 0.03 * fuel + latent
    reset = np.zeros(12, dtype=bool)
    reset[7] = True
    times[7:] = 90.0 + 0.03 * fuel[7:] + 0.05 * np.arange(5)
    compounds = ["SOFT"] * 7 + ["HARD"] * 5
    result = LatentTyreDegradationFilter().filter(times, fuel, compounds, reset)
    assert len(result) == 12
    assert result.loc[6, "latent_tyre_pace_s"] > result.loc[1, "latent_tyre_pace_s"]
    assert result.loc[7, "latent_tyre_pace_s"] < result.loc[6, "latent_tyre_pace_s"]
    assert np.all(result.upper_95_s >= result.lower_95_s)
