# Legal, Data and Branding Guardrails

This is an engineering checklist, not legal advice.

## Critical constraints

Formula 1's published guidelines state that its logos require express permission; results/timing data and other assets are protected; permitted word marks should inform rather than brand; simulators should not use Formula 1 rights without a licence; and substantial timing data should not be scraped/reproduced commercially. The guidelines also contain restrictions concerning AI use of Formula 1 rights.

Therefore:

- keep **APEX** as the product identity;
- describe it editorially as a motorsport or open-wheel racing research simulator;
- do not use official logos, typefaces, liveries, screenshots, audio, video or copied visual assets;
- do not make the UI look like an official Formula 1 product;
- do not ship bulk downloaded telemetry/timing data in the repository;
- do not imply endorsement or team association;
- keep the early project educational/non-commercial;
- review current source terms before public deployment or monetization;
- seek qualified legal advice before commercial use involving protected data/marks.

## Safer portfolio presentation

Use fictional entries and generic cars in simulated races. Demonstrate the ingestion/replay method on limited, non-redistributed data and show derived error summaries rather than republishing a complete timing database.

## Source-specific compliance

For every source store:

```text
source name and URL
terms/license URL and access date
query purpose
allowed storage/redistribution assumptions
rate limits and user agent
raw retention policy
derived artifact policy
```

## No-game boundary

Do not copy assets or data from official games. APEX does not need F1 25: the correct architecture is public historical telemetry + transparent physics + synthetic worlds + learned residuals.

## Review references

- Formula 1 guidelines: https://www.formula1.com/en/information/guidelines.4EOKE9RRqevL4niTK9kWyt
- OpenF1 docs/disclaimer: https://openf1.org/docs/
- FastF1 docs/license links: https://docs.fastf1.dev/
- Jolpica terms/docs: https://github.com/jolpica/jolpica-f1
- FIA regulations portal: https://www.fia.com/regulation/category/110
