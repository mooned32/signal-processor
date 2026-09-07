from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import tomllib

from .parser import load_spectrum_txt


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def calculate_data(
    file_sn_path: Path, file_n_path: Path, config_path: Path
) -> tuple[pd.DataFrame, float]:
    """
    Выполняет сопоставление и расчёт таблицы.
    Возвращает (итоговый DataFrame, скалярное значение W).
    """
    config = load_config(config_path)

    points_section: dict[str, Any] = config.get("points", {})
    constants_section: dict[str, Any] = config.get("constants", {})

    raw_targets: list[float] = [float(t) for t in points_section.get("targets", [])]
    c_constants: list[float] = [float(c) for c in constants_section.get("C", [])]
    y_constants: list[float] = [float(y) for y in constants_section.get("Y", [])]

    if not (len(raw_targets) == len(c_constants) == len(y_constants) == 20):
        raise ValueError("В конфиге targets, C и Y должны содержать ровно 20 элементов!")

    # Сортируем опорные значения и связываем с C и Y
    points_df = (
        pd.DataFrame(
            {
                "target": [round(t, 4) for t in raw_targets],
                "C": c_constants,
                "Y": y_constants,
            }
        )
        .sort_values(by="target")
        .reset_index(drop=True)
    )

    points_df["i"] = np.arange(1, 21, dtype=int)

    # Считываем спектры
    df_sn = load_spectrum_txt(file_sn_path)  # Сигнал + Шум
    df_n = load_spectrum_txt(file_n_path)  # Шум

    # Pyright stubs ошибочно типизируют tolerance как int | timedelta | None
    tolerance_val: Any = 1e-3

    merged_sn = pd.merge_asof(
        points_df.sort_values("target"),
        df_sn.sort_values("freq"),
        left_on="target",
        right_on="freq",
        direction="nearest",
        tolerance=tolerance_val,
    ).rename(columns={"voltage": "U_сш_i"})

    merged = pd.merge_asof(
        merged_sn.sort_values("target"),
        df_n.sort_values("freq"),
        left_on="target",
        right_on="freq",
        direction="nearest",
        tolerance=tolerance_val,
    ).rename(columns={"voltage": "U_ш_i"})

    # Проверка на наличие пропущенных точек
    has_missing_sn = bool(merged["U_сш_i"].isna().to_numpy().any())
    has_missing_n = bool(merged["U_ш_i"].isna().to_numpy().any())

    if has_missing_sn or has_missing_n:
        mask = merged["U_сш_i"].isna() | merged["U_ш_i"].isna()
        missing_targets: list[Any] = merged.loc[mask, "target"].tolist()
        raise ValueError(
            f"Не удалось найти соответствия в файлах для опорных значений: {missing_targets}"
        )

    # Физический расчет через numpy для строгой типизации: U_c = sqrt(max(0, U_сш^2 - U_ш^2))
    u_sn_arr = merged["U_сш_i"].to_numpy(dtype=float)
    u_n_arr = merged["U_ш_i"].to_numpy(dtype=float)
    c_arr = merged["C"].to_numpy(dtype=float)
    y_arr = merged["Y"].to_numpy(dtype=float)

    diff_squares = u_sn_arr**2 - u_n_arr**2
    u_c_arr = np.sqrt(np.maximum(0.0, diff_squares))
    merged["U_с_i"] = u_c_arr

    # Плейсхолдеры под будущие формулы для x и y
    x_arr = u_c_arr * c_arr
    y_calc_arr = u_c_arr / (y_arr + 1e-9)

    merged["x"] = x_arr
    merged["y"] = y_calc_arr

    # Скалярное значение W (плейсхолдер: среднее по столбцу x)
    w_val: float = float(x_arr.mean())

    # Формируем итоговый порядок столбцов и округляем значения
    columns_order = ["i", "C", "Y", "U_сш_i", "U_ш_i", "U_с_i", "x", "y"]
    final_df = pd.DataFrame(merged[columns_order].copy())

    for col in ["U_сш_i", "U_ш_i", "U_с_i", "x", "y"]:
        final_df[col] = final_df[col].round(4)

    return final_df, w_val
