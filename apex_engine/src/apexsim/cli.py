from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

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
    """Retired dense conversion; use frozen archives and build-observed-tables."""
    try:
        ingest_fastf1_session(year, event, session, driver, output, sample_hz)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("ingest-openf1")
def ingest_openf1(
    session_key: int,
    driver_number: int,
    output: Path = Path("data/raw/openf1.csv"),
    sample_hz: int = 4,
) -> None:
    """Retired dense conversion; use frozen archives and build-observed-tables."""
    try:
        ingest_openf1_session(session_key, driver_number, output, sample_hz)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


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
    """Run the pipeline from synthetic canonical CSV; public dense input is retired."""
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


@app.command("public-data-demo")
def public_data_demo(output: Annotated[Path, typer.Option()]) -> None:
    """Verify versioned Parquet tables and event-safe splits using synthetic fixtures."""
    from apexsim.examples.public_data_demo import run_public_data_demo

    typer.echo(json.dumps(run_public_data_demo(output), indent=2))


@app.command("download-fastf1")
def download_fastf1(
    year: Annotated[int, typer.Option()],
    round_number: Annotated[int, typer.Option()],
    session: Annotated[str, typer.Option()],
    output: Annotated[Path, typer.Option()],
) -> None:
    """Freeze a full native FastF1 session and its isolated HTTP/parser cache."""
    from apexsim.data.fastf1_archive import FastF1Query, download_fastf1_session

    result = download_fastf1_session(FastF1Query(year, round_number, session), output)
    typer.echo(json.dumps({"identity": result["identity"], "archive_sha256": result["content_sha256"],
                           "files": len(result["files"]), "path": str(output)}, indent=2))


@app.command("verify-fastf1")
def verify_fastf1(archive: Path) -> None:
    """Check a FastF1 archive without network access or loading cached pickles."""
    from apexsim.data.fastf1_archive import verify_fastf1_archive

    result = verify_fastf1_archive(archive)
    typer.echo(json.dumps({"passed": True, "identity": result["identity"],
                           "archive_sha256": result["content_sha256"]}, indent=2))


@app.command("replay-fastf1")
def replay_fastf1(archive: Path, output: Annotated[Path, typer.Option()]) -> None:
    """Rebuild a trusted archive offline and compare every native table hash."""
    from apexsim.data.fastf1_archive import replay_fastf1_archive

    typer.echo(json.dumps(replay_fastf1_archive(archive, output), indent=2))


@app.command("download-openf1")
def download_openf1(session_key: Annotated[int, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Freeze all OpenF1 endpoint families for one historical session, without filling fields."""
    from apexsim.data.openf1_archive import download_openf1_session

    result = download_openf1_session(session_key, output)
    typer.echo(json.dumps({"identity": result["identity"], "archive_sha256": result["content_sha256"],
                           "requests": len(result["requests"]), "files": len(result["files"]), "path": str(output)}, indent=2))


@app.command("verify-openf1")
def verify_openf1(archive: Path) -> None:
    """Verify OpenF1 response hashes, endpoint coverage and native table reconstruction."""
    from apexsim.data.openf1_archive import verify_openf1_archive

    result = verify_openf1_archive(archive)
    typer.echo(json.dumps({"passed": True, "identity": result["identity"],
                           "archive_sha256": result["content_sha256"]}, indent=2))


@app.command("replay-openf1")
def replay_openf1(archive: Path, output: Annotated[Path, typer.Option()]) -> None:
    """Rebuild native OpenF1 tables from saved responses with networking disabled."""
    from apexsim.data.openf1_archive import replay_openf1_archive

    typer.echo(json.dumps(replay_openf1_archive(archive, output), indent=2))


@app.command("download-jolpica")
def download_jolpica(
    season: Annotated[int, typer.Option()],
    output: Annotated[Path, typer.Option()],
    page_size: int = 100,
) -> None:
    """Freeze a complete Jolpica season calendar with raw paginated responses."""
    from apexsim.data.jolpica import download_jolpica_events

    result = download_jolpica_events(season, output, page_size=page_size)
    typer.echo(json.dumps({"season": season, "events": result["event_count"], "pages": len(result["pages"]),
                           "archive_sha256": result["content_sha256"], "path": str(output)}, indent=2))


@app.command("verify-jolpica")
def verify_jolpica(archive: Path) -> None:
    """Reconstruct and verify a Jolpica event catalog offline from its frozen pages."""
    from apexsim.data.jolpica import verify_jolpica_archive

    result = verify_jolpica_archive(archive)
    typer.echo(json.dumps({"passed": True, "season": result["query"]["season"], "events": result["event_count"],
                           "archive_sha256": result["content_sha256"]}, indent=2))


@app.command("list-events")
def list_events(archive: Path) -> None:
    """List verified season/round/circuit metadata from a local Jolpica archive."""
    from apexsim.data.jolpica import read_jolpica_events

    typer.echo(json.dumps(read_jolpica_events(archive), indent=2))


@app.command("build-observed-tables")
def build_observed_tables(
    fastf1: Annotated[Path, typer.Option()],
    openf1: Annotated[Path, typer.Option()],
    jolpica: Annotated[Path, typer.Option()],
    link: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
) -> None:
    """Map frozen native fields into nullable, source-linked provider tables."""
    from apexsim.data.observed import build_observed_tables as build

    result = build(fastf1, openf1, jolpica, link, output)
    typer.echo(json.dumps({"report_complete": result["report_complete"], "training_ready": result["training_ready"],
                           "event_id": result["identity"]["event_id"],
                           "table_rows": {p: r["table_rows"] for p, r in result["providers"].items()},
                           "report_sha256": result["content_sha256"], "path": str(output)}, indent=2))


@app.command("verify-observed-tables")
def verify_observed_tables(output: Path) -> None:
    """Verify a complete observed run, including lineage and provider bundles."""
    from apexsim.data.observed import verify_observed_tables as verify

    result = verify(output)
    typer.echo(json.dumps({"passed": True, "report_sha256": result["content_sha256"],
                           "training_ready": result["training_ready"]}, indent=2))


@app.command("align-public-data")
def align_public_data(
    fastf1: Annotated[Path, typer.Option()],
    openf1: Annotated[Path, typer.Option()],
    jolpica: Annotated[Path, typer.Option()],
    link: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
    policy: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Audit explicit source links, causal temporal joins, gaps and cross-provider differences."""
    from apexsim.data.alignment import AlignmentPolicy
    from apexsim.data.alignment_report import build_alignment_report

    settings = AlignmentPolicy(**json.loads(policy.read_text(encoding="utf-8"))) if policy else AlignmentPolicy()
    result = build_alignment_report(fastf1, openf1, jolpica, link, output, policy=settings)
    typer.echo(json.dumps({"report_complete": result["report_complete"], "training_ready": result["training_ready"],
                           "event_id": result["identity"]["event_id"], "joins": len(result["joins"]),
                           "report_sha256": result["content_sha256"], "path": str(output)}, indent=2))


@app.command("validate-public-data")
def validate_public_data(dataset: Path) -> None:
    """Verify a frozen five-table dataset, its source snapshots and artifact hashes."""
    from apexsim.data.tables import read_dataset

    _, manifest = read_dataset(dataset)
    typer.echo(json.dumps(manifest["quality"], indent=2))


@app.command("freeze-splits")
def freeze_public_splits(dataset: Path, assignments: Path, output: Path, purpose: str) -> None:
    """Freeze explicit JSON train/val/test session lists against a verified dataset."""
    from apexsim.data.splits import freeze_splits

    payload = json.loads(assignments.read_text(encoding="utf-8"))
    typer.echo(json.dumps(freeze_splits(dataset, payload, output, purpose=purpose), indent=2))


@app.command("research-demo")
def research_demo(output: Path = Path("artifacts/research_demo")) -> None:
    """Run paper-derived strategy, tyre-energy and degradation demos."""
    from apexsim.examples.research_demo import run_research_demo

    summary = run_research_demo(output)
    typer.echo(json.dumps(summary, indent=2))
    typer.echo(f"Saved research artifacts to {output}")


@app.command("strategy-foundation-demo")
def strategy_foundation_demo(output: Annotated[Path, typer.Option()]) -> None:
    """Verify frozen hand calculations and exhaustive tiny strategy optima."""
    from apexsim.examples.strategy_foundation_demo import run_strategy_foundation_demo

    typer.echo(json.dumps(run_strategy_foundation_demo(output), indent=2))


@app.command("smooth-lap-demo")
def smooth_lap_demo(output: Annotated[Path, typer.Option()]) -> None:
    """Verify synthetic smooth lap-map gradients, Hessians and declared bounds."""
    from apexsim.examples.smooth_lap_demo import run_smooth_lap_demo

    typer.echo(json.dumps(run_smooth_lap_demo(output), indent=2))


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
    artifacts_dir: Path = Path("artifacts"),
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    import uvicorn

    from apexsim.serving import create_api

    uvicorn.run(create_api(artifacts_dir), host=host, port=port)


if __name__ == "__main__":
    app()
