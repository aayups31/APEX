# GRU world model

Encodes history and then autoregresses. Each predicted state replaces the state portion of the next input, exposing compounding error.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?
