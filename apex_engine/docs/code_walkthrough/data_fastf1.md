# FastF1 adapter

Loads session/lap telemetry, resamples it, converts units and estimates missing controls. The import is optional so offline learning still works.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?
