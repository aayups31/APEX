# Standardization

Fits means and standard deviations only on training sessions. Target and input statistics are stored for reproducible inverse transforms.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?
