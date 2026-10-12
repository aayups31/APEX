"""R025 full matched benchmark; selected configs never inspect test scores."""
from __future__ import annotations

import json
import platform
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import torch

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import forecast_benchmark, temporal_fusion
from apexsim.research.forecast_benchmark import (
    DYNAMIC,
    EVENTS,
    HORIZONS,
    STATIC,
    ForecastScaler,
    ForecastWindows,
    NativeBoostRegressor,
    build_forecast_windows,
    fit_statistical,
    flat_features,
    forecast_metrics,
    neural_model,
    neural_prediction,
    neural_quantile_prediction,
    project_nonnegative,
    statistical_prediction,
    train_neural,
    transparent_prediction,
)
from apexsim.research.tyre_energy import WHEEL_NAMES
from apexsim.research.tyre_energy_dataset import read_tyre_energy_dataset

DATASET_SEAL="7793df65b58884be74529ecf3114ccf2efc310d0a3dd99dfa9edec4d961c2272"


def detailed_metrics(actual: np.ndarray, prediction: np.ndarray, metadata: list[dict]) -> dict:
    result={"aggregate":forecast_metrics(actual,prediction),"per_wheel_horizon":[],"per_event_horizon":[]}
    for h,horizon in enumerate(HORIZONS):
        for w,wheel in enumerate(WHEEL_NAMES):
            result["per_wheel_horizon"].append({"horizon":horizon,"wheel":wheel,**forecast_metrics(actual[:,h,w],prediction[:,h,w])})
        for event in sorted({m["event_id"] for m in metadata}):
            selection=np.array([m["event_id"]==event for m in metadata])
            result["per_event_horizon"].append({"horizon":horizon,"event_id":event,"origins":int(selection.sum()),
                                                **forecast_metrics(actual[selection,h],prediction[selection,h])})
    return result


def prediction_intervals(actual: np.ndarray, prediction: np.ndarray, persistence: np.ndarray, metadata: list[dict]) -> dict:
    """Sequence-cluster paired MSE differences, not independent frame confidence."""
    groups={}
    error=np.mean((actual-prediction)**2,axis=(1,2))
    base=np.mean((actual-persistence)**2,axis=(1,2))
    for i,m in enumerate(metadata):
        entries=groups.setdefault(m["sequence_id"],[])
        entries.append(error[i]-base[i])
    values=np.array([(sum(v),len(v)) for v in groups.values()])
    rng=np.random.default_rng(2025)
    results=[]
    for _ in range(500):
        selected=values[rng.integers(0,len(values),len(values))]
        results.append(selected[:,0].sum()/selected[:,1].sum())
    return {"sequence_clusters":len(values),"resamples":500,"seed":2025,
            "paired_mse_minus_persistence_kj2_lower_95":float(np.quantile(results,.025)),
            "paired_mse_minus_persistence_kj2_upper_95":float(np.quantile(results,.975))}


def _save_checkpoint(model, kind: str, path: Path) -> None:
    if kind in ("linear","ridge"):
        np.savez(path,coef=model.coef_,intercept=model.intercept_)
    elif kind=="xgboost":
        model.save_model(path)
    else:
        torch.save(model.state_dict(),path)


def checkpoint_prediction(path: Path, record: dict, data: ForecastWindows, scaler: ForecastScaler) -> np.ndarray:
    kind=record["kind"]
    if kind in ("linear","ridge"):
        with np.load(path,allow_pickle=False) as stored:
            result=flat_features(data,scaler)@stored["coef"].T+stored["intercept"]
        return scaler.inverse(result.reshape(len(data.target),3,4))
    if kind=="xgboost":
        model=NativeBoostRegressor()
        model.load_model(path)
        return statistical_prediction(model,data,scaler)
    with torch.random.fork_rng(devices=[]):
        model=neural_model(kind,data.static_widths,record["hidden"])
        model.load_state_dict(torch.load(path,map_location="cpu",weights_only=True))
    return neural_prediction(model,kind,data,scaler)


def run_forecast_benchmark(dataset_path: Path, output: Path, profile: str = "research", progress: Callable[[str],None] | None = None) -> dict:
    """Input-sealed public benchmark, or visibly smaller execution-only smoke."""
    if output.exists():
        raise FileExistsError(f"Forecast output exists: {output}")
    if profile not in ("research","smoke") or output.resolve().is_relative_to(dataset_path.resolve()):
        raise ValueError("Invalid forecast profile/output boundary")
    # Read metadata only before accessing any potentially protected telemetry.
    quality=json.loads((dataset_path/"quality.json").read_text(encoding="utf-8"))
    for source in quality["sources"]:
        query=source["query"]
        assert_development_event(query["year"],query["round_number"],event_id=source["event_id"])
    table,input_manifest=read_tyre_energy_dataset(dataset_path)
    if profile=="research" and input_manifest["content_sha256"]!=DATASET_SEAL:
        raise ValueError("Research forecast benchmark requires the frozen R024 dataset seal")
    watched=[dataset_path/"manifest.json",dataset_path/"samples.parquet",Path(__file__),Path(forecast_benchmark.__file__),Path(temporal_fusion.__file__)]
    before={str(p):file_sha256(p) for p in watched}
    windows=build_forecast_windows(table.to_pandas())
    training,validation,test=(windows.subset(events) for events in (EVENTS[:2],EVENTS[2:3],EVENTS[3:]))
    scaler=ForecastScaler.fit(training)
    if profile=="research" and min(len(d.target) for d in (training,validation,test))<1000:
        raise ValueError("Insufficient complete matched public forecast windows")
    output.mkdir(parents=True,exist_ok=False)
    records,trials,metrics,validation_scores=[],[],{},{}
    predictions={}
    old_threads=torch.get_num_threads()
    torch.set_num_threads(1)
    started=time.perf_counter()
    try:
        for method in ("persistence","trend"):
            validation_pred,_=project_nonnegative(transparent_prediction(validation,method))
            validation_scores[method]=forecast_metrics(validation.target,validation_pred)["rmse_kj"]
            raw=transparent_prediction(test,method)
            projected,correction=project_nonnegative(raw)
            predictions[method]=projected
            predictions[method+"_raw"]=raw
            metrics[method]={**detailed_metrics(test.target,projected,test.metadata),"raw":forecast_metrics(test.target,raw),"projection":correction}
        seeds=(11,23) if profile=="research" else (11,)
        for kind in ("linear","ridge","xgboost","gru","lstm","tft"):
            if kind=="linear":
                configurations=[{}]
            elif kind=="ridge":
                configurations=[{"alpha":.1},{"alpha":10.}]
            elif kind=="xgboost":
                configurations=[{"depth":3,"trees":150},{"depth":5,"trees":150}]
                if profile=="smoke":
                    configurations=[{"depth":3,"trees":5}]
            else:
                configurations=[{"hidden":16,"learning_rate":.001},{"hidden":32,"learning_rate":.0003}]
                if profile=="smoke":
                    configurations=[{"hidden":8,"learning_rate":.001}]
            candidates=[]
            for configuration_index,configuration in enumerate(configurations):
                models,reports=[],[]
                trial_seeds=seeds if kind not in ("linear","ridge") else (11,)
                for seed in trial_seeds:
                    fit_started=time.perf_counter()
                    if kind in ("gru","lstm","tft"):
                        model,report=train_neural(kind,training,validation,scaler,seed=seed,epochs=12 if profile=="research" else 2,**configuration)
                        val_raw=neural_prediction(model,kind,validation,scaler)
                    else:
                        model=fit_statistical(kind,training,scaler,configuration,seed)
                        val_raw=statistical_prediction(model,validation,scaler)
                        val,_=project_nonnegative(val_raw)
                        parameters=int(model.coef_.size+model.intercept_.size) if kind in ("linear","ridge") else None
                        tree_nodes=len(model.get_booster().trees_to_dataframe()) if kind=="xgboost" else None
                        report={"seed":seed,"validation_rmse_kj":forecast_metrics(validation.target,val)["rmse_kj"],
                                "fit_seconds":time.perf_counter()-fit_started,"parameters":parameters,
                                "tree_nodes":tree_nodes,
                                "boosted_rounds":model.get_booster().num_boosted_rounds() if kind=="xgboost" else None}
                    reports.append(report)
                    models.append(model)
                    trials.append({"kind":kind,"configuration_index":configuration_index,"configuration":configuration,**report})
                    if progress:
                        progress(f"Fitted {kind}, candidate {configuration_index+1}, seed {seed}: validation RMSE {report['validation_rmse_kj']:.6f} kJ")
                candidates.append((float(np.mean([r["validation_rmse_kj"] for r in reports])),configuration,models,reports))
            score,configuration,models,reports=min(candidates,key=lambda candidate:candidate[0])
            validation_scores[kind]=score
            for model,report in zip(models,reports,strict=True):
                seed=report["seed"]
                prediction_started=time.perf_counter()
                raw=neural_prediction(model,kind,test,scaler) if kind in ("gru","lstm","tft") else statistical_prediction(model,test,scaler)
                projected,correction=project_nonnegative(raw)
                name=f"{kind}_seed{seed}"
                extension="npz" if kind in ("linear","ridge") else "ubj" if kind=="xgboost" else "pt"
                checkpoint=f"{name}.{extension}"
                _save_checkpoint(model,kind,output/checkpoint)
                record={"name":name,"kind":kind,"seed":seed,"configuration":configuration,"checkpoint":checkpoint,
                        "hidden":configuration.get("hidden"),"selected_validation_rmse_kj":score,"fit_report":report}
                reloaded=checkpoint_prediction(output/checkpoint,record,test,scaler)
                if not np.allclose(reloaded,raw,rtol=1e-6,atol=1e-7):
                    raise ValueError(f"Forecast checkpoint prediction mismatch: {name}")
                record["reload_max_absolute_difference_kj"]=float(np.max(abs(reloaded-raw)))
                records.append(record)
                predictions[name]=projected
                predictions[name+"_raw"]=raw
                metrics[name]={**detailed_metrics(test.target,projected,test.metadata),"raw":forecast_metrics(test.target,raw),
                               "projection":correction,"inference_and_reload_seconds":time.perf_counter()-prediction_started}
                if kind=="tft":
                    quantiles=neural_quantile_prediction(model,test,scaler)
                    projected_quantiles,quantile_correction=project_nonnegative(quantiles)
                    predictions[name+"_quantiles_raw"]=quantiles
                    predictions[name+"_quantiles_projected"]=projected_quantiles
                    metrics[name]["uncalibrated_80_interval"]={
                        "coverage":float(np.mean((test.target>=projected_quantiles[...,0])&(test.target<=projected_quantiles[...,2]))),
                        "mean_width_kj":float(np.mean(projected_quantiles[...,2]-projected_quantiles[...,0])),
                        "quantile_projection":quantile_correction,"nominal_coverage":.8}
        # Config selection and family ranking use validation only, not this test table.
        winner=min(validation_scores,key=validation_scores.get)
        for name in metrics:
            metrics[name]["paired_uncertainty_vs_persistence"]=prediction_intervals(test.target,predictions[name],predictions["persistence"],test.metadata)
        elapsed=time.perf_counter()-started
    finally:
        torch.set_num_threads(old_threads)
    if before!={str(p):file_sha256(p) for p in watched}:
        raise ValueError("Forecast input/code changed during training")
    summary={"schema_version":"apex-tyre-forecast-benchmark-v1","profile":profile,"classification":"ADAPTATION",
             "R025_benchmark_complete":True,"task_closure_eligible":profile=="research","promotion":False,
             "target_quality":"PROXY_NOT_MEASURED","input_truth":quality.get("input_truth","FASTF1_PARSED_SOURCE; upstream reconstruction possible"),
             "input_field_truth_labels":{field.name:field.metadata[b"truth_label"].decode() for field in table.schema},
             "input_dataset_sha256":input_manifest["content_sha256"],"models_requested":["linear","ridge","xgboost","gru","lstm","tft"],
             "records":records,"training_trials":trials,"validation_scores":validation_scores,"validation_selected_family":winner,
             "metrics":metrics,"split":{"train":list(EVENTS[:2]),"validation":list(EVENTS[2:3]),"test":list(EVENTS[3:])},
             "origins":{"train":len(training.target),"validation":len(validation.target),"test":len(test.target)},
             "horizons_native_samples":list(HORIZONS),"history_native_samples":8,"dynamic_fields":list(DYNAMIC),"static_fields":list(STATIC),
             "vocabulary":windows.vocabulary,"elapsed_test_horizon_s_quantiles":np.quantile([m["elapsed_horizons_s"] for m in test.metadata],[0,.5,.95,1],axis=0).tolist(),
             "fit_and_evaluation_seconds":elapsed,"environment":{"python":platform.python_version(),"numpy":np.__version__,
                     "torch":torch.__version__,"xgboost":__import__("xgboost").__version__,"sklearn":__import__("sklearn").__version__,"cpu_threads":1},
             "implementation_sha256":{p.name:before[str(p)] for p in watched[2:]},
             "limitations":["R024 proxy targets, not measured wheel energy","Eight-sample native irregular histories; direct sample-index forecasts",
                            "Training-only vocabularies; test tracks all unseen in this five-event slice",
                            "Validation search budget limited; TFT is a compact architectural adaptation with native quantile loss",
                            "All output projections and raw errors disclosed; no teacher forcing/future covariates",
                            "No R026 broader seen-track study, paper reproduction, explanation faithfulness or production promotion"]}
    summary["content_sha256"]=payload_sha256(summary)
    write_manifest(output/"summary.json",summary)
    write_manifest(output/"scaler.json",scaler.as_dict())
    write_manifest(output/"window_metadata.json",windows.metadata)
    write_manifest(output/"config.json",{"vocabulary":windows.vocabulary,"records":records,"dynamic_fields":list(DYNAMIC),"split":summary["split"]})
    np.savez_compressed(output/"windows.npz",dynamic=windows.dynamic,static=windows.static,target=windows.target)
    np.savez_compressed(output/"test_predictions.npz",actual=test.target,**predictions)
    manifest={"schema_version":"apex-tyre-forecast-manifest-v1","summary_sha256":summary["content_sha256"],
              "files":{p.name:{"sha256":file_sha256(p),"bytes":p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"]=payload_sha256(manifest)
    write_manifest(output/"manifest.json",manifest)
    return summary


def verify_forecast_benchmark(output: Path) -> dict:
    """Reload every selected checkpoint and reproduce all held-out point predictions."""
    manifest=json.loads((output/"manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version")!="apex-tyre-forecast-manifest-v1" or manifest["content_sha256"]!=payload_sha256({k:v for k,v in manifest.items() if k!="content_sha256"}):
        raise ValueError("Forecast manifest hash/schema mismatch")
    if set(manifest["files"])!={p.name for p in output.iterdir()}-{"manifest.json"}:
        raise ValueError("Forecast artifact inventory mismatch")
    for name,record in manifest["files"].items():
        if Path(name).name!=name or file_sha256(output/name)!=record["sha256"] or (output/name).stat().st_size!=record["bytes"]:
            raise ValueError(f"Forecast artifact hash mismatch: {name}")
    summary=json.loads((output/"summary.json").read_text(encoding="utf-8"))
    if summary["content_sha256"]!=manifest["summary_sha256"] or summary["content_sha256"]!=payload_sha256({k:v for k,v in summary.items() if k!="content_sha256"}):
        raise ValueError("Forecast summary binding mismatch")
    metadata=json.loads((output/"window_metadata.json").read_text(encoding="utf-8"))
    with np.load(output/"windows.npz",allow_pickle=False) as stored:
        windows=ForecastWindows(stored["dynamic"],stored["static"],stored["target"],metadata,summary["vocabulary"])
    train,test=windows.subset(EVENTS[:2]),windows.subset(EVENTS[3:])
    stored_scaler=json.loads((output/"scaler.json").read_text(encoding="utf-8"))
    scaler=ForecastScaler(*(np.array(stored_scaler[key]) for key in ("input_mean","input_std","target_mean","target_std")))
    if scaler.as_dict()!=ForecastScaler.fit(train).as_dict():
        raise ValueError("Forecast scaler is not training-only on reload")
    old=torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        with np.load(output/"test_predictions.npz",allow_pickle=False) as saved:
            if not np.array_equal(saved["actual"],test.target):
                raise ValueError("Forecast held-out target binding mismatch")
            for record in summary["records"]:
                raw=checkpoint_prediction(output/record["checkpoint"],record,test,scaler)
                if not np.allclose(raw,saved[record["name"]+"_raw"],rtol=1e-6,atol=1e-7):
                    raise ValueError("Forecast checkpoint reload mismatch")
                projected,_=project_nonnegative(raw)
                if not np.allclose(projected,saved[record["name"]],rtol=1e-6,atol=1e-7):
                    raise ValueError("Forecast projected checkpoint reload mismatch")
                if record["kind"]=="tft":
                    with torch.random.fork_rng(devices=[]):
                        model=neural_model("tft",test.static_widths,record["hidden"])
                        model.load_state_dict(torch.load(output/record["checkpoint"],map_location="cpu",weights_only=True))
                    quantiles=neural_quantile_prediction(model,test,scaler)
                    if not np.allclose(quantiles,saved[record["name"]+"_quantiles_raw"],rtol=1e-6,atol=1e-7):
                        raise ValueError("TFT quantile checkpoint reload mismatch")
    finally:
        torch.set_num_threads(old)
    families={record["kind"] for record in summary["records"]}
    if families!=set(summary["models_requested"]):
        raise ValueError("Requested forecast model family missing")
    return {"verified":True,"families":sorted(families),"checkpoints":len(summary["records"]),
            "task_closure_eligible":summary["task_closure_eligible"],"summary_sha256":summary["content_sha256"]}


def make_forecast_smoke_dataset(output: Path) -> Path:
    """SIMULATED native-format R024 fixture, full public provenance verifier retained."""
    from apexsim.research.tyre_energy_dataset import FIELDS, UNKNOWN, VERSION, sample_schema, validate_samples

    if output.exists():
        raise FileExistsError("Forecast smoke dataset must be fresh")
    rng=np.random.default_rng(2525)
    rows,sources=[],[]
    for event_index,event in enumerate(EVENTS):
        streams=[]
        for driver in ("4","44"):
            for i in range(80):
                row={name:None if name in UNKNOWN else "fixture" if __import__("pyarrow").types.is_string(dtype)
                     else False if __import__("pyarrow").types.is_boolean(dtype) else 0 for name,(dtype,_,_) in FIELDS.items()}
                row.update(event_id=event,session_id=event+"_SIMULATED",driver_id=driver,track_id=f"sim_track{event_index}",
                           compound="MEDIUM",sequence_id=f"{event}_{driver}",segment_id=f"{event}_{driver}",
                           sample_id=i,native_car_row=i,car_history_start_row=max(0,i-4),native_position_row=i,
                           position_history_start_row=max(0,i-6),lap_number=1,time_s=i*.25,position_time_s=i*.25,
                           dt_s=.25,speed_kmh=180.+i*.2,speed_mps=50.+i*.2/3.6,throttle=.6,throttle_percent=60.,
                           longitudinal_accel_mps2=.2/3.6/.25,geometry_speed_mps=50.,mass_prior_kg=900.)
                for w,wheel in enumerate(WHEEL_NAMES):
                    value=1.+.2*np.sin(i*.1+w)+rng.normal(0,.01)
                    row[f"tyre_energy_{wheel}_kj"]=float(value)
                    row[f"tyre_power_{wheel}_kw"]=float(value/.25)
                rows.append(row)
            streams.append({"driver_id":driver,"native_car_rows":81,"native_position_rows":80,"accepted_rows":80,
                            "rejected_rows":1,"rejection_counts":{"SIMULATED_exclusion":1}})
        sources.append({"event_id":event,"query":{"year":2024,"round_number":int(event[-2:]),"session":"R"},"streams":streams})
    import pyarrow as pa
    import pyarrow.parquet as pq

    table=pa.Table.from_pylist(rows,schema=sample_schema())
    output.mkdir(parents=True)
    pq.write_table(table,output/"samples.parquet")
    excluded=[{"event_id":s["event_id"],"driver_id":d["driver_id"],"native_car_row":80,"reason":"SIMULATED_exclusion"} for s in sources for d in s["streams"]]
    pq.write_table(pa.Table.from_pylist(excluded),output/"rejections.parquet")
    mask={"schema_version":"SIMULATED_FIXTURE"}
    mask["content_sha256"]=payload_sha256(mask)
    write_manifest(output/"eligible_input.json",mask)
    write_manifest(output/"config.json",{"field_truth_labels":{k:label for k,(_,label,_) in FIELDS.items()},"field_units":{k:unit for k,(_,_,unit) in FIELDS.items()}})
    write_manifest(output/"quality.json",{"validation":validate_samples(table),"target_quality":"PROXY_NOT_MEASURED","input_truth":"SIMULATED","sources":sources})
    manifest={"schema_version":VERSION,"eligible_dataset_sha256":mask["content_sha256"],
              "files":{p.name:{"sha256":file_sha256(p),"bytes":p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"]=payload_sha256(manifest)
    write_manifest(output/"manifest.json",manifest)
    return output
