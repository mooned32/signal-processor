import math
from pathlib import Path

from models import (
    AppConfig,
    CalculationResult,
    LineType,
    MeasurementKind,
    MeasurementPoint,
)
from spectrum_reader import read_required_frequencies

FREQUENCY_COUNT = 20


def calculate_intermediate_u(norm_noise: float, line_type: LineType) -> float:
    """Interface function to calculate intermediate U based on line type."""
    match line_type:
        case "symmetrical" | "asymmetrical":
            return norm_noise
        case "power":
            return norm_noise


def calculate_q(
    signal_level: float,
    intermediate_u: float,
    measurement_type: MeasurementKind,
    resistance: float,
) -> float:
    """Calculate q_i: (i_c * r) / u for current or u_c / u for voltage."""
    if intermediate_u <= 0.0:
        return 0.0
    if measurement_type == "current":
        return (signal_level * resistance) / intermediate_u
    return signal_level / intermediate_u


def calculate_w(r_sum: float) -> float:
    """Interface function to calculate total power W from R = sum(r_i * k_i)."""
    return r_sum


def _select_line_noise(config: AppConfig, line_type: LineType) -> list[float]:
    match line_type:
        case "symmetrical":
            return config.norm_noise_by_line.symmetrical
        case "asymmetrical":
            return config.norm_noise_by_line.asymmetrical
        case "power":
            return config.norm_noise_by_line.power


def _compute_signal_level(signal_noise: float, noise: float) -> float:
    """Calculate signal level: sqrt(sn^2 - n^2)."""
    signal_power = signal_noise**2 - noise**2
    if signal_power <= 0.0:
        return 0.0
    return math.sqrt(signal_power)


def _compute_point_r_i(
    q: float,
    delta_a: float,
    frequency: float,
) -> float:
    """Calculate intermediate variable r_i using natural logarithm."""
    log_factor = math.log(1.0 + frequency)
    scaled_q = q * delta_a
    r_i = (scaled_q**2) * log_factor
    return round(r_i, 4)


def _validate_inputs(
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    resistance: float | None,
) -> tuple[list[float], list[float], list[float], list[float], list[float], float, float, float]:
    if resistance is None or resistance <= 0.0:
        raise ValueError("Параметр сопротивления R должен быть больше нуля.")

    line_noise = _select_line_noise(config, line_type)
    if len(line_noise) != FREQUENCY_COUNT:
        raise ValueError("В конфигурации нормированный шум должен содержать ровно 20 значений.")

    frequencies = config.frequency_constants.f_i
    delta_frequencies = config.frequency_constants.delta_f_i
    k_values = config.frequency_constants.k_i
    delta_a_values = config.frequency_constants.delta_a_i
    if (
        len(frequencies) != FREQUENCY_COUNT
        or len(delta_frequencies) != FREQUENCY_COUNT
        or len(k_values) != FREQUENCY_COUNT
        or len(delta_a_values) != FREQUENCY_COUNT
    ):
        raise ValueError("Константы частот должны содержать по 20 значений.")

    delta_stn = config.norm_params.delta_stn
    w_n_values = config.norm_params.w_n
    if not (0 <= category_index < len(delta_stn) and 0 <= category_index < len(w_n_values)):
        raise ValueError(f"Категория {category_index + 1} отсутствует в параметрах нормы.")

    return (
        frequencies,
        delta_frequencies,
        k_values,
        delta_a_values,
        line_noise,
        delta_stn[category_index],
        w_n_values[category_index],
        resistance,
    )


def _finalize_result(
    points: list[MeasurementPoint],
    delta_a_vals: list[float],
    k_vals: list[float],
    measurement_type: MeasurementKind,
    w_n: float,
) -> CalculationResult:
    has_violations = any(point.is_violation for point in points)
    if not has_violations:
        return CalculationResult(
            points=points,
            has_violations=False,
            measurement_type=measurement_type,
            w=None,
            w_n=None,
            is_w_violation=None,
        )

    updated_points: list[MeasurementPoint] = []
    r_weighted_sum = 0.0
    for idx, point in enumerate(points):
        r_i = _compute_point_r_i(
            q=point.q,
            delta_a=delta_a_vals[idx],
            frequency=point.f,
        )
        r_weighted_sum += r_i * k_vals[idx]
        updated_points.append(
            MeasurementPoint(
                index=point.index,
                delta_f=point.delta_f,
                f=point.f,
                u_sn=point.u_sn,
                u_n=point.u_n,
                u_s=point.u_s,
                q=point.q,
                is_violation=point.is_violation,
                r_i=r_i,
            )
        )

    w_total = round(calculate_w(r_weighted_sum), 4)
    return CalculationResult(
        points=updated_points,
        has_violations=True,
        measurement_type=measurement_type,
        w=w_total,
        w_n=w_n,
        is_w_violation=w_total >= w_n,
    )


def calculate(
    signal_noise_path: Path,
    noise_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    measurement_type: MeasurementKind = "voltage",
    resistance: float | None = None,
) -> CalculationResult:
    frequencies, delta_f_vals, k_vals, delta_a_vals, line_noise, delta_stn, w_n, valid_r = (
        _validate_inputs(config, category_index, line_type, resistance)
    )
    sn_values = read_required_frequencies(signal_noise_path, frequencies)
    n_values = read_required_frequencies(noise_path, frequencies)

    points: list[MeasurementPoint] = []
    for i in range(FREQUENCY_COUNT):
        signal_level = _compute_signal_level(sn_values[i], n_values[i])
        intermediate_u = calculate_intermediate_u(line_noise[i], line_type)
        q = calculate_q(signal_level, intermediate_u, measurement_type, valid_r)
        points.append(
            MeasurementPoint(
                index=i + 1,
                delta_f=round(delta_f_vals[i], 4),
                f=round(frequencies[i], 4),
                u_sn=round(sn_values[i], 4),
                u_n=round(n_values[i], 4),
                u_s=round(signal_level, 4),
                q=round(q, 4),
                is_violation=q >= delta_stn,
                r_i=None,
            )
        )

    return _finalize_result(points, delta_a_vals, k_vals, measurement_type, w_n)
