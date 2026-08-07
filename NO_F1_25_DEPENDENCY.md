# No F1 25 Dependency

The original apprenticeship contains a historical chapter and diagram about a possible F1 25 UDP migration. That path is **not required** for this complete-simulation edition.

Use this data hierarchy instead:

1. synthetic causal worlds for tests;
2. FastF1 for historical lap telemetry and track reconstruction;
3. OpenF1 for 2023+ full-field race streams;
4. Jolpica for schedules/results metadata;
5. calibrated physics and learned residuals for unobserved dynamics.

You may leave the legacy F1 25 learning material untouched as a comparison, but none of the new milestones or runnable code depend on the game.
