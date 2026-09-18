import tomllib
from pathlib import Path
from typing import cast

from error import ConfigNotFoundError, ConfigValidationError
from models import (
    AppConfig,
    FrequencyConstantsConfig,
    LineConfig,
    NormNoiseByLineConfig,
    NormParamsConfig,
)


def _require_dict(value: object, section: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigValidationError(f"Секция [{section}] отсутствует или имеет некорректный формат")
    return cast(dict[str, object], value)


def _float_list(value: object, key: str) -> list[float]:
    if not isinstance(value, list):
        raise ConfigValidationError(f"Параметр '{key}' должен быть списком чисел.")
    items = cast(list[object], value)
    result: list[float] = []
    for item in items:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ConfigValidationError(f"Параметр '{key}' содержит нечисловое значение.")
        result.append(float(item))
    return result


def _string_list(value: object, key: str) -> list[str]:
    if not isinstance(value, list):
        raise ConfigValidationError(f"Параметр '{key}' должен быть списком строк.")
    items = cast(list[object], value)
    result: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise ConfigValidationError(f"Параметр '{key}' содержит нестроковое значение.")
        result.append(item)
    return result


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        raise ConfigNotFoundError(str(config_path))

    try:
        with config_path.open("rb") as config_file:
            raw_data: object = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as err:
        raise ConfigValidationError(
            f"Синтаксическая ошибка в конфигурационном файле: {err}"
        ) from err
    except OSError as err:
        raise ConfigValidationError(f"Не удалось прочитать конфигурационный файл: {err}") from err

    raw_dict = _require_dict(raw_data, "root")

    frequency_raw = _require_dict(raw_dict.get("frequency_constants"), "frequency_constants")
    number_of_constants = frequency_raw.get("number_of_constants")
    if isinstance(number_of_constants, bool) or not isinstance(number_of_constants, int):
        raise ConfigValidationError("Параметр 'number_of_constants' должен быть целым числом.")
    if number_of_constants <= 0:
        raise ConfigValidationError("Параметр 'number_of_constants' должен быть больше нуля.")

    frequency_config = FrequencyConstantsConfig(
        number_of_constants=number_of_constants,
        f_i=_float_list(frequency_raw.get("f_i"), "f_i"),
        delta_f_i=_float_list(frequency_raw.get("delta_f_i"), "delta_f_i"),
        k_i=_float_list(frequency_raw.get("k_i"), "k_i"),
        delta_a_i=_float_list(frequency_raw.get("delta_a_i"), "delta_a_i"),
    )

    if (
        len(frequency_config.f_i) != number_of_constants
        or len(frequency_config.delta_f_i) != number_of_constants
        or len(frequency_config.k_i) != number_of_constants
        or len(frequency_config.delta_a_i) != number_of_constants
    ):
        raise ConfigValidationError(
            f"Константы частот должны содержать ровно по {number_of_constants} значений."
        )

    norm_raw = _require_dict(raw_dict.get("norm_params_by_category"), "norm_params_by_category")
    norm_config = NormParamsConfig(
        delta_stn=_float_list(norm_raw.get("delta_stn"), "delta_stn"),
        w_n=_float_list(norm_raw.get("w_n"), "w_n"),
    )

    noise_raw = _require_dict(raw_dict.get("norm_noise_by_line"), "norm_noise_by_line")
    symmetrical_raw = _require_dict(noise_raw.get("symmetrical"), "norm_noise_by_line.symmetrical")
    asymmetrical_raw = _require_dict(
        noise_raw.get("asymmetrical"), "norm_noise_by_line.asymmetrical"
    )
    power_raw = _require_dict(noise_raw.get("power"), "norm_noise_by_line.power")
    norm_noise = NormNoiseByLineConfig(
        symmetrical=_float_list(
            symmetrical_raw.get("values"), "norm_noise_by_line.symmetrical.values"
        ),
        asymmetrical=_float_list(
            asymmetrical_raw.get("values"), "norm_noise_by_line.asymmetrical.values"
        ),
        power=_float_list(power_raw.get("values"), "norm_noise_by_line.power.values"),
    )
    if not all(
        len(values) == number_of_constants
        for values in (norm_noise.symmetrical, norm_noise.asymmetrical, norm_noise.power)
    ):
        raise ConfigValidationError(
            "Списки values в [norm_noise_by_line] должны содержать по "
            + f"{number_of_constants} значений."
        )

    line_raw = _require_dict(raw_dict.get("line"), "line")
    line_sym = _require_dict(line_raw.get("symmetrical"), "line.symmetrical")
    line_asym = _require_dict(line_raw.get("asymmetrical"), "line.asymmetrical")
    line_power = _require_dict(line_raw.get("power"), "line.power")
    lines = LineConfig(
        symmetrical=_string_list(line_sym.get("names"), "line.symmetrical.names"),
        asymmetrical=_string_list(line_asym.get("names"), "line.asymmetrical.names"),
        power=_string_list(line_power.get("names"), "line.power.names"),
    )

    modes_raw = _require_dict(raw_dict.get("operation_modes"), "operation_modes")
    operation_modes = _string_list(modes_raw.get("modes"), "operation_modes.modes")

    return AppConfig(
        frequency_constants=frequency_config,
        norm_params=norm_config,
        norm_noise_by_line=norm_noise,
        lines=lines,
        operation_modes=operation_modes,
    )
