# R042 synthetic multi-lap tyre control

Research foundation R1 and production kernel R0. This synthetic benchmark
uses the accepted R039 heat and R040 wear equations. It does not require an
R041 fitted compound prior. Real-race validation of pit crossover remains
contingent on R041 and observed pit-loss calibration.

Use one effective axle over four laps, each with an 80-second nominal
exposure clock independent of scored pace. The bath temperatures are
308.15 K road and 298.15 K air. Use the R039 default thermal parameters.
Each lap selects conserve or push. The two controls dissipate 700 or
2,100 W into tread and 300 W into carcass. Push deducts 0.45 s from
scored pace. The initial soft tyre starts at 333.15 K in both nodes with
0.14 wear. An optional stop before laps two through four replaces it with
a fresh soft or hard at 323.15 K and zero wear. The stop adds a fixed
loss to scored time. The replacement state is a declared input.

Soft and hard use wear rates 1e-7 and 5e-8 per joule, wear pace slopes
28 and 18 seconds per unit fraction, and fresh pace offsets 0 and 0.9 s.
These are synthetic parameters. Scored lap time is 80 s plus the fresh
offset and wear pace slope times mean wear over the exposure, less the
push deduction.

Enumerate all 112 legal control and pit sequences with no early pruning.
Use the exact heat step with left-edge wear and trapezoidal mean wear on
4, 16, 64 and 256 substeps per lap. Compare against a separate DOP853
integration of temperatures, continuous wear and integrated wear for
every strategy. Compare with a fixed conserve/no-stop policy.

The crossover pit loss is best no-stop time minus best stop time before
adding pit loss. At fixed losses of 2 and 20 seconds, require the oracle
and fine mesh to prefer a stop and no stop respectively. The finite-mesh
winner at each fixed loss must be within 0.02 s of the reference optimum
when evaluated by the reference integrator. The fine mesh maximum time
error across all strategies and crossover error must each be at most
0.02 s. Maximum time error must decrease at each refinement. Each stint
must have monotone bounded wear and each heat step must close to 1e-6 J.
Keep the time and audit receipts, objective gaps and selected controls.
This only qualifies the synthetic research slice.
