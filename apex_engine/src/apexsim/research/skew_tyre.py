"""R023 Hansen skew-t observations and conditional causal bootstrap state inference."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import numpy as np
from scipy.special import gammaln, logsumexp
from scipy.stats import t

from apexsim.research.hierarchical_tyre import HierarchicalTyreModel
from apexsim.research.tyre_pace import validate_segments


@dataclass(frozen=True)
class SkewStudent:
    """Hansen standardized skew-t, zero mean/unit variance; never parameter-clipped."""
    nu: float = 8.
    skew: float = .25

    def __post_init__(self) -> None:
        if not np.isfinite([self.nu, self.skew]).all() or self.nu <= 2 or abs(self.skew) >= 1:
            raise ValueError("Skew-t requires finite nu>2 and |skew|<1")

    def constants(self) -> tuple[float, float, float]:
        c = float(np.exp(gammaln((self.nu+1)/2)-gammaln(self.nu/2)) / np.sqrt(np.pi*(self.nu-2)))
        a = 4*self.skew*c*(self.nu-2)/(self.nu-1)
        b = float(np.sqrt(1+3*self.skew**2-a*a))
        return a, b, c

    def logpdf(self, values: np.ndarray) -> np.ndarray:
        x = np.asarray(values, float)
        if not np.isfinite(x).all():
            raise ValueError("Skew-t observations must be finite")
        a,b,c = self.constants()
        side = np.where(x < -a/b, 1-self.skew, 1+self.skew)
        return np.log(b*c) - (self.nu+1)/2*np.log1p(((b*x+a)/side)**2/(self.nu-2))

    def cdf(self, values: np.ndarray) -> np.ndarray:
        x = np.asarray(values, float)
        a,b,_ = self.constants()
        side = np.where(x < -a/b, 1-self.skew, 1+self.skew)
        tcdf = t.cdf((b*x+a)/side*np.sqrt(self.nu/(self.nu-2)),self.nu)
        return np.where(x < -a/b,(1-self.skew)*tcdf,(1-self.skew)/2+(1+self.skew)*(tcdf-.5))

    def ppf(self, probabilities: np.ndarray) -> np.ndarray:
        u = np.asarray(probabilities,float)
        if not np.isfinite(u).all() or np.any((u<=0)|(u>=1)):
            raise ValueError("Skew-t quantiles require probabilities strictly inside (0,1)")
        a,b,_ = self.constants()
        left = u < (1-self.skew)/2
        probability = np.where(left,u/(1-self.skew),(u+self.skew)/(1+self.skew))
        side = np.where(left,1-self.skew,1+self.skew)
        return (side*t.ppf(probability,self.nu)*np.sqrt((self.nu-2)/self.nu)-a)/b

    def sample(self, rng: np.random.Generator, shape: tuple[int, ...]) -> np.ndarray:
        a,b,_ = self.constants()
        sign = np.where(rng.random(shape)<(1-self.skew)/2,-1.,1.)
        value = abs(rng.standard_t(self.nu,shape))*np.sqrt((self.nu-2)/self.nu)
        return (sign*(1+sign*self.skew)*value-a)/b


def stable_seed(key: str, seed: int) -> int:
    return int.from_bytes(sha256(f"{seed}:{key}".encode()).digest()[:8],"little")


def systematic_resample(states: np.ndarray, log_weights: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Independent conditional-state rows; do not reweight global group parameters."""
    norm = logsumexp(log_weights,axis=1)
    if not np.isfinite(norm).all():
        raise ValueError("Nonfinite particle observation likelihood")
    weights = np.exp(log_weights-norm[:,None])
    n = states.shape[1]
    result = np.empty_like(states)
    for k in range(len(states)):
        cdf = np.cumsum(weights[k])
        cdf[-1] = 1.
        points = (rng.random()+np.arange(n))/n
        result[k] = states[k,np.searchsorted(cdf,points,side="right")]
    ess = 1/np.sum(weights**2,axis=1)
    return result,ess


def particle_training_nll(segments: list[dict], hierarchy: HierarchicalTyreModel, observation: SkewStudent,
                          particles: int = 512, seed: int = 101) -> float:
    validate_segments(segments)
    if type(particles) is not int or particles<16:
        raise ValueError("At least16 particles required")
    q,r = hierarchy.noise.process_variance,hierarchy.noise.observation_variance
    score = 0.
    for segment in segments:
        values = np.array([row["corrected_s"] for row in segment["rows"]])
        drift = float(hierarchy.drift_draws(segment).mean())
        rng = np.random.default_rng(stable_seed(segment["segment_id"],seed))
        state = values[0]-observation.sample(rng,(1,particles))*np.sqrt(r)
        for value in values[1:]:
            state += drift+rng.normal(size=state.shape)*np.sqrt(q)
            log_weights = observation.logpdf((value-state)/np.sqrt(r))-.5*np.log(r)
            score -= float(logsumexp(log_weights)-np.log(particles))
            state,_ = systematic_resample(state,log_weights,rng)
    return score


def fit_observation_shape(segments: list[dict], hierarchy: HierarchicalTyreModel, *, particles: int = 512) -> tuple[SkewStudent, dict]:
    """Fixed training-only finite shape grid, conditional on the existing group fit."""
    if {s["event_id"] for s in segments} != set(hierarchy.training_events):
        raise ValueError("Observation shape fitting must use exactly the hierarchy training events")
    candidates = []
    for nu in (4.,8.,20.):
        for skew in (-.25,0.,.25,.5):
            model = SkewStudent(nu,skew)
            candidates.append({"nu":nu,"skew":skew,"training_nll":particle_training_nll(segments,hierarchy,model,particles)})
    selected = min(candidates,key=lambda c:c["training_nll"])
    return SkewStudent(selected["nu"],selected["skew"]), {"candidates":candidates,"selected":selected,
             "particles":particles,"seed":101,"training_events":hierarchy.training_events,
             "boundary":"conditional on Gaussian-trained hierarchy and fixed Q/R; shape is a training likelihood grid estimate"}


def empirical_crps(draws: np.ndarray, actual: float) -> float:
    """Exact CRPS of the empirical ensemble, O(n log n); includes finite-ensemble bias."""
    x = np.sort(np.asarray(draws,float).ravel())
    if not len(x) or not np.isfinite(x).all() or not np.isfinite(actual):
        raise ValueError("CRPS requires a finite nonempty predictive ensemble")
    coefficient = 2*np.arange(1,len(x)+1)-len(x)-1
    return float(np.mean(abs(x-actual))-coefficient@x/len(x)**2)


def observation_forecasts(segments: list[dict], hierarchy: HierarchicalTyreModel, observation: SkewStudent | None,
                         *, seed: int = 11, group_draws: int = 32, state_particles: int = 64) -> tuple[list[dict], np.ndarray]:
    """Gaussian exact conditional state control or genuine skew-t particle updates."""
    validate_segments(segments)
    if type(group_draws) is not int or group_draws<1 or type(state_particles) is not int or state_particles<4:
        raise ValueError("Invalid posterior/state particle budget")
    output,ensembles = [],[]
    q,r = hierarchy.noise.process_variance,hierarchy.noise.observation_variance
    for segment in segments:
        full = hierarchy.drift_draws(segment)
        drift = full[np.linspace(0,len(full)-1,group_draws,dtype=int)]
        values = np.array([row["corrected_s"] for row in segment["rows"]])
        rng = np.random.default_rng(stable_seed(segment["segment_id"],seed))
        if np.any(values<=0):
            raise ValueError("Lap RMSPE requires positive corrected lap times")
        if observation:
            state = values[0]-observation.sample(rng,(group_draws,state_particles))*np.sqrt(r)
        else:
            state = np.full(group_draws,values[0])
        variance, min_ess = r,float(state_particles)
        for origin in range(len(values)-1):
            for horizon in (1,3,5):
                if origin+horizon >= len(values):
                    continue
                forecast_rng = np.random.default_rng(stable_seed(f"{segment['segment_id']}:{origin}:{horizon}",seed))
                if observation:
                    draws = state+horizon*drift[:,None]+forecast_rng.normal(size=state.shape)*np.sqrt(horizon*q)
                    draws += observation.sample(forecast_rng,state.shape)*np.sqrt(r)
                else:
                    draws = state[:,None]+horizon*drift[:,None]+forecast_rng.normal(size=(group_draws,state_particles))*np.sqrt(variance+horizon*q+r)
                draws = draws.ravel()
                actual = float(values[origin+horizon])
                mean = float(draws.mean())
                output.append({"event_id":segment["event_id"],"driver":segment["driver"],"compound":segment["compound"],
                               "segment_id":segment["segment_id"],"origin_lap":segment["rows"][origin]["lap"],
                               "target_lap":segment["rows"][origin+horizon]["lap"],"horizon":horizon,"seed":seed,
                               "method":"skew_t" if observation else "gaussian","observed_s":actual,"predicted_s":mean,
                               "crps_s":empirical_crps(draws,actual),"squared_percentage_error":((actual-mean)/actual)**2,
                               "lower_90_s":float(np.quantile(draws,.05)),"upper_90_s":float(np.quantile(draws,.95)),
                               "pit":float(np.mean(draws<=actual)),"min_conditional_ess":min_ess})
                ensembles.append(draws)
            if observation:
                state += drift[:,None]+rng.normal(size=state.shape)*np.sqrt(q)
                state,ess = systematic_resample(state,observation.logpdf((values[origin+1]-state)/np.sqrt(r))-.5*np.log(r),rng)
                min_ess = float(ess.min())
            else:
                p = variance+q
                gain = p/(p+r)
                state = state+drift+gain*(values[origin+1]-state-drift)
                variance = (1-gain)*p
    return output,np.array(ensembles)


def observation_metrics(rows: list[dict]) -> dict:
    actual,mean = np.array([r["observed_s"] for r in rows]),np.array([r["predicted_s"] for r in rows])
    return {"predictions":len(rows),"crps_s":float(np.mean([r["crps_s"] for r in rows])),
            "rmspe_percent":float(100*np.sqrt(np.mean([r["squared_percentage_error"] for r in rows]))),
            "rmse_s":float(np.sqrt(np.mean((actual-mean)**2))),
            "coverage_90":float(np.mean([r["lower_90_s"]<=r["observed_s"]<=r["upper_90_s"] for r in rows])),
            "width_90_s":float(np.mean([r["upper_90_s"]-r["lower_90_s"] for r in rows]))}
