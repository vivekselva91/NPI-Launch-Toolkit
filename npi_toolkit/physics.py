"""First-principles checks used during the launch.

Each function is a back-of-envelope model, not a substitute for test data.
Default values are representative, not product-specific.
"""
from __future__ import annotations

import math


# --- Snap-fit clip strain -------------------------------------------------
def cantilever_snap_strain(deflection_mm: float, thickness_mm: float, length_mm: float) -> float:
    """Max strain of a constant-section cantilever snap: e = 1.5 * y * t / L^2."""
    return 1.5 * deflection_mm * thickness_mm / length_mm ** 2


def snap_margin(deflection_mm: float, thickness_mm: float, length_mm: float,
                allowable_strain: float = 0.025, kt: float = 1.0) -> float:
    """Ratio of allowable to applied strain (>1 = passes). kt = stress concentration."""
    return allowable_strain / (cantilever_snap_strain(deflection_mm, thickness_mm, length_mm) * kt)


# --- Tolerance stack-up ---------------------------------------------------
def worst_case(contributors: list[float]) -> float:
    return sum(abs(c) for c in contributors)


def rss(contributors: list[float]) -> float:
    """Root-sum-square. Assumes independent, centered, normal contributors."""
    return math.sqrt(sum(c * c for c in contributors))


# --- LED calibration timing -------------------------------------------------
def led_flux_drift(delta_t_k: float, coeff_per_k: float = -0.008) -> float:
    """Fractional light-output change for a junction temperature rise.

    Red AlInGaP LEDs are roughly -0.5 to -1 %/K; InGaN green/blue much less.
    """
    return coeff_per_k * delta_t_k


def integration_time_s(relative_brightness: float, t_full_s: float = 0.2) -> float:
    """For equal signal-to-noise, integration time scales ~ 1 / brightness."""
    return t_full_s / relative_brightness


def thermal_time_constant_s(mass_kg: float, c_j_per_kgk: float, h_w_m2k: float, area_m2: float) -> float:
    """Lumped-capacitance tau = m c / (h A)."""
    return mass_kg * c_j_per_kgk / (h_w_m2k * area_m2)


def time_to_settle_s(tau_s: float, start_delta_k: float, target_delta_k: float) -> float:
    return tau_s * math.log(start_delta_k / target_delta_k)


# --- Little's Law ----------------------------------------------------------
def wip_units(throughput_per_s: float, time_in_process_s: float) -> float:
    """WIP = throughput x time in process (ovens, soaks, buffers)."""
    return throughput_per_s * time_in_process_s
