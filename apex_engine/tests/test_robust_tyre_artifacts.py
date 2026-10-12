import json
import shutil

import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples.robust_tyre_demo import run_robust_tyre_demo, verify_robust_tyre_study
from apexsim.provenance import file_sha256


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp("robust")
    baseline=root/"baseline"
    result=CliRunner().invoke(app,["tyre-degradation-smoke","--output",str(baseline)])
    assert result.exit_code==0,result.output
    output=root/"robust"
    result=CliRunner().invoke(app,["robust-tyre-demo","--baseline",str(baseline),"--output",str(output),"--profile","smoke"])
    assert result.exit_code==0,result.output+repr(result.exception)
    return baseline,output


def test_cli_ensemble_reload_and_no_false_closure(study):
    _,output=study
    result=CliRunner().invoke(app,["verify-robust-tyre-study",str(output)])
    assert result.exit_code==0,result.output
    verified=json.loads(result.output)
    assert verified["verified"] and not verified["task_closure_eligible"]
    summary=json.loads((output/"summary.json").read_text())
    assert summary["shape_fit"]["training_events"]==["F1_2024_R01","F1_2024_R03"]
    assert len(summary["shape_fit"]["candidates"])==12


def test_output_immutable_and_corrupted_ensemble_refused(study,tmp_path):
    baseline,output=study
    before={p.name:file_sha256(p) for p in output.iterdir()}
    with pytest.raises(FileExistsError):
        run_robust_tyre_demo(baseline,output,"smoke")
    assert before=={p.name:file_sha256(p) for p in output.iterdir()}
    relocated=tmp_path/"relocated"
    shutil.copytree(output,relocated)
    assert verify_robust_tyre_study(relocated)["verified"]
    with (relocated/"predictive_ensembles.npz").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError,match="hash mismatch"):
        verify_robust_tyre_study(relocated)


def test_research_requires_public_baseline(study,tmp_path):
    baseline,_=study
    with pytest.raises(ValueError,match="research baseline"):
        run_robust_tyre_demo(baseline,tmp_path/"invalid")
