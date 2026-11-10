# V23 query compatibility

The historical car endpoint returns HTTP 500 for both narrow and original
bounded-time queries. A session-and-driver query succeeds with HTTP 200.
Before scoring, change acquisition to the supported session/driver request.
Preserve that exact request and raw response. Slice each already opened race's
driver history locally at the original completed lap clocks. Future observations
cannot enter per-case summaries. Retain all other v19 extraction and v23 model
rules. Existing verified native FastF1 summaries can be reused with their
sealed parent binding and exact original cohort.
