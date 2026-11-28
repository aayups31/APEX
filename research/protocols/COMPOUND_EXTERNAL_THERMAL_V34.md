# R041 external tyre telemetry and masked reconstruction pilot

Check the public BETTY Monza plot payload and Constructor driving
export for populated sensor channels, synchronized vehicle inputs
and completed lap coverage. Keep source bytes in the local cache.
Test a three-lap privileged pace forecast only on recordings with
consecutive timed laps, trustworthy stint identity and separate
training and evaluation runs. Plot points and short recordings
can be used for narrower tests of sensor availability.

## Masked temperature reconstruction at Thunderhill

Use Stanford Digital Repository object `hh613qz0317` version 3.
Keep one copy of each publisher checksum. Train on the October
logs and evaluate on entirely separate November logs. Also report
the reverse transfer. Keep a sample's recorded four tread
temperatures as supervision and evaluation targets.

Sample causally at 4 Hz using the latest observation at or before
each grid point, with at most 0.1 s staleness. Start a new segment
across missing input support. Use speed, throttle command, engine
RPM, a binary brake indicator and horizontal position. The brake
indicator uses front-left brake pressure above 5 bar. Derive
longitudinal acceleration from speed and lateral acceleration from
the trailing change in horizontal path heading. Apply a 30 m/s²
acceleration bound. No measured tyre states, wheel channels, IMU,
precise brake pressure or other privileged observations enter the
masked input.

Compare four fixed regularized readouts:

- Time since segment start, with 15 s and 60 s warm-up curves.
- Time and causal controls with instantaneous, 10 s and 40 s
  exponential histories.
- Time and the existing two-node heat balance. Use 25 °C for the
  initial and boundary temperatures and a tread heating proxy of
  `30 * speed * (abs(ax) + abs(ay))` watts. Use previous-frame
  forcing for each interval. The physical parameters are fixed.
- Time, controls and heat-balance features together.

Use a ridge penalty of 10 on features standardized using only the
training cohort. Fit a separate linear output for each wheel jointly.
Include observations at or above 5 m/s after 15 s of continuous history. Score
only finite targets in the range −30 to 140 °C. Report equal-run
MAE, median per-wheel error magnitudes and run win counts. The
hybrid must improve on time-only in both directions and in a
majority of runs in each direction. Its added thermal value must
also beat the controls-only model in both directions. Report a
privileged initialization diagnostic by giving the readout each
test segment's first eligible measured temperature and estimating subsequent
temperature change with the masked controls. This is distinct
from a privileged three-lap pace predictor.

After viewing the first transfer results, add a diagnostic
comparator on the same samples. Hold the measured starting
temperature constant to separate the benefit of scale initialization
from any ability to infer temperature change. This comparison
does not enter the registered masked-temperature gate.

This pilot probes recoverability of external tread temperature.
Leave the registered 393-case Formula 1 cohort, both crossover
labels, pace bounds, race gates and fresh confirmation intact.
Report that fuel sensitivity and any temperature-to-pace benefit
require separate evaluation.
