# Physics and Hybrid Model

## Why a hybrid model

A pure neural model can fit broadcast telemetry while violating causality and physics. A pure physics model cannot identify confidential aero, setup, tyre and energy details from public data. APEX therefore uses:

```text
next state = constrained physics prior + bounded learned residual + uncertainty
```

## Delivered V0 equations

### Longitudinal motion

```text
m dv/dt = F_drive + F_ers - F_brake - F_drag - F_roll - F_grade
F_drag = 0.5 rho CdA v²
F_downforce = 0.5 rho ClA v²
```

Drive and braking force are restricted by the remaining friction-circle capacity after lateral demand.

### Lateral feasibility

```text
lateral acceleration = v² × |curvature|
friction capacity ≈ μ × (mg + downforce)
```

The current model uses a soft curvature speed limiter for stability. V1 should move toward a properly integrated path-following model with lateral offset and yaw error.

### Tyres

The delivered model includes:

- dry/wet compound grip;
- approximate optimum temperature window;
- heating from braking, throttle and lateral work;
- cooling from air/rain;
- compound-specific wear;
- a low-health cliff;
- wet/dry compound mismatch penalties;
- driver tyre-management effect.

These quantities are latent estimates. Do not display them as measured real tyre temperatures or health.

### Fuel

Fuel changes mass and is consumed from distance and throttle. V1 calibration should fit consumption from race-distance constraints, not pretend broadcast telemetry exposes fuel flow.

### Energy store

The delivered battery/ERS is a generic bounded energy proxy. Public data generally does not expose the complete deployment state needed to identify actual strategy. Treat it as a scenario variable until stronger evidence exists.

## V1 physics upgrades

1. signed curvature and lateral offset;
2. bicycle or curvilinear point-mass model;
3. path/racing-line target;
4. combined-slip tyre approximation;
5. separate front/rear grip balance only if identifiable;
6. pit-lane geometry;
7. surface sectors and dry-line state;
8. wind relative to heading;
9. damage and reliability model calibrated only at aggregate level;
10. event/ruleset-specific drag-reduction and energy assumptions.

## Calibration order

Calibrate in this order to avoid parameter compensation:

1. units and time alignment;
2. track distance and curvature;
3. drag/rolling behavior in coasting segments;
4. braking envelope;
5. acceleration/power envelope;
6. corner speed/grip envelope;
7. fuel trend;
8. tyre degradation at lap/stint scale;
9. driver action policy;
10. residual model.

## Identifiability warning

Several parameter combinations can reproduce the same public speed trace. For example, drag, power, wind and slope can trade off. Report parameter ranges or posterior uncertainty rather than one “true” value.

## Residual model inputs

```text
recent observed states
physics-predicted next state
controls
track segment embedding
weather and race state
car/driver/session embeddings with regularization
quality masks and time gaps
```

## Residual model outputs

Prefer bounded deltas:

```text
delta acceleration or speed
delta tyre latent state
delta fuel/energy proxy only where constrained
predictive variance / ensemble disagreement
```

The delivered `hybrid.py` provides a bounded correction interface. Connect the existing GRU/RSSM/SSM models only after replay baselines are frozen.

## Model ladder

1. persistence;
2. constant acceleration;
3. linear calibrated dynamics;
4. deterministic physics prior;
5. gradient-boosted residual;
6. GRU residual;
7. RSSM latent residual;
8. selective SSM residual;
9. ensemble or probabilistic model.

A complex model is accepted only if it improves held-out multi-step replay and calibration while preserving physical validity.
