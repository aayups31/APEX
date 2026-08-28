"""Machine-readable research registry used by docs, CLI and validation gates."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    year: int
    domain: str
    priority: str
    implementation_stage: str
    apex_module: str
    validation_target: str
    source_url: str
    local_pdf: str = ""
    notes: str = ""


def default_registry() -> tuple[PaperRecord, ...]:
    return (
        PaperRecord("FIENI_2025", "Towards Learning-Based Formula 1 Race Strategies", 2025, "joint strategy/energy/tyres", "P0", "RUNNABLE_SURROGATE", "apexsim.research.fienia_strategy", "MINLP/RL regret and disturbance response", "https://arxiv.org/abs/2512.21570", "research/user_provided_papers/learning-based-f1-strategies.pdf"),
        PaperRecord("TODD_2025", "Explainable Time Series Prediction of Tyre Energy in Formula One Race Strategy", 2025, "tyre energy forecasting/XAI", "P0", "RUNNABLE_PROXY_PROTOCOL", "apexsim.research.tyre_energy; apexsim.research.tyre_forecasting", "seen/unseen-track RMSE, SMAPE, explanation faithfulness", "https://doi.org/10.1145/3672608.3707765", "research/user_provided_papers/tyre-energy-in-F1.pdf"),
        PaperRecord("HEILMEIER_2018", "A Race Simulation for Strategy Decisions in Circuit Motorsports", 2018, "race simulation", "P0", "ENGINE_CROSSWALK", "apexsim.sim_core.race", "lap/position replay and runtime", "https://doi.org/10.1109/ITSC.2018.8570012"),
        PaperRecord("HEILMEIER_2020_MC", "Application of Monte Carlo Methods to Consider Probabilistic Effects in a Race Simulation for Circuit Motorsport", 2020, "stochastic race simulation", "P0", "ENGINE_CROSSWALK", "apexsim.sim_core.strategy; apexsim.sim_core.weather", "distribution calibration and strategy rank stability", "https://doi.org/10.3390/app10124229"),
        PaperRecord("HEILMEIER_2020_VSE", "Virtual Strategy Engineer", 2020, "strategy imitation", "P1", "PROTOCOL_DEFINED", "apexsim.research.unified_race", "pit/no-pit and compound decision calibration", "https://doi.org/10.3390/app10217805"),
        PaperRecord("DUHR_2023", "Minimum-Race-Time Energy Allocation Strategies for the Hybrid-Electric Formula 1 Power Unit", 2023, "hybrid energy optimization", "P0", "PROTOCOL_DEFINED", "apexsim.research.fienia_strategy", "energy terminal constraints and shrinking-horizon response", "https://doi.org/10.1109/TVT.2023.3237388"),
        PaperRecord("HEINE_2023", "On the Optimization of Pit Stop Strategies via Dynamic Programming", 2023, "dynamic programming", "P1", "PLANNED", "apexsim.sim_core.strategy", "recover exact small-instance optimum", "https://doi.org/10.1007/s10100-021-00768-5"),
        PaperRecord("AGUAD_2024", "Optimizing Pit Stop Strategies in Formula 1 with Dynamic Programming and Game Theory", 2024, "multi-agent strategy", "P1", "PLANNED", "apexsim.sim_core.race; apexsim.sim_core.strategy", "two-car equilibrium and risk-taking objectives", "https://doi.org/10.1016/j.ejor.2024.06.026"),
        PaperRecord("THOMAS_2025", "Explainable Reinforcement Learning for Formula One Race Strategy", 2025, "race-strategy RL/XAI", "P0", "INTERFACE_IMPLEMENTED", "apexsim.research.unified_race", "finishing-position baseline, seen/unseen tracks, XAI fidelity", "https://doi.org/10.1145/3672608.3707766"),
        PaperRecord("FIENI_2026_MULTI", "Learning-based Multi-agent Race Strategies in Formula 1", 2026, "multi-agent energy/tyres/aero", "P0", "PLANNED", "apexsim.sim_core.race; apexsim.research.fienia_strategy", "self-play robustness and opponent response", "https://arxiv.org/abs/2602.23056"),
        PaperRecord("WUTHRICH_2026_RLMPC", "Bridging RL and MPC for Mixed-Integer Optimal Control with Application to Formula 1 Race Strategies", 2026, "hybrid RL/MPC", "P0", "PROTOCOL_DEFINED", "apexsim.research.fienia_strategy; apexsim.sim_core.hybrid", "near-optimality, recursive feasibility and disturbance adaptation", "https://arxiv.org/abs/2604.00826"),
        PaperRecord("CAPPELLO_2025", "A State-Space Approach to Modeling Tire Degradation in Formula 1 Racing", 2025, "probabilistic tyre degradation", "P0", "RUNNABLE_STARTER", "apexsim.research.state_space_tyre", "held-out predictive density and reset behavior", "https://arxiv.org/abs/2512.00640"),
        PaperRecord("PERANTONI_2014", "Optimal Control for a Formula One Car with Variable Parameters", 2014, "minimum-lap-time vehicle dynamics", "P0", "ENGINE_CROSSWALK", "apexsim.sim_core.track; apexsim.sim_core.vehicle", "track closure, line/control/set-up optimization", "https://doi.org/10.1080/00423114.2014.889315"),
        PaperRecord("TREMLETT_2016", "Optimal Tyre Usage for a Formula One Car", 2016, "thermodynamic tyre optimal control", "P0", "PROTOCOL_DEFINED", "apexsim.sim_core.tyres; apexsim.research.tyre_energy", "temperature/wear/control sensitivity", "https://doi.org/10.1080/00423114.2016.1213861"),
        PaperRecord("WEST_2020", "Optimal Tyre Management of a Formula One Car", 2020, "multi-lap tyre thermal/wear", "P0", "PROTOCOL_DEFINED", "apexsim.sim_core.tyres", "temperature window, wear acceleration and pit crossover", "https://doi.org/10.1016/j.ifacol.2020.12.1446"),
        PaperRecord("PLANET_2019", "Learning Latent Dynamics for Planning from Pixels", 2019, "latent world models/planning", "P1", "EXISTING_RSSM_CROSSWALK", "apexsim.models.rssm", "multi-step latent overshooting and CEM planning", "https://arxiv.org/abs/1811.04551"),
        PaperRecord("DREAMERV3_2023", "Mastering Diverse Domains through World Models", 2023, "world models/imagination", "P1", "EXISTING_RSSM_CROSSWALK", "apexsim.models.rssm", "stable imagination and actor-critic baselines", "https://arxiv.org/abs/2301.04104"),
        PaperRecord("TDMPC2_2024", "TD-MPC2: Scalable, Robust World Models for Continuous Control", 2024, "latent MPC", "P1", "PLANNED", "apexsim.sim_core.hybrid; apexsim.models", "decoder-free latent planning and robustness", "https://arxiv.org/abs/2310.16828"),
        PaperRecord("ISODREAM_2022", "Iso-Dream: Isolating and Leveraging Noncontrollable Visual Dynamics in World Models", 2022, "factorized world models", "P2", "PLANNED", "apexsim.models.rssm; apexsim.sim_core.race", "separate ego-controllable dynamics from opponents/weather/flags", "https://openreview.net/forum?id=6LBfSduVg0N"),
        PaperRecord("BOTTINGER_2023", "Mastering Nordschleife — A Comprehensive Race Simulation for AI Strategy Decision-Making in Motorsports", 2023, "endurance simulation/RL", "P1", "PROTOCOL_DEFINED", "apexsim.research.unified_race; apexsim.sim_core.race", "Gym-style environment, reward/observation ablations and historical calibration", "https://arxiv.org/abs/2306.16088"),
        PaperRecord("PACEJKA_1989", "A New Tire Model with an Application in Vehicle Dynamics Studies", 1989, "tyre force model", "P2", "REFERENCE_ONLY", "apexsim.sim_core.tyres; apexsim.sim_core.vehicle", "force-slip curve sanity and friction-envelope calibration", "https://doi.org/10.4271/890087"),
        PaperRecord("FARRONI_2017", "Physical Modelling of Tire Wear for the Analysis of Thermal and Frictional Effects on Vehicle Performance", 2017, "multiphysical tyre wear", "P1", "PROTOCOL_DEFINED", "apexsim.sim_core.tyres; apexsim.research.tyre_energy", "thermal/sliding-energy sensitivity and wear monotonicity", "https://doi.org/10.1177/1464420716666107"),
    )


def registry_frame(records: Iterable[PaperRecord] | None = None) -> pd.DataFrame:
    return pd.DataFrame([asdict(record) for record in (records or default_registry())])


def validate_local_papers(root: Path, records: Iterable[PaperRecord] | None = None) -> list[str]:
    missing = []
    for record in records or default_registry():
        if record.local_pdf and not (root / record.local_pdf).exists():
            missing.append(record.local_pdf)
    return missing
