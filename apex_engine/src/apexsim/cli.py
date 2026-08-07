from __future__ import annotations

import json
from pathlib import Path

import typer

from apexsim.config import load_config
from apexsim.data.fastf1_adapter import ingest_fastf1_session
from apexsim.data.openf1_adapter import ingest_openf1_session
from apexsim.data.synthetic import generate_synthetic_sessions
from apexsim.data.validate import validate_canonical_frame
from apexsim.pipeline.runner import run_pipeline

app = typer.Typer(no_args_is_help=True, help="Project APEX F1 world-simulation engine")


@app.command()
def generate(config: Path = Path("configs/fast.yaml"), output: Path = Path("data/raw/synthetic.csv")) -> None:
    cfg = load_config(config)
    frame = generate_synthetic_sessions(cfg, output)
    typer.echo(f"Generated {len(frame):,} canonical telemetry rows at {output}")


@app.command("ingest-fastf1")
def ingest_fastf1(
    year: int,
    event: str,
    session: str,
    driver: str,
    output: Path = Path("data/raw/fastf1.csv"),
    sample_hz: int = 5,
) -> None:
    frame = ingest_fastf1_session(year, event, session, driver, output, sample_hz)
    typer.echo(f"Ingested {len(frame):,} FastF1 rows at {output}")


@app.command("ingest-openf1")
def ingest_openf1(
    session_key: int,
    driver_number: int,
    output: Path = Path("data/raw/openf1.csv"),
    sample_hz: int = 4,
) -> None:
    frame = ingest_openf1_session(session_key, driver_number, output, sample_hz)
    typer.echo(f"Ingested {len(frame):,} OpenF1 rows at {output}")


@app.command()
def validate(path: Path) -> None:
    import pandas as pd

    report = validate_canonical_frame(pd.read_csv(path), strict=False)
    typer.echo(json.dumps(report.to_dict(), indent=2))
    if not report.passed:
        raise typer.Exit(code=1)


@app.command()
def run(
    config: Path = Path("configs/fast.yaml"),
    run_id: str = "reference_gru",
) -> None:
    summary = run_pipeline(load_config(config), run_id)
    typer.echo(json.dumps(summary, indent=2))


@app.command("run-canonical")
def run_canonical(
    input_path: Path,
    config: Path = Path("configs/fast.yaml"),
    run_id: str = "historical_world_model",
) -> None:
    """Run the full pipeline from a validated canonical FastF1/OpenF1 CSV."""
    cfg = load_config(config)
    if not input_path.exists():
        raise typer.BadParameter(f"Canonical input does not exist: {input_path}")
    cfg.data.canonical_input_path = input_path
    summary = run_pipeline(cfg, run_id)
    typer.echo(json.dumps(summary, indent=2))


@app.command("simulate-race")
def simulate_race(
    output: Path = Path("artifacts/complete_sim_demo"),
    seed: int = 42,
    laps: int = 6,
) -> None:
    """Run the complete-simulation vertical slice without an F1 game."""
    from apexsim.examples.complete_sim_demo import build_demo

    simulator = build_demo(seed=seed, total_laps=laps)
    result = simulator.run()
    result.save(output)
    simulator.track.save_csv(output / "track.csv")
    typer.echo(result.standings.to_string(index=False))
    typer.echo(f"Saved race artifacts to {output}")


@app.command("research-catalog")
def research_catalog(output: Path | None = None) -> None:
    """Show the paper-to-code registry or save it as CSV."""
    from apexsim.research.registry import registry_frame

    frame = registry_frame()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        typer.echo(f"Saved {len(frame)} paper records to {output}")
    else:
        typer.echo(frame[["paper_id", "year", "priority", "implementation_stage", "title"]].to_string(index=False))


@app.command("research-demo")
def research_demo(output: Path = Path("artifacts/research_demo")) -> None:
    """Run paper-derived strategy, tyre-energy and degradation demos."""
    from apexsim.examples.research_demo import run_research_demo

    summary = run_research_demo(output)
    typer.echo(json.dumps(summary, indent=2))
    typer.echo(f"Saved research artifacts to {output}")


@app.command()
def ui(
    run_dir: Path = Path("artifacts/runs/reference_gru"),
    config: Path = Path("configs/fast.yaml"),
    share: bool = False,
) -> None:
    from apexsim.ui import launch

    launch(run_dir, config, share=share)


@app.command()
def api(
    artifacts_dir: Path = Path("artifacts/runs"),
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    import uvicorn
    from apexsim.serving import create_api

    uvicorn.run(create_api(artifacts_dir), host=host, port=port)


if __name__ == "__main__":
    app()
