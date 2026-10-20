# Source-coherent curvature proxy v3

R029 ADAPTATION under the [v3 protocol](../protocols/TRACK_RECONSTRUCTION_V3.md).
Keep the [v2 support](OBSERVED_TRACK_SUPPORT_V2.md) and
[v2.1 boundary/pose](OBSERVED_TRACK_BOUNDARIES_V2_1.md) equations. The failed
v2.1 unfiltered proxy comparison remains a rejected experiment; its thresholds,
raw arrays and individual errors are not rewritten.

For observed source displacement vectors d_j=p_(j+1)-p_j, form the dimensionless
adjacent-direction cosine `c_j=dot(d_j,d_(j+1))/(||d_j||*||d_(j+1)||)`.
The accepted curvature-interval mask starts from native time support h_j and
removes BOTH intervals adjacent to every c_j<=0. These source samples do not
support a locally regular forward-reference derivative. This is a conservative
declared source-coherence assumption; the cause of a reversal remains UNKNOWN.
Compute it from original source XY, independently of curve fits/residuals and
rigid pose optimization. Finite nondegenerate displacements remain mandatory.

The25m centered turning proxy is evaluated only where its entire +/-25m stencil
avoids unsupported time or derivative intervals. Keep the denominator of the
support fraction equal to ALL candidate centers and retain the same>=75% and
>=100 accepted-target gates per test lap. Keep.003/m MAE and.015/m p95 tolerances.
Every native XY vertex still enters positional/backward/max-distance metrics.
No curvature residual is used to decide whether its own target is supported.

Save source turning cosines, time and derivative interval masks, time-only coarse
support, final target support and the UNFILTERED chronological turning proxy as
a DIAGNOSTIC, not an accepted target. Final unsupported proxy/model entries and
coarse coordinates are NaN UNKNOWN. The raw values remain auditable rather than
being silently clipped or relabelled measured road curvature.

The independent fixture travels0→10→20→10→30→40m on a straight line. Its adjacent
direction cosines are[1,-1,-1,1]; only the first/last intervals support a forward
derivative. A second fixture reorders circular observations: all XY scores stay
identical, while the invalid derivative windows abstain and unfiltered values
remain saved. SIMULATED artifact controls combine missing interiors, a partial
boundary and a reversal; profile/source guards prevent public promotion.

The additional24 confirmation laps are frozen before inspection and retain all
24 retrospective test laps. ALL48 must individually pass. Training/validation
and fitted coefficients/configurations remain those already sealed before the
v2.1 test outcomes. Report the two test strata separately; same-event additions
do not constitute additional independent circuit/season populations.
