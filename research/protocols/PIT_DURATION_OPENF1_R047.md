# R047 OpenF1 confirmation source substitution

The registered FastF1 confirmation failed during source acquisition.
Use OpenF1 pit-lane duration for the same five 2025 races. Freeze the
existing trained distributions, multipliers, race IDs, scores and
thresholds. This evaluates cross-provider confirmation.

Archive the sessions, pit, laps and race control responses and verify
identities. Reconcile each pit row to an adjacent inlap and flagged
outlap, using its own reported lap or the next lap as the outlap.
Require both lap clocks, the reported pit timestamp inside their
combined span, positive lane duration, and wholly green timing.
Require three preceding usable subject laps and at least three
unpitted contemporaneous drivers on all five race laps, with
the prefix end within 120 seconds. Use sector-time reconciliation
as the native clean-lap evidence where FastF1 accuracy flags are
unavailable. Publish exclusions and minimum support before accepting
the confirmation. Archived pit duration includes service.
