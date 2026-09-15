import math
from pathlib import Path

from calculation.calculator_current import calculate_current_q
from calculation.calculator_voltage import calculate_voltage_q
from calculation.models import (
    AppConfig,
    CalculationResult,
    LineType,
    MeasurementKind,
    MeasurementPoint,
)
from spectrum_io.spectrum_reader import read_required_frequencies

FREQUENCY_COUNT = 20


def _select_line_noise(config: AppConfig, line_type: LineType) -> list[float]:
    match line_type:
        case "symmetrical":
            return config.norm_noise_by_line.symmetrical
        case "asymmetrical":
            return config.norm_noise_by_line.asymmetrical
        case "power":
            return config.norm_noise_by_line.power


def _compute_signal_level(signal_noise: float, noise: float) -> float:
    """Shared difference-of-squares step for both Voltage and Current."""
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


def _calculate_voltage_point(
    index: int,
    delta_f: float,
    frequency: float,
    delta_a: float,
    norm_noise: float,
    u_sn: float,
    u_n: float,
    delta_stn: float,
    resistance: float,
) -> MeasurementPoint:
    u_s = _compute_signal_level(u_sn, u_n)
    q = calculate_voltage_q(
        u_s=u_s,
        frequency=frequency,
        delta_f=delta_f,
        delta_a=delta_a,
        norm_noise=norm_noise,
        resistance=resistance,
    )
    return MeasurementPoint(
        index=index,
        delta_f=round(delta_f, 4),
        f=round(frequency, 4),
        u_sn=round(u_sn, 4),
        u_n=round(u_n, 4),
        u_s=round(u_s, 4),
        q=round(q, 4),
        is_violation=q >= delta_stn,
        r_i=None,
    )


def _calculate_current_point(
    index: int,
    delta_f: float,
    frequency: float,
    delta_a: float,
    norm_noise: float,
    i_sn: float,
    i_n: float,
    delta_stn: float,
    resistance: float,
) -> MeasurementPoint:
    i_s = _compute_signal_level(i_sn, i_n)
    q = calculate_current_q(
        i_s=i_s,
        frequency=frequency,
        delta_f=delta_f,
        delta_a=delta_a,
        norm_noise=norm_noise,
        resistance=resistance,
    )
    return MeasurementPoint(
        index=index,
        delta_f=round(delta_f, 4),
        f=round(frequency, 4),
        u_sn=round(i_sn, 4),
        u_n=round(i_n, 4),
        u_s=round(i_s, 4),
        q=round(q, 4),
        is_violation=q >= delta_stn,
        r_i=None,
    )


def _validate_inputs(
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    resistance: float | None,
) -> tuple[list[float], list[float], list[float], list[float], float, float, float]:
    if resistance is None or resistance <= 0.0:
        raise ValueError("Параметр сопротивления R должен быть больше нуля.")

    line_noise = _select_line_noise(config, line_type)
    if len(line_noise) != FREQUENCY_COUNT:
        raise ValueError("В конфигурации нормированный шум должен содержать ровно 20 значений.")

    frequencies = config.frequency_constants.f_i
    delta_frequencies = config.frequency_constants.delta_f_i
    delta_a_values = config.frequency_constants.delta_a_i
    if (
        len(frequencies) != FREQUENCY_COUNT
        or len(delta_frequencies) != FREQUENCY_COUNT
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
        delta_a_values,
        line_noise,
        delta_stn[category_index],
        w_n_values[category_index],
        resistance,
    )


def _finalize_result(
    points: list[MeasurementPoint],
    delta_a_vals: list[float],
    measurement_type: MeasurementKind,
    resistance: float,
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
    r_i_sum = 0.0
    for idx, point in enumerate(points):
        r_i = _compute_point_r_i(
            q=point.q,
            delta_a=delta_a_vals[idx],
            frequency=point.f,
        )
        r_i_sum += r_i
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

    if measurement_type == "voltage":
        w_raw = r_i_sum / resistance
    else:
        w_raw = r_i_sum * resistance

    w_total = round(w_raw, 4)
    return CalculationResult(
        points=updated_points,
        has_violations=True,
        measurement_type=measurement_type,
        w=w_total,
        w_n=w_n,
        is_w_violation=w_total >= w_n,
    )


def calculate_voltage(
    signal_noise_path: Path,
    noise_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    resistance: float | None = None,
) -> CalculationResult:
    frequencies, delta_f_vals, delta_a_vals, line_noise, delta_stn, w_n, valid_r = _validate_inputs(
        config, category_index, line_type, resistance
    )
    u_sn_values = read_required_frequencies(signal_noise_path, frequencies)
    u_n_values = read_required_frequencies(noise_path, frequencies)

    points = [
        _calculate_voltage_point(
            index=i + 1,
            delta_f=delta_f_vals[i],
            frequency=frequencies[i],
            delta_a=delta_a_vals[i],
            norm_noise=line_noise[i],
            u_sn=u_sn_values[i],
            u_n=u_n_values[i],
            delta_stn=delta_stn,
            resistance=valid_r,
        )
        for i in range(FREQUENCY_COUNT)
    ]
    return _finalize_result(points, delta_a_vals, "voltage", valid_r, w_n)


def calculate_current(
    signal_noise_path: Path,
    noise_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    resistance: float | None = None,
) -> CalculationResult:
    frequencies, delta_f_vals, delta_a_vals, line_noise, delta_stn, w_n, valid_r = _validate_inputs(
        config, category_index, line_type, resistance
    )
    i_sn_values = read_required_frequencies(signal_noise_path, frequencies)
    i_n_values = read_required_frequencies(noise_path, frequencies)

    points = [
        _calculate_current_point(
            index=i + 1,
            delta_f=delta_f_vals[i],
            frequency=frequencies[i],
            delta_a=delta_a_vals[i],
            norm_noise=line_noise[i],
            i_sn=i_sn_values[i],
            i_n=i_n_values[i],
            delta_stn=delta_stn,
            resistance=valid_r,
        )
        for i in range(FREQUENCY_COUNT)
    ]
    return _finalize_result(points, delta_a_vals, "current", valid_r, w_n)


def calculate(
    signal_noise_path: Path,
    noise_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    measurement_type: MeasurementKind = "voltage",
    resistance: float | None = None,
) -> CalculationResult:
    match measurement_type:
        case "voltage":
            return calculate_voltage(
                signal_noise_path=signal_noise_path,
                noise_path=noise_path,
                config=config,
                category_index=category_index,
                line_type=line_type,
                resistance=resistance,
            )
        case "current":
            return calculate_current(
                signal_noise_path=signal_noise_path,
                noise_path=noise_path,
                config=config,
                category_index=category_index,
                line_type=line_type,
                resistance=resistance,
            )
