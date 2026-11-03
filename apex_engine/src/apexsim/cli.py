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


@app.command("freeze-event-corpus")
def freeze_event_corpus_command(evidence_root: Path, membership: Path, output: Path, purpose: str) -> None:
    """Bind a development collection to verified archives and canonical bundles."""
    from apexsim.data.event_corpus import CorpusSession, freeze_event_corpus

    specs = [CorpusSession(**row) for row in json.loads(membership.read_text(encoding="utf-8"))]
    typer.echo(json.dumps(freeze_event_corpus(evidence_root, specs, output, purpose=purpose), indent=2))


@app.command("verify-event-corpus")
def verify_event_corpus_command(manifest: Path, evidence_root: Path) -> None:
    """Verify a relocated development collection without provider requests."""
    from apexsim.data.event_corpus import verify_event_corpus

    typer.echo(json.dumps(verify_event_corpus(manifest, evidence_root), indent=2))


@app.command("freeze-benchmark-reservation")
def freeze_benchmark_reservation_command(calendars: Annotated[list[Path], typer.Option()], development_corpus: Annotated[Path, typer.Option()], evidence_root: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()], purpose: str) -> None:
    """Reserve whole events from calendar metadata without acquiring benchmark telemetry."""
    from apexsim.data.benchmark_reservation import freeze_benchmark_reservation

    typer.echo(json.dumps(freeze_benchmark_reservation(calendars, development_corpus, evidence_root, output, purpose=purpose), indent=2))


@app.command("verify-benchmark-reservation")
def verify_benchmark_reservation_command(reservation: Path) -> None:
    """Verify sealed systematic event membership using metadata only."""
    from apexsim.data.benchmark_reservation import load_benchmark_reservation

    typer.echo(json.dumps(load_benchmark_reservation(reservation), indent=2))


@app.command("build-tyre-dataset")
def build_tyre_dataset_command(archives: Annotated[list[Path], typer.Option()], calendar: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Build source-labelled dry race segments from verified non-benchmark archives."""
    from apexsim.data.tyre_dataset import build_tyre_dataset
    from apexsim.provenance import write_manifest

    if output.exists():
        raise FileExistsError(f"Tyre dataset output already exists: {output}")
    if any(output.resolve().is_relative_to(p.resolve()) for p in [*archives, calendar]):
        raise ValueError("Tyre dataset output must be outside source archives")
    dataset = build_tyre_dataset(archives, calendar)
    write_manifest(output, dataset)
    typer.echo(json.dumps({"content_sha256": dataset["content_sha256"], "segments": len(dataset["segments"]),
                           "events": [s["event_id"] for s in dataset["sources"]]}, indent=2))


@app.command("tyre-degradation-demo")
def tyre_degradation_demo_command(dataset: Path, output: Annotated[Path, typer.Option()], profile: str = "research") -> None:
    """Fit causal tyre pace and conditional Bayesian hierarchy with frozen evaluation."""
    from apexsim.examples.tyre_degradation_demo import run_tyre_degradation_demo

    summary = run_tyre_degradation_demo(dataset, output, profile=profile)
    typer.echo(json.dumps({"profile": summary["profile"], "R021_passed": summary["R021_passed"],
                           "R022_passed": summary["R022_passed"], "content_sha256": summary["content_sha256"]}, indent=2))


@app.command("tyre-degradation-smoke")
def tyre_degradation_smoke_command(output: Annotated[Path, typer.Option()]) -> None:
    """Run a SIMULATED offline study for artifact verification only."""
    from apexsim.examples.tyre_degradation_demo import (
        make_tyre_smoke_dataset,
        run_tyre_degradation_demo,
        verify_tyre_study,
    )
    from apexsim.provenance import write_manifest

    dataset = output.with_name(output.name + "-simulated-input.json")
    if output.exists() or dataset.exists():
        raise FileExistsError("Smoke study requires fresh input and output paths")
    write_manifest(dataset, make_tyre_smoke_dataset())
    run_tyre_degradation_demo(dataset, output, profile="smoke")
    typer.echo(json.dumps(verify_tyre_study(output), indent=2))


@app.command("verify-tyre-study")
def verify_tyre_study_command(output: Path) -> None:
    """Verify saved tyre-study artifacts and posterior arrays without refitting."""
    from apexsim.examples.tyre_degradation_demo import verify_tyre_study

    typer.echo(json.dumps(verify_tyre_study(output), indent=2))


@app.command("research-demo")
def research_demo(output: Path = Path("artifacts/research_demo")) -> None:
    """Run paper-derived strategy, tyre-energy and degradation demos."""
    from apexsim.examples.research_demo import run_research_demo

    summary = run_research_demo(output)
    typer.echo(json.dumps(summary, indent=2))
    typer.echo(f"Saved research artifacts to {output}")


@app.command("build-tyre-energy-dataset")
def build_tyre_energy_dataset_command(archives: Annotated[list[Path], typer.Option()], eligible_dataset: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Build labelled R024 motion/tyre-energy proxies from frozen native race archives."""
    from apexsim.research.tyre_energy_dataset import build_tyre_energy_dataset

    typer.echo(json.dumps(build_tyre_energy_dataset(archives, eligible_dataset, output), indent=2))


@app.command("verify-tyre-energy-dataset")
def verify_tyre_energy_dataset_command(dataset: Path) -> None:
    """Reload proxy field labels, seals and source-row/exclusion accounting."""
    from apexsim.research.tyre_energy_dataset import read_tyre_energy_dataset, validate_samples

    table, manifest = read_tyre_energy_dataset(dataset)
    typer.echo(json.dumps({"manifest_sha256": manifest["content_sha256"], **validate_samples(table)}, indent=2))


@app.command("robust-tyre-demo")
def robust_tyre_demo_command(baseline: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()], profile: str = "research") -> None:
    """Run frozen conditional skew-t versus Gaussian observation comparison."""
    from apexsim.examples.robust_tyre_demo import run_robust_tyre_demo

    summary=run_robust_tyre_demo(baseline,output,profile)
    typer.echo(json.dumps({k:summary[k] for k in ("model_decision","task_closure_eligible","content_sha256")},indent=2))


@app.command("verify-robust-tyre-study")
def verify_robust_tyre_study_command(output: Path) -> None:
    """Recompute CRPS from saved predictive ensembles and verify their seals."""
    from apexsim.examples.robust_tyre_demo import verify_robust_tyre_study

    typer.echo(json.dumps(verify_robust_tyre_study(output),indent=2))


@app.command("tyre-forecast-benchmark")
def tyre_forecast_benchmark_command(dataset: Path, output: Annotated[Path, typer.Option()], profile: str = "research") -> None:
    """Fit all six requested families with train-only preprocessing and matched horizons."""
    from apexsim.examples.tyre_forecast_benchmark import run_forecast_benchmark

    summary=run_forecast_benchmark(dataset,output,profile,progress=typer.echo)
    typer.echo(json.dumps({k:summary[k] for k in ("validation_selected_family","task_closure_eligible","content_sha256")},indent=2))


@app.command("tyre-forecast-smoke")
def tyre_forecast_smoke_command(output: Annotated[Path, typer.Option()]) -> None:
    """SIMULATED execution-only six-family training/checkpoint smoke."""
    from apexsim.examples.tyre_forecast_benchmark import (
        make_forecast_smoke_dataset,
        run_forecast_benchmark,
        verify_forecast_benchmark,
    )

    if output.exists():
        raise FileExistsError("Forecast smoke output must be fresh")
    source=output.with_name(output.name+"-simulated-input")
    make_forecast_smoke_dataset(source)
    run_forecast_benchmark(source,output,"smoke")
    typer.echo(json.dumps(verify_forecast_benchmark(output),indent=2))


@app.command("verify-tyre-forecast-benchmark")
def verify_tyre_forecast_benchmark_command(output: Path) -> None:
    """Reload every saved model and reproduce its held-out forecasts."""
    from apexsim.examples.tyre_forecast_benchmark import verify_forecast_benchmark

    typer.echo(json.dumps(verify_forecast_benchmark(output),indent=2))


@app.command("build-track-generalization-dataset")
def build_track_generalization_dataset_command(archives: Annotated[list[Path], typer.Option()], calendar: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Build the four preregistered R026 races with unchanged proxy equations/priors."""
    from apexsim.examples.track_generalization_demo import build_generalization_dataset

    typer.echo(json.dumps(build_generalization_dataset(archives, calendar, output), indent=2))


@app.command("track-generalization-demo")
def track_generalization_demo_command(dataset: Path, reference: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()], profile: str = "research") -> None:
    """Evaluate frozen R025 checkpoints with separate seen/unseen confidence intervals."""
    from apexsim.examples.track_generalization_demo import run_track_generalization

    summary = run_track_generalization(dataset, reference, output, profile)
    typer.echo(json.dumps({k: summary[k] for k in ("frozen_family_decision", "task_closure_eligible", "content_sha256")}, indent=2))


@app.command("track-generalization-smoke")
def track_generalization_smoke_command(reference: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """SIMULATED inference-only smoke using an existing six-family smoke reference."""
    from apexsim.examples.track_generalization_demo import (
        make_generalization_smoke_dataset,
        run_track_generalization,
        verify_track_generalization,
    )

    if output.exists():
        raise FileExistsError("Generalization smoke output must be fresh")
    source = output.with_name(output.name+"-simulated-input")
    make_generalization_smoke_dataset(reference, source)
    run_track_generalization(source, reference, output, "smoke")
    typer.echo(json.dumps(verify_track_generalization(output), indent=2))


@app.command("verify-track-generalization")
def verify_track_generalization_command(output: Path) -> None:
    """Replay all frozen inference weights, quantiles and clustered scores."""
    from apexsim.examples.track_generalization_demo import verify_track_generalization

    typer.echo(json.dumps(verify_track_generalization(output), indent=2))


@app.command("track-reconstruction-v2")
def track_reconstruction_v2_command(archives: Annotated[list[Path], typer.Option()], mask_2024: Annotated[Path, typer.Option()], mask_2023: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()], stage: Annotated[str, typer.Option()] = "research", observed_boundaries: Annotated[bool, typer.Option()] = False, coherent_curvature: Annotated[bool, typer.Option()] = False) -> None:
    """Reconstruct native observed support; development stage never opens geometry test laps."""
    from apexsim.examples.track_reconstruction_v2 import run_track_reconstruction_v2

    summary = run_track_reconstruction_v2(archives, mask_2024, mask_2023, output, stage=stage, observed_boundaries=observed_boundaries, coherent_curvature=coherent_curvature)
    typer.echo(json.dumps({k: summary[k] for k in ("decision", "task_closure_eligible", "content_sha256")}, indent=2))


@app.command("verify-track-reconstruction-v2")
def verify_track_reconstruction_v2_command(output: Path) -> None:
    """Refit all observed inputs, missing-data support, projections, sensitivity and decisions."""
    from apexsim.examples.track_reconstruction_v2 import verify_track_reconstruction_v2

    typer.echo(json.dumps(verify_track_reconstruction_v2(output), indent=2))


@app.command("track-reconstruction-v2-smoke")
def track_reconstruction_v2_smoke_command(output: Annotated[Path, typer.Option()], observed_boundaries: Annotated[bool, typer.Option()] = False, coherent_curvature: Annotated[bool, typer.Option()] = False) -> None:
    """SIMULATED complementary gaps and native-support replay; cannot close public R029."""
    from apexsim.examples.track_reconstruction_v2 import (
        run_track_reconstruction_v2_smoke,
        verify_track_reconstruction_v2,
    )

    run_track_reconstruction_v2_smoke(output, observed_boundaries=observed_boundaries, coherent_curvature=coherent_curvature)
    typer.echo(json.dumps(verify_track_reconstruction_v2(output), indent=2))


@app.command("track-reconstruction-demo")
def track_reconstruction_demo_command(archives: Annotated[list[Path], typer.Option()], mask_2024: Annotated[Path, typer.Option()], mask_2023: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Reconstruct preregistered public reference traces with held-out geometry gates."""
    from apexsim.examples.track_reconstruction_demo import run_track_reconstruction

    summary = run_track_reconstruction(archives, mask_2024, mask_2023, output)
    typer.echo(json.dumps({k: summary[k] for k in ("decision", "task_closure_eligible", "content_sha256")}, indent=2))


@app.command("track-reconstruction-source-audit")
def track_reconstruction_source_audit_command(archives: Annotated[list[Path], typer.Option()], mask_2024: Annotated[Path, typer.Option()], mask_2023: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Persist all frozen pre-fit source checks, including rejected native evidence."""
    from apexsim.examples.track_reconstruction_source_audit import run_source_audit

    summary = run_source_audit(archives, mask_2024, mask_2023, output)
    typer.echo(json.dumps({k: summary[k] for k in ("decision", "supported_laps", "selected_laps", "task_closure_eligible", "content_sha256")}, indent=2))


@app.command("verify-track-reconstruction-source-audit")
def verify_track_reconstruction_source_audit_command(output: Path) -> None:
    """Replay every pre-fit decision from saved native snapshots without source caches."""
    from apexsim.examples.track_reconstruction_source_audit import verify_source_audit

    typer.echo(json.dumps(verify_source_audit(output), indent=2))


@app.command("track-reconstruction-smoke")
def track_reconstruction_smoke_command(output: Annotated[Path, typer.Option()]) -> None:
    """SIMULATED circle/ellipse execution; cannot close public reconstruction research."""
    from apexsim.examples.track_reconstruction_demo import (
        run_track_reconstruction_smoke,
        verify_track_reconstruction,
    )

    run_track_reconstruction_smoke(output)
    typer.echo(json.dumps(verify_track_reconstruction(output), indent=2))


@app.command("verify-track-reconstruction")
def verify_track_reconstruction_command(output: Path) -> None:
    """Refit stored training laps and replay geometry, diagnostics and frozen decisions."""
    from apexsim.examples.track_reconstruction_demo import verify_track_reconstruction

    typer.echo(json.dumps(verify_track_reconstruction(output), indent=2))


@app.command("fit-longitudinal-calibration")
def fit_longitudinal_calibration_command(dataset: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Fit training-only effective coefficients and freeze validation selection."""
    from apexsim.examples.longitudinal_study import fit_longitudinal_study

    typer.echo(json.dumps(fit_longitudinal_study(dataset, output), indent=2))


@app.command("verify-longitudinal-development")
def verify_longitudinal_development_command(output: Path) -> None:
    """Refit training and reproduce the frozen validation choice without test scoring."""
    from apexsim.examples.longitudinal_study import verify_longitudinal_development

    typer.echo(json.dumps(verify_longitudinal_development(output), indent=2))


@app.command("audit-longitudinal-calibration")
def audit_longitudinal_calibration_command(output: Path) -> None:
    """Independently check bounded-fit optimality, DOP853 paths and section scores."""
    from apexsim.research.longitudinal_audit import independent_longitudinal_audit

    typer.echo(json.dumps(independent_longitudinal_audit(output), indent=2))


@app.command("evaluate-longitudinal-calibration")
def evaluate_longitudinal_calibration_command(development: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Evaluate frozen longitudinal parameters on untouched section outcomes."""
    from apexsim.examples.longitudinal_study import evaluate_longitudinal_study

    typer.echo(json.dumps(evaluate_longitudinal_study(development, output), indent=2))


@app.command("verify-longitudinal-calibration")
def verify_longitudinal_calibration_command(output: Path) -> None:
    """Refit training and replay validation, held-out predictions and gate decisions."""
    from apexsim.examples.longitudinal_study import verify_longitudinal_study

    typer.echo(json.dumps(verify_longitudinal_study(output), indent=2))


@app.command("prepare-recorded-replay")
def prepare_recorded_replay_command(longitudinal: Annotated[Path, typer.Option()], archives: Annotated[list[Path], typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """R033 source-sealed causal controls and observed-state alignment on frozen laps."""
    from apexsim.examples.recorded_replay import prepare_recorded_replay

    result = prepare_recorded_replay(longitudinal, archives, output)
    typer.echo(json.dumps(result, indent=2))
    if not result["task_closure_eligible"]:
        raise typer.Exit(code=1)


@app.command("recorded-replay-smoke")
def recorded_replay_smoke_command(output: Annotated[Path, typer.Option()]) -> None:
    """SIMULATED async source/control fixture; cannot close public R033."""
    from apexsim.examples.recorded_replay import make_recorded_smoke

    typer.echo(json.dumps(make_recorded_smoke(output), indent=2))


@app.command("verify-recorded-replay")
def verify_recorded_replay_command(output: Path) -> None:
    """Regenerate every native association, unknown field, input and coverage gate."""
    from apexsim.examples.recorded_replay import verify_recorded_replay

    typer.echo(json.dumps(verify_recorded_replay(output), indent=2))


@app.command("audit-recorded-replay")
def audit_recorded_replay_command(output: Path) -> None:
    """Independently check native rows, causal position joins and recorded controls."""
    from apexsim.examples.recorded_replay import audit_recorded_replay

    typer.echo(json.dumps(audit_recorded_replay(output), indent=2))


@app.command("aero-load-study")
def aero_load_study_command(output: Annotated[Path, typer.Option()]) -> None:
    """R032 synthetic aero/load-transfer sensitivity and identifiability evidence."""
    from apexsim.examples.aero_study import run_aero_study

    result = run_aero_study(output)
    typer.echo(json.dumps(result, indent=2))
    if not result["task_closure_eligible"]:
        raise typer.Exit(code=1)


@app.command("verify-aero-load-study")
def verify_aero_load_study_command(output: Path) -> None:
    """Regenerate all coupled-load equations, sensitivity and synthetic trajectories."""
    from apexsim.examples.aero_study import verify_aero_study

    typer.echo(json.dumps(verify_aero_study(output), indent=2))


@app.command("audit-aero-load-study")
def audit_aero_load_study_command(output: Path) -> None:
    """Independently integrate coupled-load dynamics with bisection and DOP853."""
    from apexsim.examples.aero_study import audit_aero_study

    typer.echo(json.dumps(audit_aero_study(output), indent=2))


@app.command("bicycle-dynamics-study")
def bicycle_dynamics_study_command(output: Annotated[Path, typer.Option()]) -> None:
    """Run R031 synthetic force/stability acceptance; no public cornering calibration."""
    from apexsim.examples.bicycle_study import run_bicycle_study

    summary = run_bicycle_study(output)
    typer.echo(json.dumps(summary, indent=2))
    if not summary["task_closure_eligible"]:
        raise typer.Exit(code=1)


@app.command("verify-bicycle-dynamics")
def verify_bicycle_dynamics_command(output: Path) -> None:
    """Regenerate all synthetic trajectories, force gates and stability evidence."""
    from apexsim.examples.bicycle_study import verify_bicycle_study

    typer.echo(json.dumps(verify_bicycle_study(output), indent=2))


@app.command("audit-bicycle-dynamics")
def audit_bicycle_dynamics_command(output: Path) -> None:
    """Rebuild scalar forces and independently integrate saved R031 trajectories."""
    from apexsim.examples.bicycle_study import audit_bicycle_study

    typer.echo(json.dumps(audit_bicycle_study(output), indent=2))


@app.command("longitudinal-calibration-smoke")
def longitudinal_calibration_smoke_command(output: Annotated[Path, typer.Option()]) -> None:
    """SIMULATED equation/replay execution; cannot close public R030."""
    from apexsim.examples.longitudinal_study import (
        evaluate_longitudinal_study,
        fit_longitudinal_study,
        make_longitudinal_smoke_dataset,
        verify_longitudinal_study,
    )

    if output.exists():
        raise FileExistsError("R030 smoke output must be fresh")
    dataset = make_longitudinal_smoke_dataset(output.with_name(output.name+"-dataset"))
    development = output.with_name(output.name+"-development")
    fit_longitudinal_study(dataset, development)
    evaluate_longitudinal_study(development, output)
    typer.echo(json.dumps(verify_longitudinal_study(output), indent=2))


@app.command("prepare-longitudinal-dataset")
def prepare_longitudinal_dataset_command(geometry: Annotated[Path, typer.Option()], archives: Annotated[list[Path], typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Freeze source-bound R030 sections before any coefficient fitting."""
    from apexsim.examples.longitudinal_dataset import prepare_longitudinal_dataset

    typer.echo(json.dumps(prepare_longitudinal_dataset(geometry, archives, output), indent=2))


@app.command("verify-longitudinal-dataset")
def verify_longitudinal_dataset_command(output: Path) -> None:
    """Regenerate native controls, section membership and rejected-row accounting."""
    from apexsim.examples.longitudinal_dataset import verify_longitudinal_dataset

    typer.echo(json.dumps(verify_longitudinal_dataset(output), indent=2))


@app.command("freeze-forecast-explanation-cohort")
def freeze_forecast_explanation_cohort_command(reference: Annotated[Path, typer.Option()], evaluation: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()], profile: str = "research") -> None:
    """Freeze source-key origins/donors without reading prediction or target payloads."""
    from apexsim.examples.forecast_explanation_study import freeze_cohort

    typer.echo(json.dumps(freeze_cohort(reference, evaluation, output, profile), indent=2))


@app.command("forecast-explanation-study")
def forecast_explanation_study_command(reference: Annotated[Path, typer.Option()], evaluation: Annotated[Path, typer.Option()], cohort: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Evaluate faithful diagnostics and constraint-feasible scenarios using frozen weights."""
    from apexsim.examples.forecast_explanation_study import run_explanation_study

    summary = run_explanation_study(reference, evaluation, cohort, output, lambda message: typer.echo(message, err=True))
    typer.echo(json.dumps(summary, indent=2))


@app.command("verify-forecast-explanation-study")
def verify_forecast_explanation_study_command(output: Path) -> None:
    """Reload checkpoints and replay every explanation, constraint and candidate choice."""
    from apexsim.examples.forecast_explanation_study import verify_explanation_study

    typer.echo(json.dumps(verify_explanation_study(output, lambda message: typer.echo(message, err=True)), indent=2))


@app.command("audit-forecast-explanation-study")
def audit_forecast_explanation_study_command(output: Path) -> None:
    """Independently audit scenario equations, minimality and selected checkpoint forecasts."""
    from apexsim.research.forecast_explanation_audit import independent_explanation_audit

    typer.echo(json.dumps(independent_explanation_audit(output), indent=2))


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


@app.command("strategy-solver-demo")
def strategy_solver_demo(output: Annotated[Path, typer.Option()]) -> None:
    """Verify a bounded local strategy solver against matched tiny continuous optima."""
    from apexsim.examples.strategy_solver_demo import run_strategy_solver_demo

    typer.echo(json.dumps(run_strategy_solver_demo(output), indent=2))


@app.command("sac-strategy-demo")
def sac_strategy_demo(output: Annotated[Path, typer.Option()], profile: str = "research") -> None:
    """Train frozen synthetic hybrid SAC seeds and report matched in-task regret."""
    from apexsim.examples.sac_strategy_demo import run_sac_strategy_demo

    def progress(row: dict) -> None:
        typer.echo(f"seed={row['seed']} step={row['step']} updates={row['updates']} episodes={row['episodes']}", err=True)

    typer.echo(json.dumps(run_sac_strategy_demo(output, profile, progress), indent=2))


@app.command("strategy-scenarios-demo")
def strategy_scenarios_demo(policy_run: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Evaluate frozen SAC checkpoints under causal synthetic wear disturbances."""
    from apexsim.examples.strategy_scenarios_demo import run_strategy_scenarios_demo

    typer.echo(json.dumps(run_strategy_scenarios_demo(policy_run, output), indent=2))


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


@app.command("open-loop-error-study")
def open_loop_error_study_command(recorded: Annotated[Path, typer.Option()], development: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Report frozen matched section errors and explicit unavailable lap/stint scopes."""
    from apexsim.examples.open_loop_study import run_open_loop_study

    typer.echo(json.dumps(run_open_loop_study(recorded, development, output), indent=2))


@app.command("verify-open-loop-errors")
def verify_open_loop_errors_command(output: Path) -> None:
    from apexsim.examples.open_loop_study import verify_open_loop_study

    typer.echo(json.dumps(verify_open_loop_study(output), indent=2))


@app.command("audit-open-loop-errors")
def audit_open_loop_errors_command(output: Path) -> None:
    from apexsim.research.open_loop_audit import audit_open_loop_study

    typer.echo(json.dumps(audit_open_loop_study(output), indent=2))


@app.command("freeze-driver-calibration")
def freeze_driver_calibration_command(open_loop: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Freeze transparent pace selection on train/validation labels before test laps."""
    from apexsim.examples.driver_study import freeze_driver_calibration

    typer.echo(json.dumps(freeze_driver_calibration(open_loop, output), indent=2))


@app.command("verify-driver-calibration")
def verify_driver_calibration_command(output: Path) -> None:
    from apexsim.examples.driver_study import verify_driver_calibration

    typer.echo(json.dumps(verify_driver_calibration(output), indent=2))


@app.command("transparent-driver-study")
def transparent_driver_study_command(calibration: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Run every frozen conditional lap case, baseline, refinement and independent audit."""
    from apexsim.examples.driver_study import run_driver_study

    typer.echo(json.dumps(run_driver_study(calibration, output, lambda m: typer.echo(m, err=True)), indent=2))


@app.command("verify-transparent-driver")
def verify_transparent_driver_command(output: Path) -> None:
    from apexsim.examples.driver_study import verify_driver_study

    typer.echo(json.dumps(verify_driver_study(output, lambda m: typer.echo(m, err=True)), indent=2))


@app.command("prepare-imitation-dataset")
def prepare_imitation_dataset_command(teacher: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Freeze accepted R035 maps, pace and event-safe source conditions for R036."""
    from apexsim.examples.imitation_study import prepare_imitation_dataset

    typer.echo(json.dumps(prepare_imitation_dataset(teacher, output), indent=2))


@app.command("fit-imitation-driver")
def fit_imitation_driver_command(dataset: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Select a simulated expert and train/aggregate on training events only."""
    from apexsim.examples.imitation_study import fit_imitation_study

    typer.echo(json.dumps(fit_imitation_study(dataset, output, lambda m: typer.echo(m, err=True)), indent=2))


@app.command("verify-imitation-development")
def verify_imitation_development_command(output: Path, receipt: Annotated[Path | None, typer.Option()] = None) -> None:
    """Replay every development trajectory and independently refit all checkpoints."""
    from apexsim.examples.imitation_study import verify_imitation_development
    from apexsim.provenance import write_manifest

    result = verify_imitation_development(output, progress=lambda m: typer.echo(m, err=True))
    if receipt is not None:
        write_manifest(receipt, result)
    typer.echo(json.dumps(result, indent=2))


@app.command("evaluate-imitation-driver")
def evaluate_imitation_driver_command(development: Annotated[Path, typer.Option()], verification: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Run the frozen complete matched R036 test catalog, refinements and audit."""
    from apexsim.examples.imitation_study import run_imitation_evaluation

    typer.echo(json.dumps(run_imitation_evaluation(development, verification, output, lambda m: typer.echo(m, err=True)), indent=2))


@app.command("verify-imitation-driver")
def verify_imitation_driver_command(output: Path, receipt: Annotated[Path | None, typer.Option()] = None) -> None:
    """Regenerate every final comparison and independent held-action lap replay."""
    from apexsim.examples.imitation_study import verify_imitation_evaluation
    from apexsim.provenance import write_manifest

    result = verify_imitation_evaluation(output, lambda m: typer.echo(m, err=True))
    if receipt is not None:
        write_manifest(receipt, result)
    typer.echo(json.dumps(result, indent=2))


@app.command("imitation-driver-smoke")
def imitation_driver_smoke_command(output: Annotated[Path, typer.Option()]) -> None:
    """SIMULATED execution of all R036 stages; cannot close public R036."""
    from apexsim.examples.imitation_study import (
        fit_imitation_study,
        make_imitation_smoke_dataset,
        run_imitation_evaluation,
        verify_imitation_development,
        verify_imitation_evaluation,
    )
    from apexsim.provenance import write_manifest

    if output.exists():
        raise FileExistsError("R036 smoke output must be fresh")
    dataset, development = output.with_name(output.name+"-dataset"), output.with_name(output.name+"-development")
    receipt = output.with_name(output.name+"-development-verification.json")
    def progress(message: str) -> None:
        typer.echo(message, err=True)

    make_imitation_smoke_dataset(dataset)
    fit_imitation_study(dataset, development, progress)
    write_manifest(receipt, verify_imitation_development(development, progress=progress))
    run_imitation_evaluation(development, receipt, output, progress)
    typer.echo(json.dumps(verify_imitation_evaluation(output, progress), indent=2))


@app.command("prepare-recovery-benchmark")
def prepare_recovery_command(reference: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Freeze accepted R036 inputs and code before multi-lap evaluation."""
    from apexsim.examples.recovery_study import prepare_recovery

    typer.echo(json.dumps(prepare_recovery(reference, output), indent=2))


@app.command("run-recovery-benchmark")
def run_recovery_command(inputs: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Continuous five-lap public or three-lap explicitly simulated study."""
    from apexsim.examples.recovery_study import run_recovery

    typer.echo(json.dumps(run_recovery(inputs, output, lambda message: typer.echo(message, err=True)), indent=2))


@app.command("verify-recovery-benchmark")
def verify_recovery_command(output: Path, receipt: Annotated[Path | None, typer.Option()] = None) -> None:
    """Regenerate all continuous paths and repeat independent numerical audits."""
    from apexsim.examples.recovery_study import verify_recovery
    from apexsim.provenance import write_manifest

    result = verify_recovery(output, lambda message: typer.echo(message, err=True))
    if receipt is not None:
        write_manifest(receipt, result)
    typer.echo(json.dumps(result, indent=2))


@app.command("fit-support-detector")
def fit_support_command(recovery: Annotated[Path, typer.Option()], verification: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Fit train/validation-only support envelope after verified R037 recovery."""
    from apexsim.examples.support_study import fit_support

    typer.echo(json.dumps(fit_support(recovery, verification, output), indent=2))


@app.command("verify-support-detector")
def verify_support_detector_command(output: Path) -> None:
    """Rebuild detector ranges/cutoff and audit independent quantiles before test."""
    from apexsim.examples.support_study import load_support_detector

    summary, model = load_support_detector(output)
    typer.echo(json.dumps({"verified": True, "summary_sha256": summary["content_sha256"], "model": model}, indent=2))


@app.command("run-support-benchmark")
def run_support_command(detector: Annotated[Path, typer.Option()], output: Annotated[Path, typer.Option()]) -> None:
    """Matched multi-lap guarded/unguarded/transparent fault and abstention study."""
    from apexsim.examples.support_study import run_support

    typer.echo(json.dumps(run_support(detector, output, lambda message: typer.echo(message, err=True)), indent=2))


@app.command("verify-support-benchmark")
def verify_support_command(output: Path, receipt: Annotated[Path | None, typer.Option()] = None) -> None:
    """Regenerate all fallback paths and recheck every detector and numerical gate."""
    from apexsim.examples.support_study import verify_support
    from apexsim.provenance import write_manifest

    result = verify_support(output, lambda message: typer.echo(message, err=True))
    if receipt is not None:
        write_manifest(receipt, result)
    typer.echo(json.dumps(result, indent=2))


@app.command("run-tyre-thermal-study")
def run_tyre_thermal_study_command(
    recovery: Annotated[Path, typer.Option()],
    verification: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
) -> None:
    """Replay the R039 tread and carcass heat balance on accepted R037 trajectories."""
    from apexsim.examples.thermal_study import run_thermal_study

    typer.echo(json.dumps(run_thermal_study(recovery, verification, output), indent=2))


if __name__ == "__main__":
    app()
