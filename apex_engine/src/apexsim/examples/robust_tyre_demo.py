"""Frozen R023 conditional observation comparison with complete predictive ensembles."""
from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np

from apexsim.examples.tyre_degradation_demo import EVENTS, verify_tyre_study
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import skew_tyre
from apexsim.research.hierarchical_tyre import HierarchicalTyreModel, HierarchySettings
from apexsim.research.skew_tyre import fit_observation_shape, observation_forecasts, observation_metrics
from apexsim.research.tyre_pace import PaceParameters


def load_group_posterior(baseline: Path) -> tuple[HierarchicalTyreModel, dict]:
    verify_tyre_study(baseline)
    summary = json.loads((baseline/"summary.json").read_text(encoding="utf-8"))
    posterior = summary["hierarchical_posterior"]
    parameters = summary["hierarchical_noise_fit"]["parameters"]
    noise = PaceParameters(tuple(parameters["drift"]),parameters["process_variance"],parameters["observation_variance"])
    settings = HierarchySettings(tuple(posterior["settings"]["seeds"]),posterior["settings"]["warmup"],posterior["settings"]["draws"])
    model = HierarchicalTyreModel(noise,settings)
    with np.load(baseline/"hierarchical_draws.npz",allow_pickle=False) as weights:
        model.chains,model.variance_chains = weights["parameters"],weights["group_variances"]
    model.levels = posterior["levels"]
    model.labels = ["population"]+[f"{family}:{level}" for family in ("compound","track_id","driver") for level in model.levels[family]]
    model.indices = {(family,level):model.labels.index(f"{family}:{level}") for family in model.levels for level in model.levels[family]}
    model.training_events = posterior["training_events"]
    return model,summary


def grouped_observation_metrics(rows: list[dict], fields: tuple[str,...]) -> list[dict]:
    keys = sorted({tuple(r[f] for f in fields) for r in rows})
    return [{**dict(zip(fields,key,strict=True)),**observation_metrics([r for r in rows if tuple(r[f] for f in fields)==key])} for key in keys]


def paired_crps_intervals(rows: list[dict], resamples: int = 500) -> list[dict]:
    output = []
    for horizon in (1,3,5):
        gaussian = [r for r in rows if r["method"]=="gaussian" and r["horizon"]==horizon]
        robust = [r for r in rows if r["method"]=="skew_t" and r["horizon"]==horizon]
        def key(row: dict) -> tuple:
            return row["seed"],row["segment_id"],row["origin_lap"],row["horizon"]
        gaussian,robust = sorted(gaussian,key=key),sorted(robust,key=key)
        if [key(r) for r in gaussian]!=[key(r) for r in robust]:
            raise ValueError("Robust/Gaussian forecast keys differ")
        clusters = {}
        for a,b in zip(gaussian,robust,strict=True):
            values = clusters.setdefault(a["segment_id"],[])
            values.append(b["crps_s"]-a["crps_s"])
        values = np.array([(sum(v),len(v)) for v in clusters.values()])
        rng = np.random.default_rng(2023)
        samples = []
        for _ in range(resamples):
            chosen = values[rng.integers(0,len(values),len(values))]
            samples.append(chosen[:,0].sum()/chosen[:,1].sum())
        output.append({"horizon":horizon,"clusters":len(values),"resamples":resamples,"seed":2023,
                       "skew_minus_gaussian_crps_s_lower_95":float(np.quantile(samples,.025)),
                       "skew_minus_gaussian_crps_s_upper_95":float(np.quantile(samples,.975)),
                       "scope":"paired segment clusters include all seed replicas; not independent lap/seed samples"})
    return output


def run_robust_tyre_demo(baseline: Path, output: Path, profile: str = "research") -> dict:
    if output.exists():
        raise FileExistsError(f"Robust output exists: {output}")
    if profile not in ("research","smoke") or output.resolve().is_relative_to(baseline.resolve()):
        raise ValueError("Invalid robust profile or output inside baseline")
    hierarchy,base = load_group_posterior(baseline)
    if profile=="research" and not base["task_closure_eligible"]:
        raise ValueError("Public robust closure requires a research baseline")
    dataset = json.loads((baseline/"dataset.json").read_text(encoding="utf-8"))
    if hierarchy.training_events != list(EVENTS[:2]):
        raise ValueError("R023 group posterior has unsupported training membership")
    watched = [baseline/"manifest.json",baseline/"dataset.json",Path(__file__),Path(skew_tyre.__file__)]
    before = {str(p):file_sha256(p) for p in watched}
    train = [s for s in dataset["segments"] if s["event_id"] in EVENTS[:2]]
    shape,fit = fit_observation_shape(train,hierarchy,particles=512 if profile=="research" else 32)
    rows,draws = [],[]
    settings = {"group_draws":32,"state_particles":64} if profile=="research" else {"group_draws":4,"state_particles":16}
    seeds = (11,23,37) if profile=="research" else (11,)
    for seed in seeds:
        for phase,events in (("validation",EVENTS[2:3]),("test",EVENTS[3:])):
            segments = [s for s in dataset["segments"] if s["event_id"] in events]
            for observation in (None,shape):
                forecast,ensemble = observation_forecasts(segments,hierarchy,observation,seed=seed,**settings)
                rows.extend({**r,"phase":phase,"ensemble_row":len(draws)+i} for i,r in enumerate(forecast))
                draws.extend(ensemble)
    test = [r for r in rows if r["phase"]=="test"]
    metrics = grouped_observation_metrics(test,("method","horizon"))
    improvements = []
    for horizon in (1,3,5):
        a = next(r for r in metrics if r["method"]=="gaussian" and r["horizon"]==horizon)
        b = next(r for r in metrics if r["method"]=="skew_t" and r["horizon"]==horizon)
        improvements.append({"horizon":horizon,"crps_relative_improvement":1-b["crps_s"]/a["crps_s"],
                             "rmspe_relative_improvement":1-b["rmspe_percent"]/a["rmspe_percent"]})
    accepted = ((sum(r["crps_relative_improvement"]>=.01 for r in improvements)>=2 and
                 min(r["rmspe_relative_improvement"] for r in improvements)>=-.05) or
                (sum(r["rmspe_relative_improvement"]>=.01 for r in improvements)>=2 and
                 min(r["crps_relative_improvement"] for r in improvements)>=-.05))
    summary = {"schema_version":"apex-robust-tyre-study-v1","profile":profile,"classification":"ADAPTATION",
               "model_decision":"ACCEPT_CONDITIONAL_RESEARCH" if accepted else "REJECT_NO_FROZEN_IMPROVEMENT",
               "R023_comparison_complete":True,"task_closure_eligible":profile=="research",
               "promotion":False,"baseline_summary_sha256":base["content_sha256"],"input_dataset_sha256":dataset["content_sha256"],
               "target_quality":"FUEL_CORRECTED_PACE_PROXY","fuel_prior":dataset["fuel_prior"],"input_truth_labels":dataset["truth_labels"],
               "environment":{"python":platform.python_version(),"numpy":np.__version__,"scipy":__import__("scipy").__version__},
               "shape_fit":fit,"settings":settings,"seeds":list(seeds),"split":base["hierarchical_split"],
               "test_metrics":metrics,"validation_metrics":grouped_observation_metrics([r for r in rows if r["phase"]=="validation"],("method","horizon")),
               "event_metrics":grouped_observation_metrics(test,("method","event_id","horizon")),
               "seed_metrics":grouped_observation_metrics(test,("method","seed","horizon")),
               "improvements":improvements,"paired_crps_intervals":paired_crps_intervals(test),
               "limitations":["Gaussian-trained hierarchy and Q/R fixed; conditional modular adaptation",
                              "Finite particles and posterior draw subset; finite-ensemble CRPS bias",
                              "Reused development test events, not untouched benchmark",
                              "No full paper reproduction, guaranteed calibration repair or production promotion"],
               "implementation_sha256":{p.name:file_sha256(p) for p in watched[2:]}}
    if before!={str(p):file_sha256(p) for p in watched}:
        raise ValueError("Robust study input/code changed during evaluation")
    summary["content_sha256"] = payload_sha256(summary)
    output.mkdir(parents=True,exist_ok=False)
    write_manifest(output/"summary.json",summary)
    write_manifest(output/"predictions.json",rows)
    np.savez_compressed(output/"predictive_ensembles.npz",draws=np.array(draws))
    np.savez_compressed(output/"group_posterior.npz",parameters=hierarchy.chains,group_variances=hierarchy.variance_chains)
    write_manifest(output/"config.json",{"shape_fit":fit,"settings":settings,"seeds":list(seeds)})
    manifest = {"schema_version":"apex-robust-tyre-manifest-v1","summary_sha256":summary["content_sha256"],
                "files":{p.name:{"sha256":file_sha256(p),"bytes":p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output/"manifest.json",manifest)
    return summary


def verify_robust_tyre_study(output: Path) -> dict:
    manifest = json.loads((output/"manifest.json").read_text(encoding="utf-8"))
    required = {"summary.json","predictions.json","predictive_ensembles.npz","group_posterior.npz","config.json"}
    if (manifest.get("schema_version")!="apex-robust-tyre-manifest-v1" or set(manifest["files"])!=required
            or manifest["content_sha256"]!=payload_sha256({k:v for k,v in manifest.items() if k!="content_sha256"})):
        raise ValueError("Robust manifest schema/hash/inventory mismatch")
    for name,record in manifest["files"].items():
        if file_sha256(output/name)!=record["sha256"] or (output/name).stat().st_size!=record["bytes"]:
            raise ValueError(f"Robust artifact hash mismatch: {name}")
    summary = json.loads((output/"summary.json").read_text(encoding="utf-8"))
    if summary["content_sha256"]!=manifest["summary_sha256"] or summary["content_sha256"]!=payload_sha256({k:v for k,v in summary.items() if k!="content_sha256"}):
        raise ValueError("Robust summary binding mismatch")
    rows = json.loads((output/"predictions.json").read_text(encoding="utf-8"))
    with np.load(output/"predictive_ensembles.npz",allow_pickle=False) as stored:
        draws = stored["draws"]
        if draws.shape!=(len(rows),summary["settings"]["group_draws"]*summary["settings"]["state_particles"]) or not np.isfinite(draws).all():
            raise ValueError("Invalid robust predictive ensemble")
        for i,row in enumerate(rows):
            if row["ensemble_row"]!=i or not np.isclose(row["crps_s"],skew_tyre.empirical_crps(draws[i],row["observed_s"]),rtol=1e-12,atol=1e-12):
                raise ValueError("Robust score/ensemble reload mismatch")
    return {"verified":True,"task_closure_eligible":summary["task_closure_eligible"],"model_decision":summary["model_decision"],"summary_sha256":summary["content_sha256"]}
