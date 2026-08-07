# Training loop

Clears gradients, performs the forward pass, computes reconstruction/KL loss, backpropagates, clips gradients, updates parameters and checkpoints by validation loss.

## Questions to answer

- What contract does this module receive?
- What does it promise to return or persist?
- Which invariants must remain true?
- Which errors should be retried, quarantined or treated as bugs?
- What simpler implementation could replace it?
- What future requirement would justify a more complex implementation?
