import math
from pathlib import Path

from calculation.models import AppConfig, CalculationResult, LineType, MeasurementPoint
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


def _calculate_point(
    index: int,
    delta_f: float,
    frequency: float,
    u_sn: float,
    u_n: float,
    delta_stn: float,
) -> MeasurementPoint:
    signal_power = u_sn**2 - u_n**2
    u_s = math.sqrt(signal_power) if signal_power > 0.0 else 0.0
    factor = (2.66 * math.exp(2.3)) / 5.34
    q_inner = 0.90 + factor * u_s
    q = math.sqrt(q_inner) if q_inner > 0.0 else 0.0

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


def calculate(
    signal_noise_path: Path,
    noise_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
) -> CalculationResult:
    line_noise = _select_line_noise(config, line_type)
    if len(line_noise) != FREQUENCY_COUNT:
        raise ValueError("В конфигурации нормированный шум должен содержать ровно 20 значений!")

    frequencies = config.frequency_constants.f_i
    delta_frequencies = config.frequency_constants.delta_f_i
    if len(frequencies) != FREQUENCY_COUNT or len(delta_frequencies) != FREQUENCY_COUNT:
        raise ValueError("В frequency_constants f_i и delta_f_i должны содержать по 20 чисел!")

    delta_stn = config.norm_params.delta_stn
    if not 0 <= category_index < len(delta_stn):
        raise ValueError(f"Категория {category_index + 1} отсутствует в delta_stn!")

    u_sn_values = read_required_frequencies(signal_noise_path, frequencies)
    u_n_values = read_required_frequencies(noise_path, frequencies)
    delta_stn_value = delta_stn[category_index]

    points = [
        _calculate_point(
            index=index + 1,
            delta_f=delta_f,
            frequency=frequency,
            u_sn=u_sn,
            u_n=u_n,
            delta_stn=delta_stn_value,
        )
        for index, (delta_f, frequency, u_sn, u_n) in enumerate(
            zip(delta_frequencies, frequencies, u_sn_values, u_n_values, strict=True)
        )
    ]

    return CalculationResult(
        points=points,
        has_violations=any(point.is_violation for point in points),
    )
