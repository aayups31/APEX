# Complete code atlas

`cli.py` resolves commands, `config.py` validates intent, source adapters produce the contract, windowing creates examples, models learn transitions, training changes parameters, evaluation measures rollout truth, simulation applies interventions, pipeline stages persist artifacts, registry records state, serving/UI expose results.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?
