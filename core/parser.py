import re
from io import StringIO
from pathlib import Path

import pandas as pd


def load_spectrum_txt(file_path: Path | str) -> pd.DataFrame:
    """
    Быстро считывает текстовый файл (32k строк).
    Пропускает строки с комментариями (#, [, ().
    Корректно обрабатывает запятые в качестве десятичного разделителя.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    cleaned_lines: list[str] = []
    comment_pattern = re.compile(r"^\s*([#\[\(])")

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or comment_pattern.match(stripped):
                continue
            cleaned_lines.append(stripped.replace(",", "."))

    if not cleaned_lines:
        raise ValueError(f"Файл {path.name} не содержит числовых данных.")

    df = pd.read_csv(
        StringIO("\n".join(cleaned_lines)),
        sep=r"\s+",
        header=None,
        names=["freq", "voltage"],
        dtype={"freq": float, "voltage": float},
        usecols=[0, 1],
        engine="c",
    )

    df["freq"] = df["freq"].round(4)
    return df
