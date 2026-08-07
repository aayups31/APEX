# Protocol — Vehicle and Tyre Optimal Control

## Research basis
Perantoni/Limebeer minimum-lap-time vehicle dynamics; Tremlett/West thermal and wear-aware tyre management; Pacejka force-slip reference; Farroni multiphysical wear.

## Stages
V1 curvilinear point mass → V2 bicycle model and friction ellipse → V3 load transfer/aero balance → V4 thermal tyre states → V5 wear from sliding energy → V6 direct-transcription lap solver → V7 multi-lap tyre-management OCP.

## Parameter discipline
Separate identifiable public-data parameters, literature priors and unidentifiable nuisance parameters. Use sensitivity/identifiability analysis before adding states.

## Acceptance
Track closure, force balance, plausible force-slip envelope, energy conservation checks, temperature-window behavior, wear monotonicity, lap-time replay, and optimizer mesh-convergence.
