"""R032 synthetic force-sensor oracle; never infer availability of public sensors."""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from apexsim.research.aero_bicycle import AeroParameters
from apexsim.research.bicycle import BicycleParameters

FIELDS = ("air_density_kgpm3", "drag_area_m2", "downforce_area_m2", "front_downforce_fraction", "cg_height_m")


def oracle_observations(aero: AeroParameters, *, zero_force: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Drag and axle loads [N] given synthetic known mass and unsaturated tyre force.

    Rows in the analytic Jacobian follow flattened [drag, front load, rear load].
    Observed load/force sensors assumed here are UNKNOWN in public telemetry.
    """
    p = BicycleParameters()
    length = p.front_distance_m+p.rear_distance_m
    rows, jacobians = [], []
    for v in (20., 40., 70.):
        for force in ((0.,) if zero_force else (-2000., 0., 2000.)):
            unit_q, q = .5*v*v, .5*aero.air_density_kgpm3*v*v
            z, beta = q*aero.downforce_area_m2, aero.front_downforce_fraction
            front = p.mass_kg*p.gravity_mps2*p.rear_distance_m/length+beta*z-aero.cg_height_m*force/length
            rear = p.mass_kg*p.gravity_mps2*p.front_distance_m/length+(1-beta)*z+aero.cg_height_m*force/length
            rows.extend([q*aero.drag_area_m2, front, rear])
            jacobians.extend([[unit_q*aero.drag_area_m2, q, 0, 0, 0],
                              [beta*unit_q*aero.downforce_area_m2, 0, beta*q, z, -force/length],
                              [(1-beta)*unit_q*aero.downforce_area_m2, 0, (1-beta)*q, -z, force/length]])
    return np.array(rows), np.array(jacobians)


def identifiability_report() -> dict:
    """Audit product confounding and finite differences; no fitting or inference."""
    aero = AeroParameters()
    theta = np.array([getattr(aero, k) for k in FIELDS])
    observed, jacobian = oracle_observations(aero)
    normalized = jacobian*theta/np.maximum(1., abs(observed))[:, None]
    numerical = np.zeros_like(jacobian)
    for i, key in enumerate(FIELDS):
        step = theta[i]*1e-5
        plus = oracle_observations(replace(aero, **{key: theta[i]+step}))[0]
        minus = oracle_observations(replace(aero, **{key: theta[i]-step}))[0]
        numerical[:, i] = (plus-minus)/(2*step)
    error = float(np.max(abs((numerical-jacobian)*theta/np.maximum(1., abs(observed))[:, None])))
    singular = np.linalg.svd(normalized, compute_uv=False)
    rank = int(sum(singular > singular[0]*1e-8))
    fixed_density_rank = int(np.linalg.matrix_rank(normalized[:, 1:], tol=1e-8))
    zero_y, zero_j = oracle_observations(aero, zero_force=True)
    zero_rank = int(np.linalg.matrix_rank(zero_j*theta/np.maximum(1., abs(zero_y))[:, None], tol=1e-8))
    drag_rank = int(np.linalg.matrix_rank(normalized[::3], tol=1e-8))
    invariant = replace(aero, air_density_kgpm3=aero.air_density_kgpm3*1.1,
                        drag_area_m2=aero.drag_area_m2/1.1, downforce_area_m2=aero.downforce_area_m2/1.1)
    invariant_error = float(np.max(abs(oracle_observations(invariant)[0]-observed)))
    null_error = float(np.max(abs(normalized@np.array([1., -1., -1., 0, 0]))))
    return {"observation_truth": "SYNTHETIC_FORCE_SENSOR_ORACLE; NOT_PUBLIC_MEASUREMENTS", "parameter_order": list(FIELDS),
            "relative_parameter_jacobian_singular_values": singular.tolist(), "rank": rank, "parameters": 5,
            "fixed_density_rank": fixed_density_rank, "fixed_density_parameters": 4, "zero_tyre_force_rank": zero_rank,
            "drag_only_rank": drag_rank, "maximum_normalized_fd_error": error, "maximum_null_direction_error": null_error,
            "maximum_product_invariance_error_n": invariant_error, "real_parameters_identified": False,
            "passed": bool(rank == 4 and fixed_density_rank == 4 and zero_rank == 3 and drag_rank == 1
                           and error <= 1e-5 and null_error <= 1e-8 and invariant_error <= 1e-8)}
