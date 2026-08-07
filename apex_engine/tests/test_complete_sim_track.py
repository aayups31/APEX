import numpy as np

from apexsim.sim_core.track import TrackMap


def test_track_wrap_and_sampling():
    track = TrackMap.synthetic(length_m=3000.0, points=500, seed=1)
    assert 2990.0 < track.length_m < 3010.0
    first = track.sample(10.0)
    wrapped = track.sample(track.length_m + 10.0)
    assert np.isclose(first.x_m, wrapped.x_m)
    assert np.isfinite(track.lookahead_curvature(100.0))
