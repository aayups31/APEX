# Synthetic generator

A controlled causal environment produces track geometry, driver policy, weather, tyre wear and longitudinal dynamics. Known rules make debugging possible.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?
