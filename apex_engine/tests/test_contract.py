from pathlib import Path

from apexsim.config import load_config
from apexsim.data.synthetic import generate_synthetic_sessions
from apexsim.data.validate import validate_canonical_frame


def test_synthetic_data_passes_contract(tmp_path: Path):
    config = load_config("configs/fast.yaml")
    config.data.sessions = 3
    config.data.session_seconds = 35
    frame = generate_synthetic_sessions(config, tmp_path / "data.csv")
    report = validate_canonical_frame(frame)
    assert report.passed
    assert report.sessions == 3
