from pathlib import Path

import numpy as np
import pandas as pd
import tomllib

from .parser import load_spectrum_txt


def load_config(config_path: Path) -> dict:
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

    # Загружаем и сортируем точки
    raw_targets = config["points"]["targets"]
    c_constants = config["constants"]["C"]
    y_constants = config["constants"]["Y"]

    if not (len(raw_targets) == len(c_constants) == len(y_constants) == 20):
        raise ValueError("В конфиге targets, C и Y должны содержать ровно 20 элементов!")

    # Сортируем опорные значения и связываем с C и Y
    points_df = (
        pd.DataFrame(
            {
                "target": [round(float(t), 4) for t in raw_targets],
                "C": [float(c) for c in c_constants],
                "Y": [float(y) for y in y_constants],
            }
        )
        .sort_values(by="target")
        .reset_index(drop=True)
    )

    points_df["i"] = np.arange(1, 21)

    # Считываем спектры
    df_sn = load_spectrum_txt(file_sn_path)  # Сигнал + Шум
    df_n = load_spectrum_txt(file_n_path)  # Шум

    # Ищем строки по совпадению частоты (merge_asof с допуском 1e-3)
    merged_sn = pd.merge_asof(
        points_df.sort_values("target"),
        df_sn.sort_values("freq"),
        left_on="target",
        right_on="freq",
        direction="nearest",
        tolerance=1e-3,
    ).rename(columns={"voltage": "U_сш_i"})

    merged = pd.merge_asof(
        merged_sn.sort_values("target"),
        df_n.sort_values("freq"),
        left_on="target",
        right_on="freq",
        direction="nearest",
        tolerance=1e-3,
    ).rename(columns={"voltage": "U_ш_i"})

    # Проверка на наличие пропущенных точек
    if merged["U_сш_i"].isna().any() or merged["U_ш_i"].isna().any():
        missing = merged[merged["U_сш_i"].isna() | merged["U_ш_i"].isna()]["target"].tolist()
        raise ValueError(f"Не удалось найти соответствия в файлах для опорных значений: {missing}")

    # Физический расчет: U_c = sqrt(max(0, U_сш^2 - U_ш^2))
    diff_squares = merged["U_сш_i"] ** 2 - merged["U_ш_i"] ** 2
    # Если разница отрицательна, зануляем (U_c = 0.0)
    merged["U_с_i"] = np.sqrt(np.maximum(0.0, diff_squares))

    # Плейсхолдеры под будущие формулы для x и y
    merged["x"] = merged["U_с_i"] * merged["C"]  # TODO: подставить итоговую формулу
    merged["y"] = merged["U_с_i"] / (merged["Y"] + 1e-9)  # TODO: подставить итоговую формулу

    # Скалярное значение W (плейсхолдер: среднее по столбцу x)
    W = float(merged["x"].mean())

    # Формируем итоговый порядок столбцов
    final_df = merged[["i", "C", "Y", "U_сш_i", "U_ш_i", "U_с_i", "x", "y"]].copy()

    # Округляем для аккуратного отображения
    for col in ["U_сш_i", "U_ш_i", "U_с_i", "x", "y"]:
        final_df[col] = final_df[col].round(4)

    return final_df, W
