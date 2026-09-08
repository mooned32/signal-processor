"""Скрипт генерации тестовых спектральных данных (32 000 строк)."""

import math
import random
from pathlib import Path

import numpy as np


def generate_spectrum_files(
    output_dir: Path | None = None,
    num_points: int = 32_000,
) -> tuple[Path, Path]:
    target_dir = Path("test_data") if output_dir is None else output_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    file_sn_path = target_dir / "signal_noise.txt"
    file_n_path = target_dir / "noise.txt"

    freq_floats: list[float] = [float(i) for i in range(1, num_points + 1)]

    # Фоновый шум
    np.random.seed(42)
    raw_noise = np.clip(1.5 + 0.3 * np.random.randn(num_points), 0.5, 4.0)
    noise_floats: list[float] = [float(v) for v in raw_noise]

    # Сигнал U_с
    signal_floats: list[float] = [
        5.0 + 3.0 * math.sin(2.0 * math.pi * f / 2000.0) for f in freq_floats
    ]

    # Смесь U_сш = sqrt(U_c^2 + U_ш^2) + шум
    sn_floats: list[float] = [
        math.sqrt(s**2 + n**2) + random.gauss(0.0, 0.1)
        for s, n in zip(signal_floats, noise_floats, strict=True)
    ]

    # Запись шума
    noise_lines: list[str] = [
        "# Тестовый спектр: ЧИСТЫЙ ШУМ (U_ш)\n",
        "[Параметры: 32000 строк, шаг 1.0]\n",
        *(f"{freq:.2f}\t{val:.3f}\n" for freq, val in zip(freq_floats, noise_floats, strict=True)),
    ]
    with open(file_n_path, "w", encoding="utf-8") as f_n:
        f_n.writelines(noise_lines)

    # Запись сигнала с шумом
    sn_lines: list[str] = [
        "# Тестовый спектр: СИГНАЛ + ШУМ (U_сш)\n",
        "[Параметры: 32000 строк, шаг 1.0]\n",
        *(f"{freq:.2f}\t{val:.3f}\n" for freq, val in zip(freq_floats, sn_floats, strict=True)),
    ]
    with open(file_sn_path, "w", encoding="utf-8") as f_sn:
        f_sn.writelines(sn_lines)

    print(f"Готово! Сгенерированы:\n - {file_sn_path}\n - {file_n_path}")
    return file_sn_path, file_n_path


if __name__ == "__main__":
    _ = generate_spectrum_files()
