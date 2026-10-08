# Verification Reports

This directory contains recorded verification results for major stages of APEX.

## Reports

- [Original engine report](original-engine-report.md)
- [Complete simulation report](simulation-report.md)
- [Research report](research-report.md)
- [Foundation and local platform report](foundation-platform-report.md)
- [Data provenance report](data-provenance-report.md)
- [Public tables and frozen splits](public-data-foundation-report.md)
- [FastF1 acquisition and offline replay](fastf1-offline-replay-report.md)
- [OpenF1 acquisition and offline replay](openf1-offline-replay-report.md)
- [Jolpica event catalog](jolpica-event-catalog-report.md)
- [Temporal alignment](temporal-alignment-report.md)
- [Observed public fields and CSV migration](observed-public-fields-report.md)

## Purpose

These reports document what was tested at a particular point in development.

They should not be interpreted as permanent guarantees. Results can become stale as the code changes.

Current claims should always be confirmed by running:

```bash
cd ../../apex_engine
pytest -q
