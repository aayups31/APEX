# V23 query compatibility

The historical car endpoint returns HTTP 500 for both narrow and original
bounded-time queries. A session-and-driver query succeeds with HTTP 200.
Before scoring, change acquisition to the supported session/driver request.
Preserve that exact request and raw response. Slice each already opened race's
driver history locally at the original completed lap clocks. Future observations
cannot enter per-case summaries. Retain all other v19 extraction and v23 model
rules. Existing verified native FastF1 summaries can be reused with their
sealed parent binding and exact original cohort.

The follow-up request isolates the HTTP 500 to a malformed lower-bound key.
With requests' query encoder, the key is date> and the encoder adds the equals
delimiter. Using date>= as the key encodes an extra equals. The corrected query
returns HTTP 200. Keep already sealed session/driver responses. Use corrected
time bounds for remaining drivers, and preserve identical local lap slicing for
both response types. This acquisition fix precedes any v23 model score.

The service truncates sub-millisecond filter bounds to its millisecond clock.
Permit one millisecond plus the two-microsecond encoding allowance when
checking response envelopes. Exact local half-open lap masks still determine
which observations contribute to every summary.
