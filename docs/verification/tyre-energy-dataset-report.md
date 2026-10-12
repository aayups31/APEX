# R024 public tyre-energy proxy dataset

## A. Current state

**R024 DONE**, 2026-10-11. Research inventory **23/73 DONE**, build inventory
13/66 unchanged. Scoped research R1/kernel R0; no maturity or production promotion.
R023 remains TODO; R025 is the next P0 dependency-priority slice.

Baseline `7fefeb4`: existing 469-test regression and final matrix CI pass.
Fresh relevant baseline: five tyre-energy/forecast tests pass in 21.14 s;
`.cache/r024-baseline-research-20261012` has 140 finite synthetic predictions,
ridge RMSE .0554717 kJ and feasible terminal resource states. Its existing ridge
conditioning warning is retained. User artifacts were preserved and left unstaged.

## B. Scope

Completed a causal native-sample four-wheel proxy dataset with explicit priors,
UNKNOWN measured quantities, source-row lineage, exclusions and portable reload.
Two fixed drivers (4/44) across five existing development races. No forecasting
training or physical-energy accuracy claim follows dataset construction.

## C. Source of truth

Master guide, maturity model, R024/backlog, existing R006 estimator, TODD protocol,
FastF1 archive contracts, sealed R021 eligible lap mask, and the
[frozen plan](../../research/protocols/TYRE_ENERGY_DATASET.md).

Native FastF1 3.8.3 docs and [official source](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/core.py)
confirm position units (1/10 m), speed (km/h), throttle (%) and binary brake.
No proprietary wheel force/slip/steering/energy observations were available.
All five source archives had exact offline replay, zero network attempts and
zero mismatched tables; conversion verifies source hashes before and after use.
The R020 nine-weekend permanent benchmark remains untouched.

## D. Implementation and inspected public artifact

`apexsim.research.tyre_energy_dataset` reconstructs speed derivatives from five
past car samples and local motion from seven past position samples. Position
lookup is backward-only, with maximum .35 s lag. History stays within one eligible
stint segment; each rejected native row breaks the forecasting sequence. Strict
support limits reject gaps, invalid controls, unsupported motion and normal loads
requiring R006's 50 N projection. No clipping or gap filling was required.

R006's energy equation is unchanged. Steering/lateral acceleration/binary brake
pressure are PROXY; mass900 kg and other vehicle/slip/aero coefficients are PRIOR.
Energy is kJ over the actual preceding native interval; power is kW. The
[equation/unit map](../../research/equations/TYRE_ENERGY_PROXY_V1.md) records
the mathematical XY/rightward-positive convention and its physical limitations.

| 2024 race | Driver 4 samples | Driver 44 samples | Total |
| --- | ---: | ---: | ---: |
| Bahrain | 12,472 | 13,755 | 26,227 |
| Australia | 13,061 | 0 | 13,061 |
| Miami | 14,114 | 14,015 | 28,129 |
| Monza | 13,156 | 13,394 | 26,550 |
| Singapore | 19,394 | 19,085 | 38,479 |
| Total | 72,197 | 60,249 | **132,446** |

All **333,274** native car rows are accounted for: 132,446 accepted and
200,828 excluded. Inside the existing clean-lap mask, 132,446/149,263
samples (**88.73%**) pass the proxy support gate. Whole-stream retention is lower
because native archives also contain pre/post-race and ineligible lap samples.

| Exclusive first exclusion reason | Rows |
| --- | ---: |
| Outside eligible lap | 151,745 |
| No eligible stint segment (Australia/44) | 32,266 |
| History gap/span or position lag | 14,478 |
| Unsupported motion envelope | 1,977 |
| Wheel load requiring projection | 190 |
| Segment history warmup | 153 |
| Unsupported speed/control | 19 |

The first public attempt stopped on Australia's absent eligible Hamilton stream.
The original code required nonempty data in every driver/event stream; the
protocol specified fixed-driver representation across the corpus. The correction
retains all 32,266 Australia/44 rows as named exclusions and tests that path.
No driver substitution, support-prior change, numerical threshold relaxation or
proxy-outcome tuning occurred. Australia still passes the ≥1,000/event gate.

All **50 canonical fields** carry explicit truth labels and units. Four energy
and four power fields are PROXY; twelve measured force/slip/energy fields remain
null UNKNOWN. Configuration preserves field ancestry and vehicle priors. Source
manifests retain queries, versions, acquisition metadata, licence notes and file
hashes. Parquet schema metadata and reload checks preserve these labels.

Native intervals are approximately .158–.481 s, median .240 s; no 0.1 s sampling
claim is made. There are **8,058 uninterrupted sequences**, length median11,
95th percentile 50 and maximum 143. Next-sample candidate counts, respecting
sequence boundaries, are 81,931 with eight past samples, 40,607 with twenty,
and only 394 with one hundred. These are availability counts, not training results.
R025 must match histories/horizons and avoid interleaving drivers or bridging gaps.

Conditional mass sensitivity gives linear energy scaling under aero0 and fixed
kinematics: 810 kg scales energy by .9; three rows fall below the load-support
boundary and are excluded from that sensitivity. 990 kg scales by 1.1 with no
additional unsupported rows. This sensitivity does not identify actual car mass
or physical energy; the primary prior remains 900 kg.

## E. Acceptance, tests and reproducibility

The frozen R024 gate passes: ≥1,000 finite nonnegative proxy samples per event,
both selected drivers represented across the corpus, complete labels, every
native row accounted for, and immutable portable artifacts with valid lineage.

- Nine new targeted tests pass (29.88 s), including independent quadratic-motion
  and hand energy fixtures, unit checks, future-input invariance, gap/stint resets,
  invalid/protected inputs, unknown-target/label tampering, missing-stream handling,
  immutable output reuse and relocated artifact reload.
- Final full regression at corrected checkpoint `65c83a3`: **478 passed**, two
  pre-existing dependency warnings, 201.95 s. Cwd `apex_engine`, OMP/MKL/OpenBLAS
  threads1, fresh `.cache/r024-final-regression-20261012`.
- Ruff and Airflow wrapper compile pass.
- [CI 38201271391](https://github.com/aayups31/APEX/actions/runs/38201271391)
  passes both Python 3.11/3.12 jobs. Prior checkpoint CI also passed.
- Real artifact CLI reload passes schema, field labels, units, finite targets,
  file inventory/hashes, input-mask binding, source membership, native bounds,
  accepted/rejected accounting and energy=`power*dt`. No original cache is required
  for portable reload; hash integrity does not establish source authenticity.

Public artifact: `.cache/tyre-energy-public-corrected-20261012`.
Manifest seal `7793df65b58884be74529ecf3114ccf2efc310d0a3dd99dfa9edec4d961c2272`.
Input R021 dataset seal
`d79966d3b13c06cb8a0bd6f6bcff1690a10965d6414e0e71840ecf6d7811d6a2`.
The run started during correction review; its manifest records base commit
`dfc2a31` and actual implementation fingerprints, matching the code committed
in `65c83a3`. No input or scientific code changed during conversion.

The [machine evidence](tyre-energy-dataset-evidence.json) includes full quality,
source manifests, field schemas/labels, distributions, exclusions, config,
mass sensitivity, replay seals and verification metadata. Evidence seal
`abb28713870aa1a83f849902b05c94f7d6d181a8f18c5619fca62d33d53543a1`.
Bulk provider telemetry stays ignored. See the [run/data card](../data/tyre-energy-proxy.md).

## F. Limits

These energies are proxies under assumed vehicle/slip/coordinate conventions.
They are not measured tyre energy, steering, force or wear. The retrospective
clean-lap mask and irregular sampling are recorded explicitly.

Local derivatives can be noisy; wheel side depends on the assumed XY convention.
Actual mass, downforce, slip, brake pressure and force allocation are unmeasured.
Two drivers, one missing event/driver cell, short histories and correlated samples
limit representativeness. Proxy self-consistency cannot establish physical accuracy,
causal wear effects, forecast skill, world-model quality or production readiness.

## G. Order

Implementation `dfc2a31` and accounting correction `65c83a3` were pushed directly
to `main` during the work. This completion report, machine evidence, data card,
inventory and DONE row form the closure checkpoint.

Next priority work is **R025**: preregister a matched linear/ridge/XGBoost/GRU/
LSTM/TFT proxy forecasting comparison, whole-event splits, causal sequences,
comparable horizons and explicit compute budget. **R026** then separates seen/
unseen-track evidence. **R023** remains pending for robust skewed-t observations
and a frozen CRPS/RMSPE accept/reject comparison against R021/R022; its improvement
or repair of the earlier nominal-coverage shortfall is not assumed.
