from __future__ import annotations

import json
from pathlib import Path

import gradio as gr
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import torch

from apexsim.config import load_config
from apexsim.contracts import MODEL_INPUT_COLUMNS
from apexsim.data.features import Standardizer
from apexsim.data.windows import TelemetryWindowDataset
from apexsim.pipeline.stages import load_trained_model
from apexsim.simulation import Scenario, rollout


CUSTOM_CSS = """
.gradio-container {max-width: 1500px !important; background: radial-gradient(circle at 15% 5%, #191b22 0%, #090a0e 48%, #050506 100%);}
#hero {border: 1px solid #30343d; border-radius: 22px; padding: 24px; background: linear-gradient(135deg, rgba(239,35,60,.18), rgba(255,255,255,.025));}
.metric-card {border: 1px solid #2e323b; border-radius: 16px; padding: 14px; background: rgba(255,255,255,.035);}
"""


def _load_bundle(run_dir: Path, config_path: Path):
    config = load_config(config_path)
    frame = pd.read_csv(run_dir / "canonical_telemetry.csv")
    splits = json.loads((run_dir / "splits.json").read_text())
    standardizer = Standardizer.from_dict(json.loads((run_dir / "standardizer.json").read_text()))
    model = load_trained_model(config, run_dir)
    dataset = TelemetryWindowDataset(
        frame,
        splits["test"],
        config.data.sequence_length,
        max(config.data.prediction_horizon, 80),
        standardizer,
        max_windows=200,
    )
    return config, frame, splits, standardizer, model, dataset


def _track_figure(frame: pd.DataFrame, session_id: str) -> go.Figure:
    session = frame[frame.session_id == session_id]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=session.x_m,
            y=session.y_m,
            mode="lines",
            line=dict(width=6, color="#ef233c"),
            hovertemplate="x=%{x:.0f}m<br>y=%{y:.0f}m<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title=f"Track trace - {session_id}",
        xaxis_visible=False,
        yaxis_visible=False,
        height=430,
        margin=dict(l=15, r=15, t=50, b=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_scaleanchor="x",
    )
    return fig


def _telemetry_figure(frame: pd.DataFrame, session_id: str) -> go.Figure:
    session = frame[frame.session_id == session_id].iloc[:1200]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=session.timestamp_s, y=session.speed_mps * 3.6, name="Speed km/h"))
    fig.add_trace(go.Scatter(x=session.timestamp_s, y=session.throttle * 100, name="Throttle %", yaxis="y2"))
    fig.add_trace(go.Scatter(x=session.timestamp_s, y=session.brake * 100, name="Brake %", yaxis="y2"))
    fig.update_layout(
        template="plotly_dark",
        title="Observed telemetry",
        xaxis_title="Time (s)",
        yaxis_title="Speed (km/h)",
        yaxis2=dict(title="Pedal (%)", overlaying="y", side="right", range=[0, 100]),
        height=430,
        legend=dict(orientation="h"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,.02)",
    )
    return fig


def create_app(run_dir: str | Path, config_path: str | Path = "configs/fast.yaml") -> gr.Blocks:
    run_path = Path(run_dir)
    config, frame, splits, standardizer, model, dataset = _load_bundle(run_path, Path(config_path))
    metrics = json.loads((run_path / "metrics.json").read_text())
    ablations = pd.DataFrame(json.loads((run_path / "ablations.json").read_text()))
    sessions = sorted(frame.session_id.unique().tolist())

    def update_session(session_id: str):
        session = frame[frame.session_id == session_id]
        cards = (
            f"### Session snapshot\n"
            f"- **Driver:** {session.driver_id.iloc[0]}\n"
            f"- **Track:** {session.track_id.iloc[0]}\n"
            f"- **Frames:** {len(session):,}\n"
            f"- **Peak speed:** {session.speed_mps.max() * 3.6:.1f} km/h\n"
            f"- **Rain peak:** {session.rainfall.max():.2f}"
        )
        return _track_figure(frame, session_id), _telemetry_figure(frame, session_id), cards

    def simulate(index: int, throttle: float, brake: float, grip: float, rain: float, tyre: float):
        index = int(np.clip(index, 0, len(dataset) - 1))
        item = dataset[index]
        history_z = item["history"].numpy()
        future_z = item["future_inputs"].numpy()
        history_raw = history_z * standardizer.input_std + standardizer.input_mean
        future_raw = future_z * standardizer.input_std + standardizer.input_mean
        scenario = Scenario(throttle, brake, grip, rain, tyre)
        predicted = rollout(model, history_raw, future_raw, standardizer, scenario)
        actual = standardizer.inverse_targets(item["future_targets"].numpy())
        seconds = np.arange(len(predicted)) / config.data.sample_hz
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=seconds, y=actual[:, 0] * 3.6, name="Recorded future", line=dict(width=3)))
        fig.add_trace(go.Scatter(x=seconds, y=predicted[:, 0] * 3.6, name="Imagined future", line=dict(width=3, dash="dash")))
        fig.update_layout(
            template="plotly_dark",
            title="World-model rollout: recorded vs imagined speed",
            xaxis_title="Seconds into future",
            yaxis_title="Speed (km/h)",
            height=470,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,.02)",
        )
        delta = float((predicted[-1, 0] - actual[-1, 0]) * 3.6)
        summary = (
            f"### Scenario result\n"
            f"- Rollout horizon: **{len(predicted) / config.data.sample_hz:.1f} s**\n"
            f"- Final imagined speed: **{predicted[-1, 0] * 3.6:.1f} km/h**\n"
            f"- Difference from recorded future: **{delta:+.1f} km/h**\n"
            f"- Model: **{config.model.kind.upper()} world model**"
        )
        return fig, summary

    with gr.Blocks(title="Project APEX") as app:
        gr.Markdown(
            """
<div id="hero">
<h1>PROJECT APEX</h1>
<h3>F1 Telemetry World-Simulation Engine</h3>
<p>Explore real-shaped telemetry, inspect the learned world model, alter future conditions, and watch the engine imagine what happens next.</p>
</div>
            """
        )
        with gr.Tabs():
            with gr.Tab("Race Engineering Desk"):
                with gr.Row():
                    session_select = gr.Dropdown(sessions, value=sessions[0], label="Session")
                    session_summary = gr.Markdown()
                with gr.Row():
                    track_plot = gr.Plot(_track_figure(frame, sessions[0]))
                    telemetry_plot = gr.Plot(_telemetry_figure(frame, sessions[0]))
                session_select.change(update_session, session_select, [track_plot, telemetry_plot, session_summary])
                initial = frame[frame.session_id == sessions[0]]
                session_summary.value = f"**Frames:** {len(initial):,} | **Peak speed:** {initial.speed_mps.max()*3.6:.1f} km/h"

            with gr.Tab("World Rollout Simulator"):
                gr.Markdown("Change the future controls and environment. The model rolls forward from a real test-window history.")
                with gr.Row():
                    with gr.Column(scale=1):
                        sample_index = gr.Slider(0, max(0, len(dataset) - 1), value=0, step=1, label="Test window")
                        throttle = gr.Slider(0.7, 1.3, value=1.0, step=0.02, label="Throttle multiplier")
                        brake = gr.Slider(0.7, 1.3, value=1.0, step=0.02, label="Brake multiplier")
                        grip = gr.Slider(0.6, 1.2, value=1.0, step=0.02, label="Grip multiplier")
                        rain = gr.Slider(-0.2, 0.5, value=0.0, step=0.02, label="Rain change")
                        tyre = gr.Slider(0.5, 2.0, value=1.0, step=0.05, label="Tyre degradation multiplier")
                        run_button = gr.Button("IMAGINE FUTURE", variant="primary")
                    with gr.Column(scale=2):
                        rollout_plot = gr.Plot()
                        rollout_summary = gr.Markdown()
                run_button.click(simulate, [sample_index, throttle, brake, grip, rain, tyre], [rollout_plot, rollout_summary])

            with gr.Tab("Model & Evaluation"):
                gr.Markdown(
                    f"""
### Test performance
- **Overall MAE:** {metrics['overall_mae']:.4f}
- **Speed MAE:** {metrics['speed_mae_mps'] * 3.6:.2f} km/h
- **Speed RMSE:** {metrics['speed_rmse_mps'] * 3.6:.2f} km/h
- **Test windows:** {metrics['samples']:,}

The horizon curve matters more than a single one-step number: simulation error compounds as the model consumes its own predictions.
                    """
                )
                horizon = pd.DataFrame({"step": np.arange(1, len(metrics["horizon_rmse"]) + 1), "rmse": metrics["horizon_rmse"]})
                fig = go.Figure(go.Scatter(x=horizon.step, y=horizon.rmse, mode="lines+markers"))
                fig.update_layout(template="plotly_dark", title="Rollout RMSE by horizon", xaxis_title="Prediction step", yaxis_title="Normalized RMSE")
                gr.Plot(fig)

            with gr.Tab("Ablation Lab"):
                gr.Markdown("Ablations answer one causal engineering question at a time by removing information while holding the evaluation protocol fixed.")
                gr.Dataframe(ablations[["ablation", "speed_mae_mps", "overall_mae"]], interactive=False)
                fig = go.Figure(go.Bar(x=ablations.ablation, y=ablations.speed_mae_mps * 3.6))
                fig.update_layout(template="plotly_dark", title="One-step speed MAE by feature ablation", yaxis_title="MAE (km/h)")
                gr.Plot(fig)

            with gr.Tab("System Architecture"):
                gr.Markdown(
                    """
```text
FastF1 / OpenF1 / Synthetic / Future F1 25 UDP
                       ↓
              Source-specific adapters
                       ↓
            Canonical telemetry contract
                       ↓
       Validation → alignment → session splits
                       ↓
          Sequence windows + train-only scaling
                       ↓
 Persistence / Linear / GRU / RSSM / SSM models
                       ↓
          Horizon evaluation + physical checks
                       ↓
      Scenario interventions + imagined rollouts
                       ↓
       Registry / artifacts / API / interactive UI
```
                    """
                )
    return app


def launch(run_dir: str | Path, config_path: str | Path = "configs/fast.yaml", share: bool = False) -> None:
    create_app(run_dir, config_path).launch(share=share, css=CUSTOM_CSS)


if __name__ == "__main__":
    launch("artifacts/runs/reference_gru")
