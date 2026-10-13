"""R025 event/sequence-safe windows, training-only preprocessing and six real model families."""
from __future__ import annotations

import copy
import re
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LinearRegression, Ridge
from torch.utils.data import DataLoader, TensorDataset
from xgboost import Booster, DMatrix
from xgboost import train as train_booster

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.research.temporal_fusion import RecurrentForecaster, TemporalFusionForecaster, quantile_loss
from apexsim.research.tyre_energy import WHEEL_NAMES

EVENTS=("F1_2024_R01","F1_2024_R03","F1_2024_R06","F1_2024_R16","F1_2024_R18")
HORIZONS=(1,3,5)
TARGETS=tuple(f"tyre_energy_{wheel}_kj" for wheel in WHEEL_NAMES)
DYNAMIC=("speed_mps","throttle","brake_pressure_proxy","longitudinal_accel_mps2","lateral_accel_proxy_mps2",
         "steering_rad_proxy","heading_rate_rad_s","geometry_speed_mps","dt_s","position_lag_s",*TARGETS)
STATIC=("driver_id","compound","track_id")


@dataclass(frozen=True)
class ForecastWindows:
    dynamic: np.ndarray
    static: np.ndarray
    target: np.ndarray
    metadata: list[dict]
    vocabulary: dict[str,list[str]]

    def __post_init__(self) -> None:
        n=len(self.dynamic)
        if (self.dynamic.shape!=(n,8,len(DYNAMIC)) or self.static.shape!=(n,sum(len(v) for v in self.vocabulary.values()))
                or self.target.shape!=(n,3,4) or len(self.metadata)!=n or not n
                or not all(np.isfinite(a).all() for a in (self.dynamic,self.static,self.target))):
            raise ValueError("Invalid finite matched forecast window shapes")

    @property
    def static_widths(self) -> tuple[int,...]:
        return tuple(len(self.vocabulary[field]) for field in STATIC)

    def subset(self, events: tuple[str,...]) -> ForecastWindows:
        indices=np.array([i for i,m in enumerate(self.metadata) if m["event_id"] in events])
        return ForecastWindows(self.dynamic[indices],self.static[indices],self.target[indices],
                               [self.metadata[i] for i in indices],self.vocabulary)


def build_forecast_windows(frame: pd.DataFrame, *, expected_events: tuple[str,...] = EVENTS,
                           vocabulary: dict[str,list[str]] | None = None) -> ForecastWindows:
    """Same origins for every horizon; no future values, native gaps or mixed drivers."""
    required={"event_id","sequence_id","segment_id","native_car_row","time_s",*DYNAMIC,*STATIC}
    if not required.issubset(frame):
        raise ValueError(f"Missing matched forecasting fields: {sorted(required-set(frame))}")
    for event in frame.event_id.unique():
        match=re.fullmatch(r"F1_(\d{4})_R(\d{2})",event)
        if not match:
            raise ValueError("Forecast event IDs must have canonical season/round identities")
        assert_development_event(int(match[1]),int(match[2]),event_id=event)
    if not expected_events or len(set(expected_events))!=len(expected_events) or set(frame.event_id.unique())!=set(expected_events):
        raise ValueError("Forecast requires all unique frozen development events")
    if vocabulary is None:
        if expected_events!=EVENTS:
            raise ValueError("Evaluation cohorts require a frozen training vocabulary")
        training=frame[frame.event_id.isin(EVENTS[:2])]
        vocabulary={field:["UNKNOWN",*sorted(training[field].unique().tolist())] for field in STATIC}
    elif (set(vocabulary)!=set(STATIC) or any(not values or values[0]!="UNKNOWN"
          or len(values)!=len(set(values)) or not all(isinstance(v,str) for v in values)
          for values in vocabulary.values())):
        raise ValueError("Invalid frozen forecasting vocabulary")
    vocabulary=copy.deepcopy(vocabulary)
    xs,ss,ys,metadata=[],[],[],[]
    for sequence,group in frame.groupby("sequence_id",sort=True):
        group=group.sort_values("time_s",kind="stable")
        if (any(group[field].nunique()!=1 for field in ("event_id","driver_id","segment_id","compound","track_id"))
                or np.any(np.diff(group.native_car_row.to_numpy())!=1) or np.any(np.diff(group.time_s.to_numpy())<=0)):
            raise ValueError("Forecast sequence crosses identity or native continuity boundary")
        dynamic=group[list(DYNAMIC)].to_numpy(float)
        target=group[list(TARGETS)].to_numpy(float)
        if not np.isfinite(dynamic).all() or not np.isfinite(target).all() or np.any(target<0):
            raise ValueError("Forecast inputs/targets must be finite and targets nonnegative")
        static=[]
        for field in STATIC:
            values=vocabulary[field]
            value=group.iloc[0][field]
            code=values.index(value) if value in values else 0
            static.extend(float(i==code) for i in range(len(values)))
        records=group.to_dict("records")
        for origin in range(7,len(group)-5):
            xs.append(dynamic[origin-7:origin+1])
            ss.append(static)
            ys.append(target[[origin+h for h in HORIZONS]])
            row=records[origin]
            metadata.append({"event_id":row["event_id"],"driver_id":row["driver_id"],"compound":row["compound"],"track_id":row["track_id"],
                             "sequence_id":sequence,"origin_native_row":int(row["native_car_row"]),
                             "origin_time_s":float(row["time_s"]),
                             "target_native_rows":[int(records[origin+h]["native_car_row"]) for h in HORIZONS],
                             "elapsed_horizons_s":[float(records[origin+h]["time_s"]-row["time_s"]) for h in HORIZONS]})
    return ForecastWindows(np.asarray(xs,np.float32),np.asarray(ss,np.float32),np.asarray(ys,np.float64),metadata,vocabulary)


@dataclass(frozen=True)
class ForecastScaler:
    input_mean: np.ndarray
    input_std: np.ndarray
    target_mean: np.ndarray
    target_std: np.ndarray

    @classmethod
    def fit(cls, training: ForecastWindows) -> ForecastScaler:
        if {m["event_id"] for m in training.metadata}!=set(EVENTS[:2]):
            raise ValueError("Forecast scaler requires exactly frozen training membership")
        return cls(training.dynamic.mean(axis=(0,1),dtype=np.float64),np.maximum(training.dynamic.std(axis=(0,1),dtype=np.float64),1e-8),
                   training.target.mean(axis=0),np.maximum(training.target.std(axis=0),1e-8))

    def inputs(self, data: ForecastWindows) -> np.ndarray:
        return ((data.dynamic-self.input_mean)/self.input_std).astype(np.float32)

    def targets(self, data: ForecastWindows) -> np.ndarray:
        return ((data.target-self.target_mean)/self.target_std).astype(np.float32)

    def inverse(self, prediction: np.ndarray) -> np.ndarray:
        return prediction*self.target_std+self.target_mean

    def as_dict(self) -> dict:
        return {name:getattr(self,name).tolist() for name in ("input_mean","input_std","target_mean","target_std")}


def flat_features(data: ForecastWindows, scaler: ForecastScaler) -> np.ndarray:
    return np.column_stack((scaler.inputs(data).reshape(len(data.dynamic),-1),data.static))


def forecast_metrics(actual: np.ndarray, prediction: np.ndarray) -> dict:
    if actual.shape!=prediction.shape or not np.isfinite(prediction).all():
        raise ValueError("Forecast metric shape/finite contract failed")
    error=prediction-actual
    return {"mae_kj":float(np.mean(abs(error))),"rmse_kj":float(np.sqrt(np.mean(error**2))),
            "smape_percent":float(np.mean(200*abs(error)/(abs(prediction)+abs(actual)+.001)))}


def project_nonnegative(prediction: np.ndarray) -> tuple[np.ndarray,dict]:
    if not np.isfinite(prediction).all():
        raise ValueError("Nonfinite forecast output")
    return np.maximum(prediction,0),{"negative_cells":int(np.sum(prediction<0)),
                                    "largest_correction_kj":float(max(0,-prediction.min()))}


def transparent_prediction(data: ForecastWindows, method: str) -> np.ndarray:
    energies=data.dynamic[:,:,-4:].astype(float)
    if method=="persistence":
        return np.repeat(energies[:,-1,None,:],3,axis=1)
    if method=="trend":
        slope=(energies[:,-1]-energies[:,-3])/2
        return energies[:,-1,None,:]+np.array(HORIZONS)[None,:,None]*slope[:,None,:]
    raise ValueError("Unknown transparent forecast")


def neural_model(kind: str, widths: tuple[int,...], hidden: int):
    if kind=="tft":
        return TemporalFusionForecaster(len(DYNAMIC),widths,hidden)
    return RecurrentForecaster(kind,len(DYNAMIC),widths,hidden)


def _neutral_unknown_static(model, kind: str, widths: tuple[int,...], hidden: int) -> None:
    """Unseen categories have a deterministic zero input contribution, not random weights."""
    with torch.no_grad():
        if kind=="tft":
            for embedding in model.static_selection.embeddings:
                embedding.weight[:,0]=0
        else:
            offset=hidden
            for width in widths:
                model.head[0].weight[:,offset]=0
                offset+=width


def neural_prediction(model, kind: str, data: ForecastWindows, scaler: ForecastScaler) -> np.ndarray:
    model.eval()
    dynamic=scaler.inputs(data)
    values=[]
    with torch.no_grad():
        for start in range(0,len(dynamic),1024):
            pred=model(torch.from_numpy(dynamic[start:start+1024]),torch.from_numpy(data.static[start:start+1024]))
            values.append((pred[...,1] if kind=="tft" else pred).numpy())
    return scaler.inverse(np.concatenate(values))


def neural_quantile_prediction(model, data: ForecastWindows, scaler: ForecastScaler) -> np.ndarray:
    """Uncalibrated TFT10/50/90 quantiles in physical kJ, including all four wheels."""
    model.eval()
    dynamic=scaler.inputs(data)
    values=[]
    with torch.no_grad():
        for start in range(0,len(dynamic),1024):
            values.append(model(torch.from_numpy(dynamic[start:start+1024]),torch.from_numpy(data.static[start:start+1024])).numpy())
    return np.concatenate(values)*scaler.target_std[...,None]+scaler.target_mean[...,None]


def train_neural(kind: str, training: ForecastWindows, validation: ForecastWindows, scaler: ForecastScaler,
                 *, hidden: int, learning_rate: float, seed: int, epochs: int = 12) -> tuple[object,dict]:
    started=time.perf_counter()
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model=neural_model(kind,training.static_widths,hidden)
        _neutral_unknown_static(model,kind,training.static_widths,hidden)
        loader=DataLoader(TensorDataset(torch.from_numpy(scaler.inputs(training)),torch.from_numpy(training.static),
                                       torch.from_numpy(scaler.targets(training))),batch_size=512,shuffle=True,
                          generator=torch.Generator().manual_seed(seed))
        optimizer=torch.optim.AdamW(model.parameters(),lr=learning_rate,weight_decay=.0001)
        history,best,best_state,best_epoch,stale=[],float("inf"),None,0,0
        for epoch in range(epochs):
            model.train()
            losses=[]
            for dynamic,static,target in loader:
                optimizer.zero_grad(set_to_none=True)
                prediction=model(dynamic,static)
                loss=quantile_loss(prediction,target) if kind=="tft" else torch.mean((prediction-target)**2)
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite neural training loss")
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                optimizer.step()
                losses.append(float(loss.detach()))
            predicted,_=project_nonnegative(neural_prediction(model,kind,validation,scaler))
            score=forecast_metrics(validation.target,predicted)["rmse_kj"]
            history.append({"epoch":epoch+1,"training_loss":float(np.mean(losses)),"validation_rmse_kj":score})
            if score<best:
                best,best_state,best_epoch,stale=score,copy.deepcopy(model.state_dict()),epoch+1,0
            else:
                stale+=1
            if stale>=3:
                break
        model.load_state_dict(best_state)
    return model,{"seed":seed,"hidden":hidden,"learning_rate":learning_rate,"best_epoch":best_epoch,
                  "validation_rmse_kj":best,"history":history,"fit_seconds":time.perf_counter()-started,
                  "parameters":sum(p.numel() for p in model.parameters()),"loss":"pinball .1/.5/.9" if kind=="tft" else "MSE",
                  "epochs_budget":epochs,"batch_size":512,"weight_decay":.0001,"gradient_norm":1.,"patience":3}


def fit_statistical(kind: str, training: ForecastWindows, scaler: ForecastScaler, configuration: dict, seed: int = 11):
    if kind=="linear":
        model=LinearRegression()
    elif kind=="ridge":
        model=Ridge(alpha=configuration["alpha"])
    elif kind=="xgboost":
        model=NativeBoostRegressor(configuration,seed)
    else:
        raise ValueError("Unknown statistical forecast family")
    model.fit(flat_features(training,scaler),scaler.targets(training).reshape(len(training.target),12))
    return model


def statistical_prediction(model, data: ForecastWindows, scaler: ForecastScaler) -> np.ndarray:
    return scaler.inverse(model.predict(flat_features(data,scaler)).reshape(len(data.target),3,4))


class NativeBoostRegressor:
    """Pinned XGBoost native API; no dependence on sklearn's removed estimator mixin tags."""
    def __init__(self, configuration: dict | None = None, seed: int = 11):
        self.configuration,self.seed=configuration or {},seed
        self.booster: Booster | None=None

    def fit(self, inputs: np.ndarray, targets: np.ndarray):
        parameters={"max_depth":self.configuration["depth"],"eta":.05,"subsample":.9,"colsample_bytree":.9,
                    "nthread":1,"seed":self.seed,"tree_method":"hist","objective":"reg:squarederror",
                    "multi_strategy":"one_output_per_tree"}
        self.booster=train_booster(parameters,DMatrix(inputs,label=targets,nthread=1),num_boost_round=self.configuration.get("trees",150))
        return self

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        if self.booster is None:
            raise RuntimeError("Fit or reload XGBoost before predicting")
        return self.booster.predict(DMatrix(inputs,nthread=1))

    def get_booster(self) -> Booster:
        if self.booster is None:
            raise RuntimeError("XGBoost is not fitted")
        return self.booster

    def save_model(self, path) -> None:
        self.get_booster().save_model(path)

    def load_model(self, path) -> None:
        self.booster=Booster(params={"nthread":1})
        self.booster.load_model(path)
