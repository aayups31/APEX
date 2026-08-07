# Protocol — Multi-Agent Strategy and RL–MPC

## Target architecture
A policy proposes discrete pit/compound decisions and a continuous warm start; nonlinear MPC enforces resource constraints and refines energy allocation; a terminal critic captures long-horizon value; opponents are represented through interaction states and self-play.

## Prerequisites
Do not begin until R6 stochastic full-field calibration and a trusted single-agent oracle exist.

## Experiments
- exact two-car small games; - fixed-opponent curricula; - self-play pools; - exploitability and policy cycling; - dirty-air/DRS ablations; - unseen-opponent tests; - RL-only vs MPC-only vs hybrid; - disturbance without retraining.

## Acceptance
Constraint satisfaction, regret to offline oracle, online runtime, recursive-feasibility tests, opponent adaptation and stable performance across policy pools.
