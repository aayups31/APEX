# Phase 04 — FastF1, OpenF1 and source adapters

## Goal

Obtain session data, cache it, preserve source payloads, align independent streams and translate units.

## Instructor loop

1. Predict what artifact or behaviour should exist at the end.
2. Read the relevant textbook chapter.
3. Open the referenced source file before running it.
4. Execute the smallest command that proves the idea.
5. Inspect shapes, units, timestamps and persistent artifacts.
6. Introduce one deliberate failure.
7. Explain why the quality gate, test or metric detected it.
8. Compare at least two implementation choices.
9. Write the decision in your engineering log.

## Completion evidence

Do not mark the phase complete because code ran. Mark it complete when you can explain the inputs, outputs, invariants, failure modes, alternative designs and operational consequence of being wrong.

## Follow-along command chain

```bash
# 1. Retrieve one historical source session and translate it to the contract.
apexsim ingest-fastf1 \
  --year 2025 --event Monza --session R --driver VER \
  --output data/raw/monza_ver.csv

# 2. Inspect and validate before training.
apexsim validate data/raw/monza_ver.csv

# 3. Feed the exact adapter output into the complete pipeline.
apexsim run-canonical \
  --input-path data/raw/monza_ver.csv \
  --config configs/fast.yaml \
  --run-id monza_ver_gru
```

`run-canonical` copies the input file into the run directory. This is deliberate: the exact evidence used for training becomes part of run lineage, and every later stage sees the same contract regardless of whether the source was FastF1, OpenF1 or the offline generator.

### Break-it exercise

Rename or remove one required contract column, then run `apexsim validate`. Explain why the failure belongs before splitting and normalization rather than inside the model training loop.
