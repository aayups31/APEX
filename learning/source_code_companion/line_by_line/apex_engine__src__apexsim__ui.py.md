# `apex_engine/src/apexsim/ui.py`

**Role:** Builds the interactive race-engineering interface.

The UI is an interpretation layer: it must preserve units, loading/error states, uncertainty and the distinction between recorded and imagined futures.

## Line-by-line guide

### Line 1
```python
from __future__ import annotations
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 2
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 3
```python
import json
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python
from pathlib import Path
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 6
```python
import gradio as gr
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python
import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python
import plotly.graph_objects as go
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 10
```python
import torch
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 11
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 12
```python
from apexsim.config import load_config
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 13
```python
from apexsim.contracts import MODEL_INPUT_COLUMNS
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 14
```python
from apexsim.data.features import Standardizer
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 15
```python
from apexsim.data.windows import TelemetryWindowDataset
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 16
```python
from apexsim.pipeline.stages import load_trained_model
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 17
```python
from apexsim.simulation import Scenario, rollout
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 18
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 19
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 20
```python
CUSTOM_CSS = """
```
Creates or updates `CUSTOM_CSS`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python
.gradio-container {max-width: 1500px !important; background: radial-gradient(circle at 15% 5%, #191b22 0%, #090a0e 48%, #050506 100%);}
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 22
```python
#hero {border: 1px solid #30343d; border-radius: 22px; padding: 24px; background: linear-gradient(135deg, rgba(239,35,60,.18), rgba(255,255,255,.025));}
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 23
```python
.metric-card {border: 1px solid #2e323b; border-radius: 16px; padding: 14px; background: rgba(255,255,255,.035);}
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 24
```python
"""
```
Begins or ends documentation describing the module, class or function contract.

### Line 25
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 26
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 27
```python
def _load_bundle(run_dir: Path, config_path: Path):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 28
```python
    config = load_config(config_path)
```
Creates or updates `config`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
    frame = pd.read_csv(run_dir / "canonical_telemetry.csv")
```
Loads persisted tabular evidence; validate schema, units and ordering immediately afterward.

### Line 30
```python
    splits = json.loads((run_dir / "splits.json").read_text())
```
Creates or updates `splits`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 31
```python
    standardizer = Standardizer.from_dict(json.loads((run_dir / "standardizer.json").read_text()))
```
Creates or updates `standardizer`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 32
```python
    model = load_trained_model(config, run_dir)
```
Creates or updates `model`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
    dataset = TelemetryWindowDataset(
```
Creates or updates `dataset`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
        frame,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 35
```python
        splits["test"],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 36
```python
        config.data.sequence_length,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 37
```python
        max(config.data.prediction_horizon, 80),
```
Runs model inference using learned parameters without fitting on the requested examples.

### Line 38
```python
        standardizer,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 39
```python
        max_windows=200,
```
Creates or updates `max_windows`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 40
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 41
```python
    return config, frame, splits, standardizer, model, dataset
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 42
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 43
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 44
```python
def _track_figure(frame: pd.DataFrame, session_id: str) -> go.Figure:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 45
```python
    session = frame[frame.session_id == session_id]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 46
```python
    fig = go.Figure()
```
Creates or updates `fig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 47
```python
    fig.add_trace(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 48
```python
        go.Scatter(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 49
```python
            x=session.x_m,
```
Creates or updates `x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 50
```python
            y=session.y_m,
```
Creates or updates `y`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 51
```python
            mode="lines",
```
Creates or updates `mode`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 52
```python
            line=dict(width=6, color="#ef233c"),
```
Creates or updates `line`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 53
```python
            hovertemplate="x=%{x:.0f}m<br>y=%{y:.0f}m<extra></extra>",
```
Creates or updates `hovertemplate`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 54
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 55
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 56
```python
    fig.update_layout(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 57
```python
        template="plotly_dark",
```
Creates or updates `template`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 58
```python
        title=f"Track trace - {session_id}",
```
Creates or updates `title`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 59
```python
        xaxis_visible=False,
```
Creates or updates `xaxis_visible`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 60
```python
        yaxis_visible=False,
```
Creates or updates `yaxis_visible`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python
        height=430,
```
Creates or updates `height`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 62
```python
        margin=dict(l=15, r=15, t=50, b=15),
```
Creates or updates `margin`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 63
```python
        paper_bgcolor="rgba(0,0,0,0)",
```
Creates or updates `paper_bgcolor`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 64
```python
        plot_bgcolor="rgba(0,0,0,0)",
```
Creates or updates `plot_bgcolor`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 65
```python
        yaxis_scaleanchor="x",
```
Creates or updates `yaxis_scaleanchor`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 67
```python
    return fig
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 68
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 69
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 70
```python
def _telemetry_figure(frame: pd.DataFrame, session_id: str) -> go.Figure:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 71
```python
    session = frame[frame.session_id == session_id].iloc[:1200]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 72
```python
    fig = go.Figure()
```
Creates or updates `fig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 73
```python
    fig.add_trace(go.Scatter(x=session.timestamp_s, y=session.speed_mps * 3.6, name="Speed km/h"))
```
Creates or updates `fig.add_trace(go.Scatter(x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 74
```python
    fig.add_trace(go.Scatter(x=session.timestamp_s, y=session.throttle * 100, name="Throttle %", yaxis="y2"))
```
Creates or updates `fig.add_trace(go.Scatter(x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 75
```python
    fig.add_trace(go.Scatter(x=session.timestamp_s, y=session.brake * 100, name="Brake %", yaxis="y2"))
```
Creates or updates `fig.add_trace(go.Scatter(x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 76
```python
    fig.update_layout(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 77
```python
        template="plotly_dark",
```
Creates or updates `template`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 78
```python
        title="Observed telemetry",
```
Creates or updates `title`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 79
```python
        xaxis_title="Time (s)",
```
Creates or updates `xaxis_title`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 80
```python
        yaxis_title="Speed (km/h)",
```
Creates or updates `yaxis_title`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 81
```python
        yaxis2=dict(title="Pedal (%)", overlaying="y", side="right", range=[0, 100]),
```
Creates or updates `yaxis2`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 82
```python
        height=430,
```
Creates or updates `height`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 83
```python
        legend=dict(orientation="h"),
```
Creates or updates `legend`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 84
```python
        paper_bgcolor="rgba(0,0,0,0)",
```
Creates or updates `paper_bgcolor`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 85
```python
        plot_bgcolor="rgba(255,255,255,.02)",
```
Creates or updates `plot_bgcolor`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 86
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 87
```python
    return fig
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 88
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 89
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 90
```python
def create_app(run_dir: str | Path, config_path: str | Path = "configs/fast.yaml") -> gr.Blocks:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 91
```python
    run_path = Path(run_dir)
```
Creates or updates `run_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 92
```python
    config, frame, splits, standardizer, model, dataset = _load_bundle(run_path, Path(config_path))
```
Creates or updates `config, frame, splits, standardizer, model, dataset`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 93
```python
    metrics = json.loads((run_path / "metrics.json").read_text())
```
Creates or updates `metrics`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 94
```python
    ablations = pd.DataFrame(json.loads((run_path / "ablations.json").read_text()))
```
Creates or updates `ablations`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 95
```python
    sessions = sorted(frame.session_id.unique().tolist())
```
Creates or updates `sessions`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 96
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 97
```python
    def update_session(session_id: str):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 98
```python
        session = frame[frame.session_id == session_id]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 99
```python
        cards = (
```
Creates or updates `cards`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 100
```python
            f"### Session snapshot\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 101
```python
            f"- **Driver:** {session.driver_id.iloc[0]}\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 102
```python
            f"- **Track:** {session.track_id.iloc[0]}\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 103
```python
            f"- **Frames:** {len(session):,}\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 104
```python
            f"- **Peak speed:** {session.speed_mps.max() * 3.6:.1f} km/h\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 105
```python
            f"- **Rain peak:** {session.rainfall.max():.2f}"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 106
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 107
```python
        return _track_figure(frame, session_id), _telemetry_figure(frame, session_id), cards
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 108
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 109
```python
    def simulate(index: int, throttle: float, brake: float, grip: float, rain: float, tyre: float):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 110
```python
        index = int(np.clip(index, 0, len(dataset) - 1))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 111
```python
        item = dataset[index]
```
Creates or updates `item`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 112
```python
        history_z = item["history"].numpy()
```
Creates or updates `history_z`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 113
```python
        future_z = item["future_inputs"].numpy()
```
Creates or updates `future_z`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 114
```python
        history_raw = history_z * standardizer.input_std + standardizer.input_mean
```
Creates or updates `history_raw`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 115
```python
        future_raw = future_z * standardizer.input_std + standardizer.input_mean
```
Creates or updates `future_raw`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 116
```python
        scenario = Scenario(throttle, brake, grip, rain, tyre)
```
Creates or updates `scenario`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 117
```python
        predicted = rollout(model, history_raw, future_raw, standardizer, scenario)
```
Creates or updates `predicted`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 118
```python
        actual = standardizer.inverse_targets(item["future_targets"].numpy())
```
Creates or updates `actual`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 119
```python
        seconds = np.arange(len(predicted)) / config.data.sample_hz
```
Creates or updates `seconds`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 120
```python
        fig = go.Figure()
```
Creates or updates `fig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 121
```python
        fig.add_trace(go.Scatter(x=seconds, y=actual[:, 0] * 3.6, name="Recorded future", line=dict(width=3)))
```
Creates or updates `fig.add_trace(go.Scatter(x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 122
```python
        fig.add_trace(go.Scatter(x=seconds, y=predicted[:, 0] * 3.6, name="Imagined future", line=dict(width=3, dash="dash")))
```
Creates or updates `fig.add_trace(go.Scatter(x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 123
```python
        fig.update_layout(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 124
```python
            template="plotly_dark",
```
Creates or updates `template`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 125
```python
            title="World-model rollout: recorded vs imagined speed",
```
Creates or updates `title`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 126
```python
            xaxis_title="Seconds into future",
```
Creates or updates `xaxis_title`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 127
```python
            yaxis_title="Speed (km/h)",
```
Creates or updates `yaxis_title`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 128
```python
            height=470,
```
Creates or updates `height`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 129
```python
            paper_bgcolor="rgba(0,0,0,0)",
```
Creates or updates `paper_bgcolor`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 130
```python
            plot_bgcolor="rgba(255,255,255,.02)",
```
Creates or updates `plot_bgcolor`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 131
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 132
```python
        delta = float((predicted[-1, 0] - actual[-1, 0]) * 3.6)
```
Creates or updates `delta`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 133
```python
        summary = (
```
Creates or updates `summary`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 134
```python
            f"### Scenario result\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 135
```python
            f"- Rollout horizon: **{len(predicted) / config.data.sample_hz:.1f} s**\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 136
```python
            f"- Final imagined speed: **{predicted[-1, 0] * 3.6:.1f} km/h**\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 137
```python
            f"- Difference from recorded future: **{delta:+.1f} km/h**\n"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 138
```python
            f"- Model: **{config.model.kind.upper()} world model**"
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 139
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 140
```python
        return fig, summary
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 141
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 142
```python
    with gr.Blocks(title="Project APEX") as app:
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 143
```python
        gr.Markdown(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 144
```python
            """
```
Begins or ends documentation describing the module, class or function contract.

### Line 145
```python
<div id="hero">
```
Creates or updates `<div id`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 146
```python
<h1>PROJECT APEX</h1>
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 147
```python
<h3>F1 Telemetry World-Simulation Engine</h3>
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 148
```python
<p>Explore real-shaped telemetry, inspect the learned world model, alter future conditions, and watch the engine imagine what happens next.</p>
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 149
```python
</div>
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 150
```python
            """
```
Begins or ends documentation describing the module, class or function contract.

### Line 151
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 152
```python
        with gr.Tabs():
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 153
```python
            with gr.Tab("Race Engineering Desk"):
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 154
```python
                with gr.Row():
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 155
```python
                    session_select = gr.Dropdown(sessions, value=sessions[0], label="Session")
```
Creates or updates `session_select`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 156
```python
                    session_summary = gr.Markdown()
```
Creates or updates `session_summary`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 157
```python
                with gr.Row():
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 158
```python
                    track_plot = gr.Plot(_track_figure(frame, sessions[0]))
```
Creates or updates `track_plot`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 159
```python
                    telemetry_plot = gr.Plot(_telemetry_figure(frame, sessions[0]))
```
Creates or updates `telemetry_plot`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 160
```python
                session_select.change(update_session, session_select, [track_plot, telemetry_plot, session_summary])
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 161
```python
                initial = frame[frame.session_id == sessions[0]]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 162
```python
                session_summary.value = f"**Frames:** {len(initial):,} | **Peak speed:** {initial.speed_mps.max()*3.6:.1f} km/h"
```
Creates or updates `session_summary.value`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 163
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 164
```python
            with gr.Tab("World Rollout Simulator"):
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 165
```python
                gr.Markdown("Change the future controls and environment. The model rolls forward from a real test-window history.")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 166
```python
                with gr.Row():
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 167
```python
                    with gr.Column(scale=1):
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 168
```python
                        sample_index = gr.Slider(0, max(0, len(dataset) - 1), value=0, step=1, label="Test window")
```
Creates or updates `sample_index`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 169
```python
                        throttle = gr.Slider(0.7, 1.3, value=1.0, step=0.02, label="Throttle multiplier")
```
Creates or updates `throttle`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 170
```python
                        brake = gr.Slider(0.7, 1.3, value=1.0, step=0.02, label="Brake multiplier")
```
Creates or updates `brake`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 171
```python
                        grip = gr.Slider(0.6, 1.2, value=1.0, step=0.02, label="Grip multiplier")
```
Creates or updates `grip`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 172
```python
                        rain = gr.Slider(-0.2, 0.5, value=0.0, step=0.02, label="Rain change")
```
Creates or updates `rain`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 173
```python
                        tyre = gr.Slider(0.5, 2.0, value=1.0, step=0.05, label="Tyre degradation multiplier")
```
Creates or updates `tyre`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 174
```python
                        run_button = gr.Button("IMAGINE FUTURE", variant="primary")
```
Creates or updates `run_button`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 175
```python
                    with gr.Column(scale=2):
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 176
```python
                        rollout_plot = gr.Plot()
```
Creates or updates `rollout_plot`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 177
```python
                        rollout_summary = gr.Markdown()
```
Creates or updates `rollout_summary`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 178
```python
                run_button.click(simulate, [sample_index, throttle, brake, grip, rain, tyre], [rollout_plot, rollout_summary])
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 179
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 180
```python
            with gr.Tab("Model & Evaluation"):
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 181
```python
                gr.Markdown(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 182
```python
                    f"""
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 183
```python
### Test performance
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 184
```python
- **Overall MAE:** {metrics['overall_mae']:.4f}
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 185
```python
- **Speed MAE:** {metrics['speed_mae_mps'] * 3.6:.2f} km/h
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 186
```python
- **Speed RMSE:** {metrics['speed_rmse_mps'] * 3.6:.2f} km/h
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 187
```python
- **Test windows:** {metrics['samples']:,}
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 188
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 189
```python
The horizon curve matters more than a single one-step number: simulation error compounds as the model consumes its own predictions.
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 190
```python
                    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 191
```python
                )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 192
```python
                horizon = pd.DataFrame({"step": np.arange(1, len(metrics["horizon_rmse"]) + 1), "rmse": metrics["horizon_rmse"]})
```
Creates or updates `horizon`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 193
```python
                fig = go.Figure(go.Scatter(x=horizon.step, y=horizon.rmse, mode="lines+markers"))
```
Creates or updates `fig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 194
```python
                fig.update_layout(template="plotly_dark", title="Rollout RMSE by horizon", xaxis_title="Prediction step", yaxis_title="Normalized RMSE")
```
Creates or updates `fig.update_layout(template`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 195
```python
                gr.Plot(fig)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 196
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 197
```python
            with gr.Tab("Ablation Lab"):
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 198
```python
                gr.Markdown("Ablations answer one causal engineering question at a time by removing information while holding the evaluation protocol fixed.")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 199
```python
                gr.Dataframe(ablations[["ablation", "speed_mae_mps", "overall_mae"]], interactive=False)
```
Creates or updates `gr.Dataframe(ablations[["ablation", "speed_mae_mps", "overall_mae"]], interactive`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 200
```python
                fig = go.Figure(go.Bar(x=ablations.ablation, y=ablations.speed_mae_mps * 3.6))
```
Creates or updates `fig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 201
```python
                fig.update_layout(template="plotly_dark", title="One-step speed MAE by feature ablation", yaxis_title="MAE (km/h)")
```
Creates or updates `fig.update_layout(template`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 202
```python
                gr.Plot(fig)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 203
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 204
```python
            with gr.Tab("System Architecture"):
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 205
```python
                gr.Markdown(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 206
```python
                    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 207
```python
```text
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 208
```python
FastF1 / OpenF1 / Synthetic / Future F1 25 UDP
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 209
```python
                       ↓
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 210
```python
              Source-specific adapters
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 211
```python
                       ↓
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 212
```python
            Canonical telemetry contract
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 213
```python
                       ↓
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 214
```python
       Validation → alignment → session splits
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 215
```python
                       ↓
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 216
```python
          Sequence windows + train-only scaling
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 217
```python
                       ↓
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 218
```python
 Persistence / Linear / GRU / RSSM / SSM models
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 219
```python
                       ↓
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 220
```python
          Horizon evaluation + physical checks
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 221
```python
                       ↓
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 222
```python
      Scenario interventions + imagined rollouts
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 223
```python
                       ↓
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 224
```python
       Registry / artifacts / API / interactive UI
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 225
```python
```
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 226
```python
                    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 227
```python
                )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 228
```python
    return app
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 229
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 230
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 231
```python
def launch(run_dir: str | Path, config_path: str | Path = "configs/fast.yaml", share: bool = False) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 232
```python
    create_app(run_dir, config_path).launch(share=share, css=CUSTOM_CSS)
```
Creates or updates `create_app(run_dir, config_path).launch(share`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 233
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 234
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 235
```python
if __name__ == "__main__":
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 236
```python
    launch("artifacts/runs/reference_gru")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
