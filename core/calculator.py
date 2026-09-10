from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
import tomllib

from .parser import load_spectrum_txt


def load_config(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
    with open(config_path, "rb") as f:
        return cast(dict[str, object], tomllib.load(f))


def calculate_data(
    file_sn_path: Path,
    file_n_path: Path,
    config_path: Path,
    category_index: int,  # 0, 1, или 2 (Категория 1, 2, 3)
    line_type: str,  # "symmetrical", "asymmetrical", "power"
    r_param: float | None = None,
) -> tuple[pd.DataFrame, list[bool], bool]:
    """
    Векторизованный расчет на NumPy.
    Возвращает:
      (DataFrame со столбцами i, delta_f_i, f_i, U_sn_i, U_n_i, U_s_i, q,
       список флагов превышения для каждой точки,
       общий флаг наличия нарушений).
    """
    _ = r_param

    config = load_config(config_path)

    # 1. Извлечение констант частот
    freq_cfg = cast(dict[str, object], config.get("frequency_constants", {}))
    raw_f_i = cast(list[object], freq_cfg.get("f_i", []))
    raw_delta_f = cast(list[object], freq_cfg.get("delta_f_i", []))
    raw_delta_a = cast(list[object], freq_cfg.get("delta_A_i", []))

    if len(raw_f_i) != 20 or len(raw_delta_f) != 20:
        raise ValueError("В frequency_constants f_i и delta_f_i должны содержать по 20 чисел!")

    f_i_arr = np.array([float(str(x)) for x in raw_f_i], dtype=np.float64)
    delta_f_arr = np.array([float(str(x)) for x in raw_delta_f], dtype=np.float64)
    _ = raw_delta_a

    # 2. Нормированные шумы для выбранной линии
    norm_noise_cfg = cast(dict[str, object], config.get("norm_noise_by_line", {}))
    line_noise_dict = cast(dict[str, object], norm_noise_cfg.get(line_type, {}))
    raw_noise_vals = cast(list[object], line_noise_dict.get("values", []))
    line_norm_noise = (
        np.array([float(str(x)) for x in raw_noise_vals], dtype=np.float64)
        if len(raw_noise_vals) == 20
        else np.zeros(20, dtype=np.float64)
    )
    _ = line_norm_noise

    # 3. Нормированные параметры по категории
    norm_cat_cfg = cast(dict[str, object], config.get("norm_params_by_category", {}))
    delta_stn_list = cast(list[object], norm_cat_cfg.get("delta_stn", []))
    if len(delta_stn_list) < 3:
        raise ValueError("В norm_params_by_category.delta_stn должно быть 3 значения!")
    delta_stn_val = float(str(delta_stn_list[category_index]))

    # 4. Считывание спектров и сопоставление по f_i
    df_sn = load_spectrum_txt(file_sn_path)
    df_n = load_spectrum_txt(file_n_path)

    df_sn["freq_key"] = df_sn["freq"].round().astype(int)
    df_n["freq_key"] = df_n["freq"].round().astype(int)

    points_df = pd.DataFrame(
        {
            "i": list(range(1, 21)),
            "delta_f_i": delta_f_arr,
            "f_i": f_i_arr,
            "freq_key": np.rint(f_i_arr).astype(int),
        }
    )

    merged_sn = pd.merge(
        points_df,
        df_sn[["freq_key", "voltage"]].rename(columns={"voltage": "U_sn_i"}),
        on="freq_key",
        how="left",
    )

    merged = (
        pd.merge(
            merged_sn,
            df_n[["freq_key", "voltage"]].rename(columns={"voltage": "U_n_i"}),
            on="freq_key",
            how="left",
        )
        .sort_values("i")
        .reset_index(drop=True)
    )

    if bool(merged["U_sn_i"].isna().to_numpy().any()) or bool(
        merged["U_n_i"].isna().to_numpy().any()
    ):
        missing = merged.loc[merged["U_sn_i"].isna() | merged["U_n_i"].isna(), "f_i"].tolist()
        raise ValueError(f"Не найдены строки измерений для частот: {missing}")

    # 5. Векторизованные расчеты на NumPy
    u_sn = merged["U_sn_i"].to_numpy(dtype=np.float64)
    u_n = merged["U_n_i"].to_numpy(dtype=np.float64)

    # U_s = sqrt(max(0, U_sn^2 - U_n^2))
    u_s = np.sqrt(np.maximum(0.0, u_sn**2 - u_n**2))
    merged["U_s_i"] = u_s

    # Формула q (плейсхолдер)
    euler_e = np.e
    factor = (2.66 * (euler_e**2.3)) / 5.34
    q_arr = np.sqrt(np.maximum(0.0, 0.90 + factor * u_s))
    merged["q"] = q_arr

    # Сравнение с дельта_стн
    violations_arr = q_arr >= delta_stn_val
    violations_mask: list[bool] = [bool(x) for x in violations_arr]
    has_violations = bool(np.any(violations_arr))

    cols = ["i", "delta_f_i", "f_i", "U_sn_i", "U_n_i", "U_s_i", "q"]
    final_df = pd.DataFrame(merged[cols].copy())

    for col in ["delta_f_i", "f_i", "U_sn_i", "U_n_i", "U_s_i", "q"]:
        final_df[col] = final_df[col].round(4)

    return final_df, violations_mask, has_violations
