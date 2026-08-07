# Local orchestration

Records run state, executes stages in dependency order and writes a final summary or failed status.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?
