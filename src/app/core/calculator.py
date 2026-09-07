from pathlib import Path
from typing import Any
import tomllib

import numpy as np
import pandas as pd

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
    Выполняет сопоставление по меткам C и расчёт таблицы.
    Возвращает (итоговый DataFrame со столбцом W, скалярное значение W).
    """
    config = load_config(config_path)
    constants_section: dict[str, Any] = config.get("constants", {})

    raw_c: list[Any] = list(constants_section.get("C", []))
    if len(raw_c) != 20:
        raise ValueError(f"В конфиге C должно быть ровно 20 элементов (сейчас {len(raw_c)})!")

    # Сортируем C по возрастанию и формируем i от 1 до 20
    sorted_c = sorted([int(c) for c in raw_c])

    points_df = pd.DataFrame({
        "i": np.arange(1, 21, dtype=int),
        "C": sorted_c,
        "target_freq": [float(c) for c in sorted_c]
    })

    # Считываем спектры (32k строк)
    df_sn = load_spectrum_txt(file_sn_path)  # Сигнал + Шум
    df_n = load_spectrum_txt(file_n_path)   # Шум

    # Ищем строки по значению C с допуском (например, для "500.00" и 500)
    tolerance_val: Any = 1e-3

    merged_sn = pd.merge_asof(
        points_df.sort_values("target_freq"),
        df_sn.sort_values("freq"),
        left_on="target_freq",
        right_on="freq",
        direction="nearest",
        tolerance=tolerance_val,
    ).rename(columns={"voltage": "U_сш_i"})

    merged = pd.merge_asof(
        merged_sn.sort_values("target_freq"),
        df_n.sort_values("freq"),
        left_on="target_freq",
        right_on="freq",
        direction="nearest",
        tolerance=tolerance_val,
    ).rename(columns={"voltage": "U_ш_i"}).sort_values("i").reset_index(drop=True)

    # Проверка на пропущенные точки
    if bool(merged["U_сш_i"].isna().to_numpy().any()) or bool(merged["U_ш_i"].isna().to_numpy().any()):
        mask = merged["U_сш_i"].isna() | merged["U_ш_i"].isna()
        missing = merged.loc[mask, "C"].tolist()
        raise ValueError(f"В файлах не найдены строки для следующих значений C: {missing}")

    # Расчет: U_c = sqrt(max(0, U_сш^2 - U_ш^2))
    u_sn = merged["U_сш_i"].to_numpy(dtype=float)
    u_n = merged["U_ш_i"].to_numpy(dtype=float)

    diff_sq = u_sn**2 - u_n**2
    u_c = np.sqrt(np.maximum(0.0, diff_sq))
    merged["U_с_i"] = u_c

    # Плейсхолдеры для x и y
    c_arr = merged["C"].to_numpy(dtype=float)
    merged["x"] = u_c * (c_arr / 1000.0)
    merged["y"] = u_c / (c_arr + 1.0)

    # Плейсхолдер скаляра W (случайное или среднее значение)
    w_val: float = float(np.random.uniform(10.0, 50.0))

    # Столбец W в таблице
    merged["W"] = w_val

    # Итоговый порядок столбцов: i, C, U_сш_i, U_ш_i, U_с_i, x, y, W
    cols = ["i", "C", "U_сш_i", "U_ш_i", "U_с_i", "x", "y", "W"]
    final_df = pd.DataFrame(merged[cols].copy())

    for col in ["U_сш_i", "U_ш_i", "U_с_i", "x", "y", "W"]:
        final_df[col] = final_df[col].round(4)

    return final_df, w_val