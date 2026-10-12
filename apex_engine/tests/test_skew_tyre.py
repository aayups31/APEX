import copy

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import t
from test_tyre_pace import segments

from apexsim.research.hierarchical_tyre import HierarchicalTyreModel, HierarchySettings
from apexsim.research.skew_tyre import SkewStudent, empirical_crps, observation_forecasts
from apexsim.research.tyre_pace import PaceParameters


@pytest.mark.parametrize("nu,skew",[(8,-.25),(8,0.),(8,.5),(4,.5)])
def test_density_normalization_mean_variance_and_inverse(nu,skew):
    model=SkewStudent(nu,skew)
    a,b,_=model.constants()
    def moment(order):
        def function(x):
            return float(x**order*np.exp(model.logpdf(np.array(x))))
        return quad(function,-np.inf,-a/b,epsabs=1e-8)[0]+quad(function,-a/b,np.inf,epsabs=1e-8)[0]
    assert moment(0)==pytest.approx(1,abs=1e-7)
    assert moment(1)==pytest.approx(0,abs=1e-7)
    assert moment(2)==pytest.approx(1,abs=1e-7)
    probabilities=np.linspace(.001,.999,101)
    np.testing.assert_allclose(model.cdf(model.ppf(probabilities)),probabilities,atol=1e-10)
    if skew==0:
        x=np.linspace(-5,5,100)
        np.testing.assert_allclose(model.logpdf(x),t.logpdf(x,8,scale=np.sqrt(6/8)),atol=1e-12)


def test_large_particle_near_gaussian_limit_matches_independent_kalman():
    from types import SimpleNamespace

    from apexsim.research.tyre_pace import filter_prefix

    values=np.array([90.,90.2,90.25,90.5,90.6,90.7,90.8])
    data=segments()[:1]
    data[0]["rows"]=[{"lap":i+1,"corrected_s":float(value)} for i,value in enumerate(values)]
    model=SimpleNamespace(noise=PaceParameters((.1,.1,.1),.01,.04),drift_draws=lambda _:np.full(10,.1))
    rows,_=observation_forecasts(data,model,SkewStudent(10000,0),group_draws=1,state_particles=32768)
    for row in rows:
        mean,_=filter_prefix(values[:row["origin_lap"]],.1,.01,.04)
        assert row["predicted_s"]==pytest.approx(mean+row["horizon"]*.1,abs=.012)


def test_sampling_moments_and_invalid_shape():
    model=SkewStudent(8,.5)
    x=model.sample(np.random.default_rng(25),(100000,))
    assert x.mean()==pytest.approx(0,abs=.015)
    assert x.var()==pytest.approx(1,abs=.04)
    for nu,skew in ((2,0),(8,1),(float("nan"),0)):
        with pytest.raises(ValueError):
            SkewStudent(nu,skew)
    with pytest.raises(ValueError):
        model.ppf(np.array([0.]))
    assert empirical_crps(np.array([0.,2.]),1.)==pytest.approx(.5)


def test_particle_forecast_causal_local_rng_and_fixed_group_posterior():
    data=segments()[:6]
    model=HierarchicalTyreModel(PaceParameters((.1,.1,.1),.001,.01),HierarchySettings(warmup=30,draws=50))
    model.fit(data)
    original=model.chains.copy()
    np.random.seed(512)
    before=np.random.get_state()
    rows,draws=observation_forecasts(data[:1],model,SkewStudent(),group_draws=4,state_particles=32)
    changed=copy.deepcopy(data[:1])
    changed[0]["rows"][-1]["corrected_s"]+=100
    after,again=observation_forecasts(changed,model,SkewStudent(),group_draws=4,state_particles=32)
    np.testing.assert_array_equal(draws,again)
    np.testing.assert_array_equal(original,model.chains)
    assert any(a["observed_s"]!=b["observed_s"] for a,b in zip(rows,after,strict=True))
    state=np.random.get_state()
    assert np.array_equal(before[1],state[1]) and before[2:]==state[2:]


def test_protected_segment_refused_and_gaussian_keys_match():
    data=segments()[:6]
    model=HierarchicalTyreModel(PaceParameters((.1,.1,.1),.001,.01),HierarchySettings(warmup=30,draws=50))
    model.fit(data)
    a,_=observation_forecasts(data[:1],model,None,group_draws=4,state_particles=32)
    b,_=observation_forecasts(data[:1],model,SkewStudent(),group_draws=4,state_particles=32)
    def key(row):
        return row["segment_id"],row["origin_lap"],row["horizon"]
    assert list(map(key,a))==list(map(key,b))
    data[0].update(event_id="F1_2023_R04",season=2023,round_number=4)
    with pytest.raises(ValueError,match="Permanent benchmark"):
        observation_forecasts(data[:1],model,SkewStudent())
