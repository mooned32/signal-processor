"""Скрипт генерации тестовых спектральных данных (32 000 строк)."""

from pathlib import Path

import numpy as np


def generate_spectrum_files(
    output_dir: Path = Path("test_data"),
    num_points: int = 32_000,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    file_sn_path = output_dir / "signal_noise.txt"
    file_n_path = output_dir / "noise.txt"

    frequencies = np.arange(1.0, float(num_points) + 1.0, 1.0)

    np.random.seed(42)
    noise = 1.5 + 0.3 * np.random.randn(num_points)
    noise = np.clip(noise, 0.5, 4.0)

    # Сигнал с синусоидой
    signal = 5.0 + 3.0 * np.sin(2 * np.pi * frequencies / 2000)
    signal_noise = np.sqrt(signal**2 + noise**2) + 0.1 * np.random.randn(num_points)

    with open(file_n_path, "w", encoding="utf-8") as f_n:
        f_n.write("# Тестовый спектр: ЧИСТЫЙ ШУМ (U_ш)\n")
        f_n.write("[Параметры: 32000 строк, шаг 1.0]\n")
        for freq, val in zip(frequencies, noise, strict=True):
            f_n.write(f"{freq:.2f}\t{val:.3f}\n")

    with open(file_sn_path, "w", encoding="utf-8") as f_sn:
        f_sn.write("# Тестовый спектр: СИГНАЛ + ШУМ (U_сш)\n")
        f_sn.write("[Параметры: 32000 строк, шаг 1.0]\n")
        for freq, val in zip(frequencies, signal_noise, strict=True):
            f_sn.write(f"{freq:.2f}\t{val:.3f}\n")

    print(f"Готово! Сгенерированы:\n - {file_sn_path}\n - {file_n_path}")
    return file_sn_path, file_n_path


if __name__ == "__main__":
    generate_spectrum_files()
