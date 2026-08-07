# Future Game-Telemetry Validation Plan

Buying the game will add a controlled, high-frequency simulator domain. It will not turn game telemetry into real Formula 1 ground truth. The purpose is to stress equations, interfaces and causal responses that public broadcast data cannot expose directly.

## Adapter contract

A future UDP adapter must emit the columns defined in:

```text
apexsim.research.game_validation.GAME_REQUIRED_COLUMNS
```

The adapter is isolated from all paper implementations. Game packets are converted once into the evidence contract; research models and the APEX engine consume the same aligned table.

## Pre-registered test families

### G1 — vehicle dynamics

Use fixed car/setup/track/weather and scripted controls. Test:

- throttle step response;
- braking distance across speeds;
- corner speed versus steering/curvature;
- mass/fuel sensitivity;
- DRS drag effect;
- track closure and coordinate alignment.

Compare current APEX, minimum-lap-time equations and game traces with matched controls.

### G2 — tyre energy, temperature and degradation

Run repeated laps with controlled push/conserve, steering and brake profiles. Test:

- left/right energy asymmetry by corner direction;
- energy/temperature response at braking, apex and traction zones;
- degradation versus accumulated proxy energy;
- compound crossover;
- cold/optimal/overheated grip response;
- pit reset behavior.

The game may expose temperatures and wear but not the Mercedes paper’s proprietary tyre-energy target. Therefore the test is primarily directional and relational unless a documented game field has the same physical definition.

### G3 — fuel and ERS

Use identical laps with varied fuel load and deployment modes. Test:

- lap-time sensitivity to fuel mass;
- battery state transition and bounds;
- deploy/harvest balance;
- inlap recuperation;
- terminal-energy feasibility;
- DUHR/FIENI optimization recommendations against scripted alternatives.

### G4 — strategy

Use deterministic AI difficulty, weather and safety-car seeds when possible. Test:

- undercut/overcut crossover;
- pit-loss model;
- tyre-life disturbance response;
- Monte Carlo strategy rank stability;
- DP/MINLP/RL regret on small controlled races;
- opponent-conditioned pit timing.

### G5 — world model and planner

Collect complete episodes, hold out entire tracks and conditions, then test:

- state/action next-step prediction;
- long-horizon rollout;
- controllable vs noncontrollable latent separation;
- uncertainty calibration;
- CEM/TD-MPC planning;
- planner exploitation of model errors.

## Experimental controls

- lock game version, assists, setup, AI, weather seed and damage rules;
- retain raw packets and hashes;
- synchronize timestamps before resampling;
- repeat every condition across seeds/runs;
- alter one factor at a time for causal tests;
- never tune on the final game benchmark;
- report domain differences instead of forcing agreement.

## Promotion criterion

Game evidence can promote a component only when:

1. public-data performance is already acceptable;
2. synthetic invariants pass;
3. game causal direction matches;
4. magnitude error is inside a pre-declared tolerance or uncertainty interval;
5. the component remains stable in closed loop;
6. no game-specific correction degrades public-data results.

A component that only fits the game belongs in a game-domain adapter, not the core real-world-oriented engine.
