import math
import tomllib
from pathlib import Path
from typing import TypeGuard

import numpy as np
import numpy.typing as npt

from .models import (
    AppConfig,
    CalculationResult,
    FrequencyConstantsConfig,
    LineConfig,
    MeasurementPoint,
    NormParamsConfig,
)
from .parser import load_spectrum_map


def is_str_dict(val: object) -> TypeGuard[dict[str, object]]:
    """Проверяет, что объект является словарём со строковыми ключами."""
    return isinstance(val, dict)


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
    """Безопасно валидирует TOML-конфиг через TypeGuard без Unknown и Any."""
    if not config_path.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
    with open(config_path, "rb") as f:
        raw_data: object = tomllib.load(f)

    if not is_str_dict(raw_data):
        raise ValueError("Некорректный формат config.toml")

    # 1. frequency_constants
    raw_freq = raw_data.get("frequency_constants")
    if not is_str_dict(raw_freq):
        raise ValueError("Секция [frequency_constants] отсутствует в config.toml")

    num_c = raw_freq.get("number_of_constants")
    n_consts = int(num_c) if isinstance(num_c, (int, float)) else 20

    freq_cfg = FrequencyConstantsConfig(
        number_of_constants=n_consts,
        f_i=_parse_float_list(raw_freq.get("f_i")),
        delta_f_i=_parse_float_list(raw_freq.get("delta_f_i")),
        delta_A_i=_parse_float_list(raw_freq.get("delta_A_i")),
    )

    # 2. norm_params_by_category
    raw_norm = raw_data.get("norm_params_by_category")
    if not is_str_dict(raw_norm):
        raise ValueError("Секция [norm_params_by_category] отсутствует в config.toml")

    norm_cfg = NormParamsConfig(
        delta_stn=_parse_float_list(raw_norm.get("delta_stn")),
        w_n=_parse_float_list(raw_norm.get("w_n")),
    )

    # 3. line
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

    # 4. operation_modes
    raw_modes = raw_data.get("operation_modes")
    modes_list = ["ХХ", "ДР", "РР"]
    if is_str_dict(raw_modes):
        parsed = _parse_str_list(raw_modes.get("modes"))
        if parsed:
            modes_list = parsed

    return AppConfig(
        frequency_constants=freq_cfg,
        norm_params=norm_cfg,
        lines=lines_cfg,
        operation_modes=modes_list,
    )


def _extract_spectrum_voltages(
    f_list: list[float],
    file_path: Path,
) -> list[float]:
    spectrum_map = load_spectrum_map(file_path)
    matched: list[float] = []
    missing: list[float] = []

    for f_val in f_list:
        key = int(round(f_val))
        if key in spectrum_map:
            matched.append(spectrum_map[key])
        else:
            missing.append(f_val)

    if missing:
        raise ValueError(f"В файле {file_path.name} отсутствуют частоты: {missing}")

    return matched


def calculate_data(
    file_sn_path: Path,
    file_n_path: Path,
    config_path: Path,
    category_index: int,
    line_type: str,
    r_param: float | None = None,
) -> CalculationResult:
    """Векторизованный расчёт с гарантированной строгой типизацией."""
    _ = (line_type, r_param)
    config = load_config(config_path)

    f_list = config.frequency_constants.f_i
    delta_f_list = config.frequency_constants.delta_f_i

    if len(f_list) != 20 or len(delta_f_list) != 20:
        raise ValueError("В frequency_constants f_i и delta_f_i должны содержать по 20 чисел!")

    if len(config.norm_params.delta_stn) <= category_index:
        raise ValueError(f"Категория {category_index + 1} отсутствует в delta_stn!")
    delta_stn_val = config.norm_params.delta_stn[category_index]

    u_sn_list = _extract_spectrum_voltages(f_list, file_sn_path)
    u_n_list = _extract_spectrum_voltages(f_list, file_n_path)

    # Векторизованный расчёт массивов на NumPy
    u_sn_arr: npt.NDArray[np.float64] = np.array(u_sn_list, dtype=np.float64)
    u_n_arr: npt.NDArray[np.float64] = np.array(u_n_list, dtype=np.float64)

    diff: npt.NDArray[np.float64] = u_sn_arr**2 - u_n_arr**2
    clipped_diff: npt.NDArray[np.float64] = np.maximum(0.0, diff)
    u_s_arr: npt.NDArray[np.float64] = np.sqrt(clipped_diff)

    factor: float = (2.66 * math.pow(math.e, 2.3)) / 5.34
    q_inner: npt.NDArray[np.float64] = np.maximum(0.0, 0.90 + factor * u_s_arr)
    q_arr: npt.NDArray[np.float64] = np.sqrt(q_inner)

    violations_arr: npt.NDArray[np.bool_] = q_arr >= delta_stn_val
    has_violations = bool(np.any(violations_arr))

    # Сборка точек без извлечения элементов из ndarray через индекс (исключает Any)
    points: list[MeasurementPoint] = []
    for idx in range(20):
        f_val = f_list[idx]
        delta_f_val = delta_f_list[idx]
        u_sn_val = u_sn_list[idx]
        u_n_val = u_n_list[idx]

        diff_val = u_sn_val**2 - u_n_val**2
        u_s_val = math.sqrt(diff_val) if diff_val > 0.0 else 0.0
        q_inner_val = 0.90 + factor * u_s_val
        q_val = math.sqrt(q_inner_val) if q_inner_val > 0.0 else 0.0
        is_viol = q_val >= delta_stn_val

        points.append(
            MeasurementPoint(
                index=idx + 1,
                delta_f=round(delta_f_val, 4),
                f=round(f_val, 4),
                u_sn=round(u_sn_val, 4),
                u_n=round(u_n_val, 4),
                u_s=round(u_s_val, 4),
                q=round(q_val, 4),
                is_violation=is_viol,
            )
        )

    return CalculationResult(points=points, has_violations=has_violations)
