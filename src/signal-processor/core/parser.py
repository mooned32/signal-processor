import re
from pathlib import Path

import pandas as pd


def load_spectrum_txt(file_path: Path | str) -> pd.DataFrame:
    """
    Быстро считывает текстовый файл (32k строк).
    Пропускает строки с комментариями (#, [, ().
    Корректно обрабатывает запятые в качестве десятичного разделителя.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    cleaned_lines = []
    comment_pattern = re.compile(r"^\s*([#\[\(])")

    with open(file_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or comment_pattern.match(stripped):
                continue
            # Заменяем запятые на точки для дробных чисел
            cleaned_lines.append(stripped.replace(",", "."))

    if not cleaned_lines:
        raise ValueError(f"Файл {file_path.name} не содержит числовых данных.")

    from io import StringIO

    df = pd.read_csv(
        StringIO("\n".join(cleaned_lines)),
        sep=r"\s+",
        header=None,
        names=["freq", "voltage"],
        dtype={"freq": float, "voltage": float},
        usecols=[0, 1],
        engine="c",
    )

    # Округляем опорный столбец до 4 знаков для устранения погрешностей float
    df["freq"] = df["freq"].round(4)
    return df
