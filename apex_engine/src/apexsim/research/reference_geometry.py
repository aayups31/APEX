"""R029 periodic reference racing traces, analytic curvature and explicit unknowns."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize_scalar
from scipy.spatial import cKDTree

from apexsim.track_geometry import GeometrySample


@dataclass(frozen=True)
class GeometryConfig:
    harmonics: int = 48
    alpha: float = .05

    def __post_init__(self) -> None:
        if type(self.harmonics) is not int or not 1 <= self.harmonics <= 256 or not np.isfinite(self.alpha) or self.alpha < 0:
            raise ValueError("Invalid Fourier geometry configuration")


CANDIDATES = (GeometryConfig(48, .05), GeometryConfig(96, .05), GeometryConfig(96, .5))


def chord_parameter(xy: np.ndarray) -> tuple[np.ndarray, float]:
    xy = np.asarray(xy, float)
    if xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 16 or not np.isfinite(xy).all():
        raise ValueError("A reference lap needs finite two-dimensional position samples")
    steps = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    if np.any(steps <= 1e-9):
        raise ValueError("Repeated/degenerate position samples cannot define monotone chord station")
    station = np.r_[0., np.cumsum(steps)]
    if station[-1] <= 1:
        raise ValueError("Degenerate reference lap length")
    return station/station[-1], float(station[-1])


def equal_phase_points(xy: np.ndarray, count: int = 512) -> np.ndarray:
    phase, _ = chord_parameter(xy)
    query = np.arange(count)/count
    return np.column_stack([np.interp(query, phase, xy[:, axis]) for axis in (0, 1)])


def register_lap(xy: np.ndarray, reference: np.ndarray) -> tuple[np.ndarray, dict]:
    """Kabsch rigid pose registration only: no scale, reflection or local shape warp."""
    x, y = equal_phase_points(xy), equal_phase_points(reference)
    xc, yc = x.mean(axis=0), y.mean(axis=0)
    u, _, vt = np.linalg.svd((x-xc).T@(y-yc))
    correction = np.diag([1., np.linalg.det(u@vt)])
    rotation = u@correction@vt
    translation = yc-xc@rotation
    aligned = np.asarray(xy, float)@rotation+translation
    return aligned, {"rotation": rotation.tolist(), "translation_m": translation.tolist(),
                     "determinant": float(np.linalg.det(rotation)), "scale": 1.,
                     "phase_correspondences": 512, "coordinate_registration_not_shape_fit": True,
                     "rms_before_m": float(np.sqrt(np.mean(np.sum((x-y)**2, axis=1)))),
                     "rms_after_m": float(np.sqrt(np.mean(np.sum((x@rotation+translation-y)**2, axis=1))))}


def basis(u: np.ndarray, config: GeometryConfig, derivative: int = 0) -> np.ndarray:
    values = np.atleast_1d(np.asarray(u, float))
    if values.ndim != 1 or not np.isfinite(values).all() or derivative not in (0, 1, 2):
        raise ValueError("Invalid finite Fourier parameter/derivative")
    omega = 2*np.pi*np.arange(1, config.harmonics+1)
    phase = values[:, None]*omega
    if derivative == 0:
        return np.column_stack((np.ones(len(values)), np.cos(phase), np.sin(phase)))
    if derivative == 1:
        return np.column_stack((np.zeros(len(values)), -np.sin(phase)*omega, np.cos(phase)*omega))
    return np.column_stack((np.zeros(len(values)), -np.cos(phase)*omega**2, -np.sin(phase)*omega**2))


class ReferenceCurve:
    """Smooth periodic XY curve; true arc station is derived from analytic speed."""
    def __init__(self, coefficients: np.ndarray, config: GeometryConfig, track_id: str, *, intervals: int = 16384):
        self.coefficients = np.asarray(coefficients, float).copy()
        self.config, self.track_id = config, track_id
        if self.coefficients.shape != (1+2*config.harmonics, 2) or not np.isfinite(self.coefficients).all() or intervals < 1024:
            raise ValueError("Invalid reference geometry coefficients/integration resolution")
        self.arc_u = np.linspace(0, 1, intervals+1)
        speed = np.linalg.norm(self.evaluate_u(self.arc_u, 1), axis=1)
        if not np.isfinite(speed).all() or speed.min() <= .05*np.median(speed):
            raise ValueError("Reference curve has a degenerate/cusped tangent")
        self.arc_s = np.r_[0., cumulative_trapezoid(speed, self.arc_u)]
        if np.any(np.diff(self.arc_s) <= 0) or self.arc_s[-1] <= 1:
            raise ValueError("Reference arc station must be positive and strictly monotone")
        self._inverse = PchipInterpolator(self.arc_s, self.arc_u, extrapolate=False)
        self._forward = PchipInterpolator(self.arc_u, self.arc_s, extrapolate=False)
        self.lookup_u = np.arange(4096)/4096
        self._tree = cKDTree(self.evaluate_u(self.lookup_u))

    @property
    def length_m(self) -> float:
        return float(self.arc_s[-1])

    def evaluate_u(self, u: np.ndarray, derivative: int = 0) -> np.ndarray:
        return basis(u, self.config, derivative)@self.coefficients

    def geometry(self, station: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        station = np.atleast_1d(np.asarray(station, float))
        if station.ndim != 1 or not np.isfinite(station).all():
            raise ValueError("Reference station must be finite")
        u = self._inverse(np.mod(station, self.length_m))
        xy, velocity, acceleration = (self.evaluate_u(u, order) for order in (0, 1, 2))
        norm = np.linalg.norm(velocity, axis=1)
        curvature = (velocity[:, 0]*acceleration[:, 1]-velocity[:, 1]*acceleration[:, 0])/norm**3
        return xy, velocity/norm[:, None], curvature

    def sample_geometry(self, distance_m: float) -> GeometrySample:
        xy, tangent, curvature = self.geometry(np.array([distance_m]))
        return GeometrySample(float(distance_m % self.length_m), *xy[0].tolist(),
                              float(np.arctan2(tangent[0, 1], tangent[0, 0])), float(curvature[0]), "RECONSTRUCTED_REFERENCE_TRACE")

    def require_ancillary(self, field: str):
        raise ValueError(f"UNKNOWN {field}: reference geometry does not identify ancillary track properties")

    def project(self, xy: np.ndarray, *, refine: bool = True) -> dict[str, np.ndarray]:
        xy = np.asarray(xy, float)
        if xy.ndim != 2 or xy.shape[1] != 2 or not np.isfinite(xy).all():
            raise ValueError("Projection needs finite two-dimensional points")
        _, indices = self._tree.query(xy)
        parameters = self.lookup_u[indices].copy()
        if refine:
            for i, (point, start) in enumerate(zip(xy, parameters, strict=True)):
                def objective(u: float, point=point) -> float:
                    delta = self.evaluate_u(np.array([u]))[0]-point
                    return float(delta@delta)
                result = minimize_scalar(objective, bounds=(start-3/4096, start+3/4096), method="bounded",
                                         options={"xatol": 1e-11})
                if not result.success:
                    raise ValueError("Closest reference projection failed")
                parameters[i] = result.x % 1
        station = self._forward(parameters)
        points, tangents, curvature = self.geometry(station)
        delta = xy-points
        normal = np.column_stack((-tangents[:, 1], tangents[:, 0]))
        return {"station_m": station, "distance_m": np.linalg.norm(delta, axis=1),
                "signed_lateral_m": np.sum(delta*normal, axis=1), "xy_m": points, "curvature_1pm": curvature}


def fit_reference(laps: list[np.ndarray], config: GeometryConfig, track_id: str) -> ReferenceCurve:
    if not laps:
        raise ValueError("No training reference laps")
    designs = [basis(chord_parameter(xy)[0], config) for xy in laps]
    x, y = np.concatenate(designs), np.concatenate(laps)
    center = y.mean(axis=0)
    penalty = config.alpha*np.r_[0., np.tile((np.arange(1, config.harmonics+1)/config.harmonics)**4, 2)]
    normal = x.T@x/len(x)+np.diag(penalty)
    coefficients = np.linalg.solve(normal, x.T@(y-center)/len(x))
    coefficients[0] += center
    return ReferenceCurve(coefficients, config, track_id)


def polyline_distances(points: np.ndarray, line: np.ndarray) -> np.ndarray:
    """Independent exact segment distance control, including the raw endpoint chord."""
    start, end = np.asarray(line, float), np.roll(line, -1, axis=0)
    direction = end-start
    length2 = np.sum(direction**2, axis=1)
    supported = length2 > 1e-18
    start, direction, length2 = start[supported], direction[supported], length2[supported]
    values = []
    for block in np.array_split(np.asarray(points, float), max(1, int(np.ceil(len(points)/256)))):
        delta = block[:, None, :]-start[None, :, :]
        along = np.maximum(0., np.minimum(1., np.sum(delta*direction[None, :, :], axis=2)/length2))
        residual = delta-along[:, :, None]*direction[None, :, :]
        values.extend(np.sqrt(np.min(np.sum(residual**2, axis=2), axis=1)))
    return np.array(values)


def evaluate_reference(curve: ReferenceCurve, xy: np.ndarray, baseline: np.ndarray) -> tuple[dict, dict]:
    projection = curve.project(xy)
    distances = projection["distance_m"]
    raw = polyline_distances(xy, baseline)
    phase, length = chord_parameter(xy)
    centers = np.arange(25., length-25., 25.)
    points = [np.column_stack([np.interp(centers+offset, phase*length, xy[:, axis]) for axis in (0, 1)])
              for offset in (-25., 0., 25.)]
    a, b = points[1]-points[0], points[2]-points[1]
    turning = np.arctan2(a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0], np.sum(a*b, axis=1))
    proxy = turning/((np.linalg.norm(a, axis=1)+np.linalg.norm(b, axis=1))/2)
    coarse = curve.project(points[1])
    differences = abs(coarse["curvature_1pm"]-proxy)
    unwrapped = np.unwrap(projection["station_m"]/curve.length_m*2*np.pi)*curve.length_m/(2*np.pi)
    metrics = {"xy_rmse_m": float(np.sqrt(np.mean(distances**2))), "xy_p95_m": float(np.quantile(distances, .95)),
               "xy_max_m": float(distances.max()), "raw_polyline_p95_m": float(np.quantile(raw, .95)),
               "p95_minus_raw_polyline_m": float(np.quantile(distances, .95)-np.quantile(raw, .95)),
               "backward_fraction": float(np.mean(np.diff(unwrapped) < -1e-6)),
               "coarse_curvature_mae_1pm": float(np.mean(differences)),
               "coarse_curvature_p95_1pm": float(np.quantile(differences, .95)), "coarse_step_m": 25.,
               "curvature_target_quality": "COARSE_CHORD_TURNING_PROXY_NOT_SURVEYED"}
    saved = {**projection, "raw_polyline_distance_m": raw, "coarse_xy_m": points[1],
             "coarse_curvature_proxy_1pm": proxy, "coarse_model_curvature_1pm": coarse["curvature_1pm"]}
    return metrics, saved


def reconstruction_gate(curve: ReferenceCurve, training: list[np.ndarray], test_metrics: list[dict]) -> dict:
    p0, p1 = curve.evaluate_u(np.array([0.])), curve.evaluate_u(np.array([1.]))
    v0, v1 = curve.evaluate_u(np.array([0.]), 1), curve.evaluate_u(np.array([1.]), 1)
    refined = ReferenceCurve(curve.coefficients, curve.config, curve.track_id, intervals=32768)
    _, _, curvature = curve.geometry(np.linspace(0, curve.length_m, 8192, endpoint=False))
    raw_length = float(np.median([chord_parameter(lap)[1] for lap in training]))
    diagnostics = {"analytic_position_seam_m": float(np.linalg.norm(p1-p0)), "analytic_tangent_seam": float(np.linalg.norm(v1-v0)),
                   "length_refinement_difference_m": abs(curve.length_m-refined.length_m),
                   "max_absolute_curvature_1pm": float(np.max(abs(curvature))), "training_median_chord_length_m": raw_length,
                   "relative_length_difference": abs(curve.length_m/raw_length-1)}
    geometric = (diagnostics["analytic_position_seam_m"] <= 1e-8 and diagnostics["analytic_tangent_seam"] <= 1e-8
                 and diagnostics["length_refinement_difference_m"] <= .001 and diagnostics["max_absolute_curvature_1pm"] <= .12
                 and diagnostics["relative_length_difference"] <= .03)
    each = [m["xy_rmse_m"] <= 6 and m["xy_p95_m"] <= 12 and m["p95_minus_raw_polyline_m"] <= 2
            and m["backward_fraction"] <= .02 and m["coarse_curvature_mae_1pm"] <= .003 and m["coarse_curvature_p95_1pm"] <= .015
            for m in test_metrics]
    return {"passed": geometric and bool(each) and all(each), "geometry_passed": geometric, "each_test_passed": each, **diagnostics}
