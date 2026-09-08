import math
import secrets
from pathlib import Path
from typing import cast

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
    mode_index: int,
    z_value: float,
) -> tuple[pd.DataFrame, pd.DataFrame, list[bool], list[int]]:
    """
    Выполняет расчет.
    Возвращает:
      (preview_df, extended_df, x_is_alert, violating_c).
    """
    _ = z_value

    config = load_config(config_path)
    constants_obj = config.get("constants")
    constants: dict[str, object] = (
        cast(dict[str, object], constants_obj) if isinstance(constants_obj, dict) else {}
    )

    raw_c: list[object] = cast(list[object], constants.get("C", []))
    raw_f: list[object] = cast(list[object], constants.get("F", []))
    raw_o: list[object] = cast(list[object], constants.get("O", []))

    if len(raw_c) != 20 or len(raw_f) != 20:
        raise ValueError("В конфиге массивы C и F должны содержать ровно по 20 элементов!")
    if len(raw_o) != 3:
        raise ValueError("В конфиге массив O должен содержать 3 элемента!")

    c_vals: list[int] = [int(float(str(c))) for c in raw_c]
    f_vals: list[float] = [float(str(f)) for f in raw_f]
    o_vals: list[float] = [float(str(o)) for o in raw_o]

    paired = sorted(zip(c_vals, f_vals, strict=True), key=lambda item: item[0])
    sorted_c = [p[0] for p in paired]
    sorted_f = [p[1] for p in paired]

    points_df = pd.DataFrame(
        {
            "i": list(range(1, 21)),
            "C": sorted_c,
            "F": sorted_f,
            "freq_key": sorted_c,
        }
    )

    df_sn = load_spectrum_txt(file_sn_path)
    df_n = load_spectrum_txt(file_n_path)

    df_sn["freq_key"] = df_sn["freq"].round().astype(int)
    df_n["freq_key"] = df_n["freq"].round().astype(int)

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

    u_sn_list: list[float] = [float(x) for x in cast(list[object], u_sn_series.tolist())]
    u_n_list: list[float] = [float(x) for x in cast(list[object], u_n_series.tolist())]

    u_c_list: list[float] = [
        math.sqrt(max(0.0, sn**2 - n**2)) for sn, n in zip(u_sn_list, u_n_list, strict=True)
    ]
    merged["U_с_i"] = u_c_list

    factor: float = (2.66 * math.pow(math.e, 2.3)) / 5.34
    x_vals: list[float] = [math.sqrt(max(0.0, 0.90 + factor * uc)) for uc in u_c_list]
    merged["x"] = x_vals

    threshold_o: float = o_vals[mode_index]
    x_is_alert: list[bool] = [val >= threshold_o for val in x_vals]

    violating_c: list[int] = [c for c, is_bad in zip(sorted_c, x_is_alert, strict=True) if is_bad]

    f_list: list[float] = [float(x) for x in cast(list[object], merged["F"].tolist())]
    merged["y"] = [uc / (f + 1e-6) for uc, f in zip(u_c_list, f_list, strict=True)]

    w_val: float = float(secrets.SystemRandom().uniform(10.0, 50.0))
    merged["W"] = w_val

    preview_cols = ["i", "C", "F", "U_сш_i", "U_ш_i", "U_с_i", "x"]
    preview_df = pd.DataFrame(merged[preview_cols].copy())

    ext_cols = ["i", "C", "F", "U_сш_i", "U_ш_i", "U_с_i", "x", "y", "W"]
    extended_df = pd.DataFrame(merged[ext_cols].copy())

    for col in ["F", "U_сш_i", "U_ш_i", "U_с_i", "x"]:
        preview_df[col] = preview_df[col].round(4)
    for col in ["F", "U_сш_i", "U_ш_i", "U_с_i", "x", "y", "W"]:
        extended_df[col] = extended_df[col].round(4)

    return preview_df, extended_df, x_is_alert, violating_c
