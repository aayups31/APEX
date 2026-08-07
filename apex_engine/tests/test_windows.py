from pathlib import Path

from apexsim.config import load_config
from apexsim.contracts import MODEL_INPUT_COLUMNS, TARGET_COLUMNS
from apexsim.data.features import Standardizer
from apexsim.data.synthetic import generate_synthetic_sessions
from apexsim.data.windows import TelemetryWindowDataset, split_sessions


def test_window_shapes_and_session_split(tmp_path: Path):
    config = load_config("configs/fast.yaml")
    config.data.sessions = 5
    config.data.session_seconds = 35
    frame = generate_synthetic_sessions(config, tmp_path / "data.csv")
    splits = split_sessions(frame, 0.6, 0.2, 1)
    assert set(splits["train"]).isdisjoint(splits["test"])
    scaler = Standardizer.fit(frame[frame.session_id.isin(splits["train"])])
    dataset = TelemetryWindowDataset(frame, splits["train"], 16, 4, scaler, 20)
    sample = dataset[0]
    assert sample["history"].shape == (16, len(MODEL_INPUT_COLUMNS))
    assert sample["future_targets"].shape == (4, len(TARGET_COLUMNS))
