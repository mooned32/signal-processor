import tomllib
from pathlib import Path
from typing import cast

from calculation.calculation import FREQUENCY_COUNT
from calculation.models import (
    AppConfig,
    FrequencyConstantsConfig,
    LineConfig,
    NormNoiseByLineConfig,
    NormParamsConfig,
    ReportFields,
)


def _require_dict(value: object, section: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Секция [{section}] отсутствует или имеет некорректный формат")
    return cast(dict[str, object], value)


def _float_list(value: object, key: str) -> list[float]:
    if not isinstance(value, list):
        raise ValueError(f"Параметр {key} должен быть массивом чисел")
    items = cast(list[object], value)
    result: list[float] = []
    for item in items:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"Параметр {key} содержит значение нечислового типа")
        result.append(float(item))
    return result


def _string_list(value: object, key: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"Параметр {key} должен быть массивом строк")
    items = cast(list[object], value)
    result: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError(f"Параметр {key} содержит значение нестрокового типа")
        result.append(item)
    return result


def _string(value: object, key: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Параметр {key} должен быть строкой")
    return value


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")

    with config_path.open("rb") as config_file:
        raw_data: object = tomllib.load(config_file)

    raw_dict = _require_dict(raw_data, "root")

    frequency_raw = _require_dict(raw_dict.get("frequency_constants"), "frequency_constants")
    number_of_constants = frequency_raw.get("number_of_constants")
    if isinstance(number_of_constants, bool) or not isinstance(number_of_constants, int):
        raise ValueError("number_of_constants должен быть целым числом")
    if number_of_constants != FREQUENCY_COUNT:
        raise ValueError("number_of_constants must be exactly 20.")

    frequency_config = FrequencyConstantsConfig(
        number_of_constants=number_of_constants,
        f_i=_float_list(frequency_raw.get("f_i"), "f_i"),
        delta_f_i=_float_list(frequency_raw.get("delta_f_i"), "delta_f_i"),
        delta_a_i=_float_list(frequency_raw.get("delta_a_i"), "delta_a_i"),
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
        len(values) == FREQUENCY_COUNT
        for values in (norm_noise.symmetrical, norm_noise.asymmetrical, norm_noise.power)
    ):
        raise ValueError(
            "В [norm_noise_by_line] списки values должны содержать ровно по 20 значений!"
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

    report_raw = _require_dict(raw_dict.get("report_fields"), "report_fields")
    report_fields = ReportFields(
        act_number=_string(report_raw.get("ACT_NUMBER"), "report_fields.ACT_NUMBER"),
        date=_string(report_raw.get("DATE"), "report_fields.DATE"),
        operator_name=_string(report_raw.get("OPERATOR"), "report_fields.OPERATOR"),
        object_name=_string(report_raw.get("OBJECT_NAME"), "report_fields.OBJECT_NAME"),
    )

    if (
        len(frequency_config.f_i) != FREQUENCY_COUNT
        or len(frequency_config.delta_f_i) != FREQUENCY_COUNT
        or len(frequency_config.delta_a_i) != FREQUENCY_COUNT
    ):
        raise ValueError("frequency_constants содержит некорректные массивы")

    return AppConfig(
        frequency_constants=frequency_config,
        norm_params=norm_config,
        norm_noise_by_line=norm_noise,
        lines=lines,
        operation_modes=operation_modes,
        report_fields=report_fields,
    )
