"""Shared geometric query contract; it does not authorize simulator promotion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class GeometrySample:
    station_m: float
    x_m: float
    y_m: float
    heading_rad: float
    curvature_1pm: float
    truth_label: str

    @property
    def tangent(self) -> np.ndarray:
        return np.array([np.cos(self.heading_rad), np.sin(self.heading_rad)])

    @property
    def left_normal(self) -> np.ndarray:
        return np.array([-np.sin(self.heading_rad), np.cos(self.heading_rad)])


@runtime_checkable
class GeometryProvider(Protocol):
    @property
    def length_m(self) -> float: ...

    def sample_geometry(self, distance_m: float) -> GeometrySample: ...
