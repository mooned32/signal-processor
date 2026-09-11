import math
import tomllib
from pathlib import Path
from typing import TypeGuard, cast

from .models import (
    AppConfig,
    CalculationResult,
    FrequencyConstantsConfig,
    LineConfig,
    LineType,
    MeasurementPoint,
    NormNoiseByLineConfig,
    NormParamsConfig,
)
from .parser import load_spectrum_values


def is_str_dict(val: object) -> TypeGuard[dict[str, object]]:
    """Проверяет, что объект является словарём со строковыми ключами."""
    if not isinstance(val, dict):
        return False
    raw_dict = cast(dict[object, object], val)
    return all(isinstance(key, str) for key in raw_dict)


def is_object_list(val: object) -> TypeGuard[list[object]]:
    """Проверяет, что объект является списком."""
    return isinstance(val, list)


def _parse_float_list(raw: object) -> list[float]:
    if not is_object_list(raw):
        return []
    result: list[float] = []
    for item in raw:
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            result.append(float(item))
    return result


def _parse_str_list(raw: object) -> list[str]:
    if not is_object_list(raw):
        return []
    return [item for item in raw if isinstance(item, str)]


def _get_mapping(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key)
    if not is_str_dict(value):
        raise ValueError(f"Секция [{key}] отсутствует или имеет некорректный формат")
    return value


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")

    with config_path.open("rb") as config_file:
        raw_data: object = tomllib.load(config_file)

    if not is_str_dict(raw_data):
        raise ValueError("Некорректный формат config.toml")

    raw_freq = _get_mapping(raw_data, "frequency_constants")
    number_of_constants = raw_freq.get("number_of_constants")
    if not isinstance(number_of_constants, (int, float)) or isinstance(number_of_constants, bool):
        number_of_constants = 20

    freq_cfg = FrequencyConstantsConfig(
        number_of_constants=int(number_of_constants),
        f_i=_parse_float_list(raw_freq.get("f_i")),
        delta_f_i=_parse_float_list(raw_freq.get("delta_f_i")),
        delta_A_i=_parse_float_list(raw_freq.get("delta_A_i")),
    )

    raw_norm = _get_mapping(raw_data, "norm_params_by_category")
    norm_cfg = NormParamsConfig(
        delta_stn=_parse_float_list(raw_norm.get("delta_stn")),
        w_n=_parse_float_list(raw_norm.get("w_n")),
    )

    raw_noise = _get_mapping(raw_data, "norm_noise_by_line")
    raw_sym = _get_mapping(raw_noise, "symmetrical")
    raw_asym = _get_mapping(raw_noise, "asymmetrical")
    raw_power = _get_mapping(raw_noise, "power")

    sym_noise = _parse_float_list(raw_sym.get("values"))
    asym_noise = _parse_float_list(raw_asym.get("values"))
    power_noise = _parse_float_list(raw_power.get("values"))
    if not all(len(values) == 20 for values in (sym_noise, asym_noise, power_noise)):
        raise ValueError(
            "В [norm_noise_by_line] списки values должны содержать ровно по 20 значений!"
        )

    norm_noise_cfg = NormNoiseByLineConfig(
        symmetrical=sym_noise,
        asymmetrical=asym_noise,
        power=power_noise,
    )

    raw_line = raw_data.get("line")
    if not is_str_dict(raw_line):
        raw_line = {}

    def parse_line_names(line_type: LineType) -> list[str]:
        raw_line_type = raw_line.get(line_type)
        if not is_str_dict(raw_line_type):
            return []
        return _parse_str_list(raw_line_type.get("names"))

    lines_cfg = LineConfig(
        symmetrical=parse_line_names("symmetrical"),
        asymmetrical=parse_line_names("asymmetrical"),
        power=parse_line_names("power"),
    )

    raw_modes = raw_data.get("operation_modes")
    modes = _parse_str_list(raw_modes.get("modes")) if is_str_dict(raw_modes) else []
    if not modes:
        modes = ["ХХ", "ДР", "РР"]

    return AppConfig(
        frequency_constants=freq_cfg,
        norm_params=norm_cfg,
        norm_noise_by_line=norm_noise_cfg,
        lines=lines_cfg,
        operation_modes=modes,
    )


def _extract_spectrum_voltages(
    f_list: list[float],
    file_path: Path,
) -> list[float]:
    requested = {int(round(frequency)) for frequency in f_list}
    spectrum_values = load_spectrum_values(file_path, requested)

    matched: list[float] = []
    missing: list[float] = []
    for frequency in f_list:
        key = int(round(frequency))
        value = spectrum_values.get(key)
        if value is None:
            missing.append(frequency)
        else:
            matched.append(value)

    if missing:
        raise ValueError(f"В файле {file_path.name} отсутствуют частоты: {missing}")
    return matched


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
    u_s_squared = u_sn**2 - u_n**2
    u_s = math.sqrt(u_s_squared) if u_s_squared > 0.0 else 0.0
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


def calculate_data(
    file_sn_path: Path,
    file_n_path: Path,
    config: AppConfig,
    category_index: int,
    line_type: LineType,
    r_param: float | None = None,
) -> CalculationResult:
    """Выполняет расчёт по двум спектрам и типизированной конфигурации."""
    _ = r_param
    line_noise = _select_line_noise(config, line_type)
    if len(line_noise) != 20:
        raise ValueError("В конфигурации нормированный шум должен содержать ровно 20 значений!")

    f_list = config.frequency_constants.f_i
    delta_f_list = config.frequency_constants.delta_f_i
    if len(f_list) != 20 or len(delta_f_list) != 20:
        raise ValueError("В frequency_constants f_i и delta_f_i должны содержать по 20 чисел!")

    delta_stn_list = config.norm_params.delta_stn
    if not 0 <= category_index < len(delta_stn_list):
        raise ValueError(f"Категория {category_index + 1} отсутствует в delta_stn!")
    delta_stn_value = delta_stn_list[category_index]

    u_sn_list = _extract_spectrum_voltages(f_list, file_sn_path)
    u_n_list = _extract_spectrum_voltages(f_list, file_n_path)

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
            zip(delta_f_list, f_list, u_sn_list, u_n_list, strict=True)
        )
    ]

    return CalculationResult(
        points=points,
        has_violations=any(point.is_violation for point in points),
    )
