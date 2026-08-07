from pathlib import Path

from apexsim.config import load_config
from apexsim.data.synthetic import generate_synthetic_sessions
from apexsim.sim_core.calibration import fit_longitudinal_dynamics


def test_longitudinal_calibration_runs(tmp_path: Path):
    config = load_config("configs/fast.yaml")
    config.data.sessions = 3
    config.data.session_seconds = 35
    frame = generate_synthetic_sessions(config, tmp_path / "telemetry.csv")
    calibration = fit_longitudinal_dynamics(frame)
    assert calibration.samples > 100
    assert calibration.mae_mps2 >= 0
