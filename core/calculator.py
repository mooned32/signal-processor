import math
import tomllib
from pathlib import Path
from typing import Literal, TypeGuard

from .models import (
    AppConfig,
    CalculationResult,
    FrequencyConstantsConfig,
    LineConfig,
    MeasurementPoint,
    NormNoiseByLineConfig,
    NormParamsConfig,
)
from .parser import load_spectrum_values

LineType = Literal["symmetrical", "asymmetrical", "power"]
EXPECTED_POINT_COUNT = 20


def is_str_dict(val: object) -> TypeGuard[dict[str, object]]:
    """Проверяет, что объект является словарём со строковыми ключами."""
    return isinstance(val, dict) and all(isinstance(key, str) for key in val)


def is_object_list(val: object) -> TypeGuard[list[object]]:
    """Проверяет, что объект является списком."""
    return isinstance(val, list)


def _parse_float_list(raw: object) -> list[float]:
    if not is_object_list(raw):
        return []

    result: list[float] = []
    for item in raw:
        if isinstance(item, (int, float)):
            result.append(float(item))
    return result


def _parse_str_list(raw: object) -> list[str]:
    if not is_object_list(raw):
        return []

    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
    return result


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")

    with config_path.open("rb") as file:
        raw_data: object = tomllib.load(file)

    if not is_str_dict(raw_data):
        raise ValueError("Некорректный формат config.toml")

    raw_freq = raw_data.get("frequency_constants")
    if not is_str_dict(raw_freq):
        raise ValueError("Секция [frequency_constants] отсутствует в config.toml")

    num_c = raw_freq.get("number_of_constants")
    freq_cfg = FrequencyConstantsConfig(
        number_of_constants=int(num_c) if isinstance(num_c, (int, float)) else EXPECTED_POINT_COUNT,
        f_i=_parse_float_list(raw_freq.get("f_i")),
        delta_f_i=_parse_float_list(raw_freq.get("delta_f_i")),
        delta_A_i=_parse_float_list(raw_freq.get("delta_A_i")),
    )

    raw_norm = raw_data.get("norm_params_by_category")
    if not is_str_dict(raw_norm):
        raise ValueError("Секция [norm_params_by_category] отсутствует в config.toml")

    norm_cfg = NormParamsConfig(
        delta_stn=_parse_float_list(raw_norm.get("delta_stn")),
        w_n=_parse_float_list(raw_norm.get("w_n")),
    )

    raw_noise = raw_data.get("norm_noise_by_line")
    if not is_str_dict(raw_noise):
        raise ValueError("Секция [norm_noise_by_line] отсутствует в config.toml")

    sym_noise = raw_noise.get("symmetrical")
    asym_noise = raw_noise.get("asymmetrical")
    pwr_noise = raw_noise.get("power")

    if not is_str_dict(sym_noise) or not is_str_dict(asym_noise) or not is_str_dict(pwr_noise):
        raise ValueError(
            "В [norm_noise_by_line] должны быть секции symmetrical, asymmetrical и power"
        )

    sym_noise_vals = _parse_float_list(sym_noise.get("values"))
    asym_noise_vals = _parse_float_list(asym_noise.get("values"))
    pwr_noise_vals = _parse_float_list(pwr_noise.get("values"))

    if (
        len(sym_noise_vals) != EXPECTED_POINT_COUNT
        or len(asym_noise_vals) != EXPECTED_POINT_COUNT
        or len(pwr_noise_vals) != EXPECTED_POINT_COUNT
    ):
        raise ValueError(
            "В [norm_noise_by_line] списки values должны содержать ровно "
            f"по {EXPECTED_POINT_COUNT} значений!"
        )

    norm_noise_cfg = NormNoiseByLineConfig(
        symmetrical=sym_noise_vals,
        asymmetrical=asym_noise_vals,
        power=pwr_noise_vals,
    )

    raw_line = raw_data.get("line")
    sym_names: list[str] = []
    asym_names: list[str] = []
    pwr_names: list[str] = []

    if is_str_dict(raw_line):
        sym = raw_line.get("symmetrical")
        if is_str_dict(sym):
            sym_names = _parse_str_list(sym.get("names"))
        asym = raw_line.get("asymmetrical")
        if is_str_dict(asym):
            asym_names = _parse_str_list(asym.get("names"))
        pwr = raw_line.get("power")
        if is_str_dict(pwr):
            pwr_names = _parse_str_list(pwr.get("names"))

    lines_cfg = LineConfig(
        symmetrical=sym_names,
        asymmetrical=asym_names,
        power=pwr_names,
    )

    raw_modes = raw_data.get("operation_modes")
    modes_list = ["ХХ", "ДР", "РР"]
    if is_str_dict(raw_modes):
        parsed = _parse_str_list(raw_modes.get("modes"))
        if parsed:
            modes_list = parsed

    return AppConfig(
        frequency_constants=freq_cfg,
        norm_params=norm_cfg,
        norm_noise_by_line=norm_noise_cfg,
        lines=lines_cfg,
        operation_modes=modes_list,
    )


def _validate_config_for_calculation(config: AppConfig, category_index: int) -> None:
    frequency_count = len(config.frequency_constants.f_i)
    delta_frequency_count = len(config.frequency_constants.delta_f_i)
    if frequency_count != EXPECTED_POINT_COUNT or delta_frequency_count != EXPECTED_POINT_COUNT:
        raise ValueError(
            "В frequency_constants f_i и delta_f_i должны содержать ровно "
            f"по {EXPECTED_POINT_COUNT} чисел!"
        )

    if not 0 <= category_index < len(config.norm_params.delta_stn):
        raise ValueError(f"Категория {category_index + 1} отсутствует в delta_stn!")


def _extract_spectrum_voltages(
    frequencies: list[float],
    file_path: Path,
) -> list[float]:
    required_frequencies = {int(round(frequency)) for frequency in frequencies}
    spectrum = load_spectrum_values(file_path, required_frequencies)
    return [spectrum[int(round(frequency))] for frequency in frequencies]


def _calculate_point(
    index: int,
    f_value: float,
    delta_f: float,
    u_sn: float,
    u_n: float,
    delta_stn: float,
    factor: float,
) -> MeasurementPoint:
    # Математика намеренно остаётся на Python float/math: промежуточного
    # округления нет, округляются только значения, сохраняемые в результате.
    diff = u_sn * u_sn - u_n * u_n
    u_s = math.sqrt(diff) if diff > 0.0 else 0.0

    q_inner = 0.90 + factor * u_s
    q = math.sqrt(q_inner) if q_inner > 0.0 else 0.0

    return MeasurementPoint(
        index=index,
        delta_f=round(delta_f, 4),
        f=round(f_value, 4),
        u_sn=round(u_sn, 4),
        u_n=round(u_n, 4),
        u_s=round(u_s, 4),
        q=round(q, 4),
        is_violation=q >= delta_stn,
    )


def calculate_data(
    file_sn_path: Path,
    file_n_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    r_param: float | None = None,
) -> CalculationResult:
    """Рассчитывает параметры по двум спектрам без сторонних численных библиотек."""
    _ = r_param
    _validate_config_for_calculation(config, category_index)

    f_list = config.frequency_constants.f_i
    delta_f_list = config.frequency_constants.delta_f_i
    delta_stn = config.norm_params.delta_stn[category_index]

    # Проверка типа линии сохраняется, хотя соответствующая нормированная
    # таблица пока не участвует в формуле расчёта.
    if line_type not in {"symmetrical", "asymmetrical", "power"}:
        raise ValueError(f"Неизвестный тип линии: {line_type}")

    u_sn_list = _extract_spectrum_voltages(f_list, file_sn_path)
    u_n_list = _extract_spectrum_voltages(f_list, file_n_path)

    factor = (2.66 * math.pow(math.e, 2.3)) / 5.34
    points: list[MeasurementPoint] = []

    for index, (f_value, delta_f, u_sn, u_n) in enumerate(
        zip(f_list, delta_f_list, u_sn_list, u_n_list, strict=True),
        start=1,
    ):
        points.append(
            _calculate_point(
                index=index,
                f_value=f_value,
                delta_f=delta_f,
                u_sn=u_sn,
                u_n=u_n,
                delta_stn=delta_stn,
                factor=factor,
            )
        )

    has_violations = any(point.is_violation for point in points)
    return CalculationResult(points=points, has_violations=has_violations)
