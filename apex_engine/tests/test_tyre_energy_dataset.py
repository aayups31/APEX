import copy
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import tyre_energy_dataset as module
from apexsim.research.tyre_energy_dataset import (
    EVENTS,
    FIELDS,
    UNKNOWN,
    ProxyDatasetConfig,
    canonical_proxy_samples,
    motion_from_positions,
    read_tyre_energy_dataset,
    sample_schema,
    validate_samples,
)


def stream(n=80, acceleration=2., event="F1_2024_R01", driver="4"):
    t = np.arange(n) * .25
    speed = 20 + acceleration*t
    car = pd.DataFrame({"SessionTime":pd.to_timedelta(t,unit="s"), "Speed":speed*3.6,
                        "Throttle":np.full(n,60.),"Brake":np.full(n,False),"Source":["car"]*n})
    pos = pd.DataFrame({"SessionTime":pd.to_timedelta(t,unit="s"), "X":(20*t+.5*acceleration*t*t)*10,
                        "Y":np.zeros(n),"Status":["OnTrack"]*n,"Source":["pos"]*n})
    laps = pd.DataFrame({"DriverNumber":[driver],"LapNumber":[1.],"Compound":["MEDIUM"],
                         "LapStartTime":pd.to_timedelta([0],unit="s"),"Time":pd.to_timedelta([t[-1]+.25],unit="s")})
    segments = [{"event_id":event,"season":2024,"round_number":int(event[-2:]),"driver":driver,
                 "track_id":"fixture","compound":"MEDIUM","segment_id":event+"_"+driver,
                 "rows":[{"lap":1,"native_row":0}]}]
    return car,pos,laps,segments


def test_independent_quadratic_motion_fixture():
    t = np.arange(-6,1)*.25
    xy = np.column_stack((20*t, 2*t*t)) + np.array([10000,-20000])
    speed,omega = motion_from_positions(t,xy)
    assert speed == pytest.approx(20.,abs=1e-8)
    assert omega == pytest.approx(.2,abs=1e-8)
    with pytest.raises(ValueError):
        motion_from_positions(np.array([0.,0.,1.]),np.ones((3,2)))


def test_hand_energy_units_and_truth_labels():
    car,pos,laps,segments = stream()
    rows,rejected = canonical_proxy_samples(car,pos,segments,laps)
    row = next(r for r in rows if r["native_car_row"]==16)
    assert row["speed_mps"] == pytest.approx(28.)
    assert row["longitudinal_accel_mps2"] == pytest.approx(2.)
    front_total=.46*900*9.81 - 900*2*.32/3.6
    rear_wheel=(900*9.81-front_total)/2
    slip=28*(.002+.010*.6**1.5+.004*.6)
    energy=900*slip*(rear_wheel/(900*9.81/4))**.18*.25/1000
    assert row["tyre_energy_rear_left_kj"] == pytest.approx(energy)
    assert row["tyre_energy_front_left_kj"] == pytest.approx(0.,abs=1e-10)
    assert row["tyre_power_rear_left_kw"] == pytest.approx(energy/.25)
    assert row["position_time_s"] <= row["time_s"]
    assert len(rows)+len(rejected)==len(car)
    table=pa.Table.from_pylist(rows,schema=sample_schema())
    assert validate_samples(table)["truth_labels_complete"]
    assert all(table[name].null_count==len(table) for name in UNKNOWN)
    assert all(table.schema.field(name).metadata[b"truth_label"]==label.encode() for name,(_,label,_) in FIELDS.items())


def test_future_inputs_do_not_change_previous_proxy_samples():
    car,pos,laps,segments=stream()
    before,_=canonical_proxy_samples(car,pos,segments,laps)
    car.loc[40:,"Speed"] += 100
    pos.loc[40:,"Y"] += 10000
    after,_=canonical_proxy_samples(car,pos,segments,laps)
    assert [r for r in before if r["native_car_row"]<40] == [r for r in after if r["native_car_row"]<40]


def test_gap_exclusion_breaks_sequence_and_pit_reset_warms_up():
    car,pos,laps,segments=stream()
    pos.loc[30:32,"Status"]="OffTrack"
    rows,rejected=canonical_proxy_samples(car,pos,segments,laps)
    assert any(r["reason"]=="unsupported_native_source_or_position_status" for r in rejected)
    assert len({r["sequence_id"] for r in rows})==2
    laps=pd.DataFrame({"DriverNumber":["4","4"],"LapNumber":[1.,2.],"Compound":["MEDIUM","MEDIUM"],
                       "LapStartTime":pd.to_timedelta([0,10],unit="s"),"Time":pd.to_timedelta([10,20],unit="s")})
    second=copy.deepcopy(segments[0])
    second.update(segment_id="second",rows=[{"lap":2,"native_row":1}])
    rows,_=canonical_proxy_samples(car,pos,[*segments,second],laps)
    assert all(r["time_s"]>=11.5 for r in rows if r["segment_id"]=="second")


def test_unknown_controls_and_duplicate_native_times_fail_closed():
    car,pos,laps,segments=stream()
    car.loc[15,"Throttle"]=104
    _,excluded=canonical_proxy_samples(car,pos,segments,laps)
    assert next(r for r in excluded if r["native_car_row"]==15)["reason"]=="unsupported_speed_or_controls"
    car.loc[2,"SessionTime"]=car.loc[1,"SessionTime"]
    with pytest.raises(ValueError,match="strictly increasing"):
        canonical_proxy_samples(car,pos,segments,laps)
    with pytest.raises(ValueError):
        ProxyDatasetConfig(mass_kg=float("nan"))


def test_measured_target_or_modified_truth_label_rejected():
    car,pos,laps,segments=stream()
    rows,_=canonical_proxy_samples(car,pos,segments,laps)
    table=pa.Table.from_pylist(rows,schema=sample_schema())
    target=sorted(UNKNOWN)[0]
    index=table.schema.get_field_index(target)
    bad=table.set_column(index,table.schema.field(index),pa.array(np.ones(len(table))))
    with pytest.raises(ValueError,match="must remain UNKNOWN"):
        validate_samples(bad)
    fields=list(table.schema)
    fields[0]=fields[0].with_metadata({b"truth_label":b"MEASURED",b"unit":b"1"})
    bad=table.cast(pa.schema(fields,metadata=table.schema.metadata))
    with pytest.raises(ValueError,match="schema"):
        validate_samples(bad)


def test_protected_event_refused_before_native_payload(tmp_path,monkeypatch):
    mask={"schema_version":"apex-tyre-pace-dataset-v1","sources":[{"event_id":e} for e in EVENTS],"segments":[]}
    mask["content_sha256"]=payload_sha256(mask)
    source=tmp_path/"eligible.json"
    write_manifest(source,mask)
    archive=tmp_path/"protected"
    archive.mkdir()
    write_manifest(archive/"manifest.json",{"query":{"year":2023,"round_number":4,"session":"R"}})
    def forbidden(_):
        pytest.fail("Protected native payload accessed")
    monkeypatch.setattr(module,"verify_fastf1_archive",forbidden)
    with pytest.raises(ValueError,match="Permanent benchmark"):
        module.build_tyre_energy_dataset([archive],source,tmp_path/"output")


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    # SIMULATED native-format fixture; the fake source verifier is limited to this
    # test. Public acceptance uses the genuine sealed archives outside tests.
    root=tmp_path_factory.mktemp("proxy-artifact")
    all_segments, sources, archives=[],[],[]
    for event in EVENTS:
        archive=root/event
        (archive/"tables/car_data").mkdir(parents=True)
        (archive/"tables/pos_data").mkdir()
        lap_frames=[]
        for driver in ("4","44"):
            car,pos,laps,segments=stream(n=1200,acceleration=0.,event=event,driver=driver)
            segments[0]["rows"][0]["native_row"]=len(lap_frames)
            if not (event=="F1_2024_R03" and driver=="44"):
                all_segments.extend(segments)
            lap_frames.append(laps)
            car.to_parquet(archive/f"tables/car_data/{driver}.parquet")
            pos.to_parquet(archive/f"tables/pos_data/{driver}.parquet")
        pd.concat(lap_frames,ignore_index=True).to_parquet(archive/"tables/laps.parquet")
        query={"year":2024,"round_number":int(event[-2:]),"session":"R"}
        native_files={p.relative_to(archive).as_posix():{"sha256":file_sha256(p),"bytes":p.stat().st_size} for p in archive.rglob("*.parquet")}
        write_manifest(archive/"manifest.json",{"query":query,"content_sha256":event,"source_manifest":{"truth":"SIMULATED"},"environment":{},"files":native_files})
        sources.append({"event_id":event,"archive_sha256":event})
        archives.append(archive)
    mask={"schema_version":"apex-tyre-pace-dataset-v1","sources":sources,"segments":all_segments}
    mask["content_sha256"]=payload_sha256(mask)
    source=root/"eligible.json"
    write_manifest(source,mask)
    patch=pytest.MonkeyPatch()
    patch.setattr(module,"verify_fastf1_archive",lambda p:json.loads((p/"manifest.json").read_text()))
    output=root/"dataset"
    args=["build-tyre-energy-dataset","--eligible-dataset",str(source),"--output",str(output)]
    for archive in archives:
        args.extend(["--archives",str(archive)])
    try:
        result=CliRunner().invoke(app,args)
        assert result.exit_code==0,result.output+repr(result.exception)
    finally:
        patch.undo()
    return output,archives,source


def test_cli_artifact_reload_and_relocation(dataset,tmp_path):
    import shutil

    output,_,_=dataset
    relocated=tmp_path/"relocated"
    shutil.copytree(output,relocated)
    result=CliRunner().invoke(app,["verify-tyre-energy-dataset",str(relocated)])
    assert result.exit_code==0,result.output+repr(result.exception)
    assert json.loads(result.output)["measured_wheel_targets"]==0
    table,_=read_tyre_energy_dataset(relocated)
    assert len(table)>7000
    quality=json.loads((relocated/"quality.json").read_text())
    source=next(s for s in quality["sources"] if s["event_id"]=="F1_2024_R03")
    missing=next(s for s in source["streams"] if s["driver_id"]=="44")
    assert missing["accepted_rows"]==0
    assert missing["rejection_counts"]=={"no_eligible_stint_segment":1200}


def test_corruption_and_output_reuse_refused(dataset,tmp_path):
    import shutil

    output,archives,source=dataset
    before={p.name:file_sha256(p) for p in output.iterdir()}
    with pytest.raises(FileExistsError):
        module.build_tyre_energy_dataset(archives,source,output)
    assert before=={p.name:file_sha256(p) for p in output.iterdir()}
    target=tmp_path/"corrupt"
    shutil.copytree(output,target)
    with (target/"samples.parquet").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError,match="hash mismatch"):
        read_tyre_energy_dataset(target)
