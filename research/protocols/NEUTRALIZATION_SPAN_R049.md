# R049 neutralization field-span baseline

Extend the matched nonpitting snapshot audit to the already opened
OpenF1 development races. Compare before, during and after each
global SC or VSC episode. Require five common drivers and complete
laps in each phase. Split by entire event.

For each mode, predict neutralized span from pre-event span using
the median ratio in the other races. In the same fold predict the
first green span using the corresponding median after/before ratio.
Exclude zero pre-spans. Compare each prediction against preserving
pre-event span and report each phase separately. Require at least
two distinct training races for a scored episode. This is a scalar
field-span test. The full gate requires per-car gap replay and
order and restart invariants.
