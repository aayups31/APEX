# V19 acquisition limitation, before scoring

The unauthenticated OpenF1 request for session 10006 car_data returns HTTP 401
with a global live-session restriction, including historical requests. A
FastF1 historical archive attempt also fails, and a direct request for its
Japanese race SessionInfo returns HTTP 401. No historical car snapshot was
acquired. The failed attempt and raw access response must be preserved.

Run a partial-availability diagnostic using the original nine verified FastF1
archives. All other cases retain zero support indicators under the frozen
missing-input rule. Keep all 392 comparisons and all race gates visible.
Record acquisition_ready=false and force new_holdout_acquisition_allowed=false
until the planned acquisition is completed. The diagnostic cannot authorize
confirmation or completion even if its prediction gates pass.

Preserve the original v19 extraction and candidate recipe. Expose acquisition
separately so a fresh, append-only run can use recovered historical data after
the source becomes available. No substitute session, provider-mixed target,
late observation or outcome-based case selection is permitted.
