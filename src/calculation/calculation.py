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


def _calculate_voltage_point(
    index: int,
    delta_f: float,
    frequency: float,
    delta_a: float,
    norm_noise: float,
    u_sn: float,
    u_n: float,
    delta_stn: float,
    resistance: float | None,
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
    resistance: float | None,
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
    )


def _validate_inputs(
    config: AppConfig,
    category_index: int,
    line_type: LineType,
) -> tuple[list[float], list[float], list[float], list[float], float]:
    line_noise = _select_line_noise(config, line_type)
    if len(line_noise) != FREQUENCY_COUNT:
        raise ValueError("В конфигурации нормированный шум должен содержать ровно 20 значений!")

    frequencies = config.frequency_constants.f_i
    delta_frequencies = config.frequency_constants.delta_f_i
    delta_a_values = config.frequency_constants.delta_a_i
    if (
        len(frequencies) != FREQUENCY_COUNT
        or len(delta_frequencies) != FREQUENCY_COUNT
        or len(delta_a_values) != FREQUENCY_COUNT
    ):
        raise ValueError("Константы частот должны содержать по 20 значений!")

    delta_stn = config.norm_params.delta_stn
    if not 0 <= category_index < len(delta_stn):
        raise ValueError(f"Категория {category_index + 1} отсутствует в delta_stn!")

    return frequencies, delta_frequencies, delta_a_values, line_noise, delta_stn[category_index]


def calculate_voltage(
    signal_noise_path: Path,
    noise_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    resistance: float | None = None,
) -> CalculationResult:
    frequencies, delta_f_vals, delta_a_vals, line_noise, delta_stn = _validate_inputs(
        config, category_index, line_type
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
            resistance=resistance,
        )
        for i in range(FREQUENCY_COUNT)
    ]
    return CalculationResult(
        points=points,
        has_violations=any(point.is_violation for point in points),
        measurement_type="voltage",
    )


def calculate_current(
    signal_noise_path: Path,
    noise_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    resistance: float | None = None,
) -> CalculationResult:
    frequencies, delta_f_vals, delta_a_vals, line_noise, delta_stn = _validate_inputs(
        config, category_index, line_type
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
            resistance=resistance,
        )
        for i in range(FREQUENCY_COUNT)
    ]
    return CalculationResult(
        points=points,
        has_violations=any(point.is_violation for point in points),
        measurement_type="current",
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
