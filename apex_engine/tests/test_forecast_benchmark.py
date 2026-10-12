import json
import shutil

import numpy as np
import pandas as pd
import pytest
import torch
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples.tyre_forecast_benchmark import (
    make_forecast_smoke_dataset,
    run_forecast_benchmark,
    verify_forecast_benchmark,
)
from apexsim.provenance import file_sha256
from apexsim.research.forecast_benchmark import (
    EVENTS,
    ForecastScaler,
    build_forecast_windows,
    transparent_prediction,
)
from apexsim.research.temporal_fusion import TemporalFusionForecaster


@pytest.fixture(scope="module")
def fixture_dataset(tmp_path_factory):
    root=tmp_path_factory.mktemp("forecast-source")
    make_forecast_smoke_dataset(root/"source")
    return root/"source"


def test_native_windows_and_baseline_information(fixture_dataset):
    frame=pd.read_parquet(fixture_dataset/"samples.parquet")
    windows=build_forecast_windows(frame)
    assert len(windows.target)==680
    assert all(m["target_native_rows"]==[m["origin_native_row"]+h for h in (1,3,5)] for m in windows.metadata)
    assert set(m["event_id"] for m in windows.metadata)==set(EVENTS)
    predicted=transparent_prediction(windows,"persistence")
    np.testing.assert_array_equal(predicted[:,0],windows.dynamic[:,-1,-4:])
    assert predicted.shape==windows.target.shape


def test_training_scalers_and_vocab_ignore_changed_test_values(fixture_dataset):
    frame=pd.read_parquet(fixture_dataset/"samples.parquet")
    before=build_forecast_windows(frame)
    scaler=ForecastScaler.fit(before.subset(EVENTS[:2]))
    changed=frame.copy()
    changed.loc[changed.event_id.isin(EVENTS[3:]),"speed_mps"]+=10000
    changed.loc[changed.event_id.isin(EVENTS[3:]),"track_id"]="NEW_UNSEEN"
    after=build_forecast_windows(changed)
    assert scaler.as_dict()==ForecastScaler.fit(after.subset(EVENTS[:2])).as_dict()
    assert before.vocabulary==after.vocabulary
    with pytest.raises(ValueError,match="training membership"):
        ForecastScaler.fit(before)


def test_future_targets_do_not_change_past_features(fixture_dataset):
    frame=pd.read_parquet(fixture_dataset/"samples.parquet")
    original=build_forecast_windows(frame)
    frame.loc[frame.native_car_row==79,"tyre_energy_front_left_kj"]+=100
    changed=build_forecast_windows(frame)
    np.testing.assert_array_equal(original.dynamic,changed.dynamic)
    assert np.any(original.target!=changed.target)


def test_boundaries_and_protected_events_rejected(fixture_dataset):
    frame=pd.read_parquet(fixture_dataset/"samples.parquet")
    bad=frame.copy()
    bad.loc[0,"driver_id"]="99"
    with pytest.raises(ValueError,match="identity"):
        build_forecast_windows(bad)
    bad=frame.copy()
    bad.loc[0,"event_id"]="F1_2023_R04"
    with pytest.raises(ValueError,match="Permanent benchmark"):
        build_forecast_windows(bad)


def test_tft_architecture_quantiles_and_causal_attention():
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(5)
        model=TemporalFusionForecaster(14,(3,4,3),hidden=8).eval()
        output,diagnostics=model(torch.zeros(2,8,14),torch.zeros(2,10),diagnostics=True)
    assert output.shape==(2,3,4,3)
    assert torch.all(output[...,0]<output[...,1]) and torch.all(output[...,1]<output[...,2])
    assert torch.allclose(diagnostics["static_selection"].sum(-1),torch.ones(2))
    assert torch.allclose(diagnostics["past_selection"].sum(-1),torch.ones(2,8))
    attention=diagnostics["attention"]
    assert torch.allclose(attention.sum(-1),torch.ones(2,2,13))
    assert torch.all(torch.triu(attention,diagonal=1)==0)
    with pytest.raises(ValueError,match="past history"):
        model(torch.zeros(2,9,14),torch.zeros(2,10))


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp("forecast-models")
    output=root/"run"
    result=CliRunner().invoke(app,["tyre-forecast-smoke","--output",str(output)])
    assert result.exit_code==0,result.output+repr(result.exception)
    return output


def test_all_six_families_fit_and_reload(study):
    report=verify_forecast_benchmark(study)
    assert report["verified"] and not report["task_closure_eligible"]
    assert report["families"]==["gru","linear","lstm","ridge","tft","xgboost"]
    summary=json.loads((study/"summary.json").read_text())
    assert len(summary["records"])==6
    assert summary["target_quality"]=="PROXY_NOT_MEASURED"
    assert summary["input_truth"]=="SIMULATED"
    assert all(r["reload_max_absolute_difference_kj"]<1e-5 for r in summary["records"])


def test_forecast_artifact_immutable_and_corruption_refused(study,tmp_path):
    before={p.name:file_sha256(p) for p in study.iterdir()}
    with pytest.raises(FileExistsError):
        run_forecast_benchmark(study,study,"smoke")
    assert before=={p.name:file_sha256(p) for p in study.iterdir()}
    relocated=tmp_path/"relocated"
    shutil.copytree(study,relocated)
    assert verify_forecast_benchmark(relocated)["verified"]
    checkpoint=next(relocated.glob("*.pt"))
    with checkpoint.open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError,match="hash mismatch"):
        verify_forecast_benchmark(relocated)


def test_research_requires_frozen_public_dataset(fixture_dataset,tmp_path):
    with pytest.raises(ValueError,match="frozen R024 dataset"):
        run_forecast_benchmark(fixture_dataset,tmp_path/"fake")
