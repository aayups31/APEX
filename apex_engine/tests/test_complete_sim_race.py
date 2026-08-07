from apexsim.examples.complete_sim_demo import build_demo


def test_complete_race_demo_finishes(tmp_path):
    simulator = build_demo(seed=5, total_laps=2)
    result = simulator.run()
    assert len(result.standings) == 6
    assert not result.telemetry.empty
    assert (result.standings.status == "FINISHED").any()
    result.save(tmp_path)
    assert (tmp_path / "standings.csv").exists()
