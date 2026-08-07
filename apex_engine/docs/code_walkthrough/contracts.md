# Canonical contract

This file is the architectural seam between changing data sources and stable model code. Identity, state, action, context and auxiliary features are intentionally separated.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?
