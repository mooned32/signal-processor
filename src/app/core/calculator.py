import math
import random
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
        data: object = tomllib.load(f)
        if isinstance(data, dict):
            return cast(dict[str, object], data)
        raise ValueError("Некорректная структура файла конфигурации")


def calculate_data(
    file_sn_path: Path,
    file_n_path: Path,
    config_path: Path,
    mode_index: int,
    z_value: float,
) -> tuple[pd.DataFrame, float, list[bool]]:
    """
    Выполняет сопоставление по меткам C и расчёт таблицы.
    Возвращает (DataFrame, скаляр W, булев список для подсветки столбца x).
    """
    _ = z_value

    config = load_config(config_path)
    constants_obj = config.get("constants")
    constants: dict[str, object] = (
        cast(dict[str, object], constants_obj) if isinstance(constants_obj, dict) else {}
    )

    raw_c_obj = constants.get("C")
    raw_f_obj = constants.get("F")
    raw_o_obj = constants.get("O")
    raw_n_obj = constants.get("N")

    raw_c: list[object] = raw_c_obj if isinstance(raw_c_obj, list) else []
    raw_f: list[object] = raw_f_obj if isinstance(raw_f_obj, list) else []
    raw_o: list[object] = raw_o_obj if isinstance(raw_o_obj, list) else []
    raw_n: list[object] = raw_n_obj if isinstance(raw_n_obj, list) else []

    if len(raw_c) != 20 or len(raw_f) != 20:
        raise ValueError("В конфиге массивы C и F должны содержать ровно по 20 элементов!")
    if len(raw_o) != 3 or len(raw_n) != 3:
        raise ValueError("В конфиге массивы O и N должны содержать ровно по 3 элемента!")

    c_vals: list[int] = [int(float(str(c))) for c in raw_c]
    f_vals: list[float] = [float(str(f)) for f in raw_f]
    o_vals: list[float] = [float(str(o)) for o in raw_o]

    # Сортируем пары (C, F) по возрастанию C
    paired: list[tuple[int, float]] = sorted(
        zip(c_vals, f_vals, strict=True),
        key=lambda item: item[0],
    )
    sorted_c: list[int] = [p[0] for p in paired]
    sorted_f: list[float] = [p[1] for p in paired]

    points_df = pd.DataFrame(
        {
            "i": list(range(1, 21)),
            "C": sorted_c,
            "F": sorted_f,
            "freq_key": sorted_c,
        }
    )

    # Считываем 32k спектры
    df_sn = load_spectrum_txt(file_sn_path)
    df_n = load_spectrum_txt(file_n_path)

    # Формируем целочисленный ключ для точного сопоставления
    df_sn["freq_key"] = np.rint(df_sn["freq"].to_numpy()).astype(int)
    df_n["freq_key"] = np.rint(df_n["freq"].to_numpy()).astype(int)

    merged_sn = pd.merge(
        points_df,
        df_sn[["freq_key", "voltage"]].rename(columns={"voltage": "U_сш_i"}),
        on="freq_key",
        how="left",
    )

    merged = (
        pd.merge(
            merged_sn,
            df_n[["freq_key", "voltage"]].rename(columns={"voltage": "U_ш_i"}),
            on="freq_key",
            how="left",
        )
        .sort_values("i")
        .reset_index(drop=True)
    )

    u_sn_series = merged["U_сш_i"]
    u_n_series = merged["U_ш_i"]

    if bool(u_sn_series.isna().to_numpy().any()) or bool(u_n_series.isna().to_numpy().any()):
        mask = u_sn_series.isna() | u_n_series.isna()
        missing: list[object] = merged.loc[mask, "C"].tolist()
        raise ValueError(f"В файлах не найдены строки для значений C: {missing}")

    u_sn_list: list[float] = [float(v) for v in u_sn_series]
    u_n_list: list[float] = [float(v) for v in u_n_series]

    # U_c = sqrt(max(0, U_сш^2 - U_ш^2))
    u_c_list: list[float] = [
        math.sqrt(max(0.0, sn**2 - n**2)) for sn, n in zip(u_sn_list, u_n_list, strict=True)
    ]
    merged["U_с_i"] = u_c_list

    # x = sqrt(0.90 + (2.66 * e^2.3 / 5.34) * U_c)
    factor: float = (2.66 * (math.e**2.3)) / 5.34
    x_vals: list[float] = [math.sqrt(max(0.0, 0.90 + factor * uc)) for uc in u_c_list]
    merged["x"] = x_vals

    threshold_o: float = o_vals[mode_index]
    x_is_alert: list[bool] = [val >= threshold_o for val in x_vals]

    # y = U_c / (F + 1e-6)
    f_list: list[float] = [float(v) for v in merged["F"]]
    merged["y"] = [uc / (f + 1e-6) for uc, f in zip(u_c_list, f_list, strict=True)]

    w_val: float = float(random.uniform(10.0, 50.0))
    merged["W"] = w_val

    cols = ["i", "C", "F", "U_сш_i", "U_ш_i", "U_с_i", "x", "y", "W"]
    final_df = pd.DataFrame(merged[cols].copy())

    for col in ["F", "U_сш_i", "U_ш_i", "U_с_i", "x", "y", "W"]:
        final_df[col] = final_df[col].round(4)

    return final_df, w_val, x_is_alert
