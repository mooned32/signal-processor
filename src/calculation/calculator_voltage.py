"""Pipeline for voltage (U) calculation."""

import math


def calculate_voltage_q(
    u_s: float,
    frequency: float,
    delta_f: float,
    delta_a: float,
    norm_noise: float,
    resistance: float | None = None,
) -> float:
    """Calculate q for voltage from U_s, norm noise, and frequency constants."""
    del frequency, delta_f, delta_a, norm_noise, resistance

    # Intermediate calculation pipeline for Voltage
    exponent_term = math.exp(2.3)
    voltage_factor = (2.66 * exponent_term) / 5.34
    q_inner = 0.90 + voltage_factor * u_s

    if q_inner <= 0.0:
        return 0.0
    return math.sqrt(q_inner)
