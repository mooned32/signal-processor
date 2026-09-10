"""Скрипт генерации тестовых спектральных данных (32 000 строк)."""

import math
import random
from pathlib import Path


def generate_spectrum_files(
    output_dir: Path | None = None,
    num_points: int = 32_000,
) -> tuple[Path, Path]:
    target_dir = Path("test_data") if output_dir is None else output_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    file_sn_path = target_dir / "signal_noise.txt"
    file_n_path = target_dir / "noise.txt"

    freq_floats: list[float] = [float(i) for i in range(1, num_points + 1)]

    # Генерация шума в чистом Python
    noise_floats: list[float] = [
        max(0.5, min(4.0, random.gauss(1.5, 0.3))) for _ in range(num_points)
    ]

    # Сигнал U_с
    signal_floats: list[float] = [
        5.0 + 3.0 * math.sin(2.0 * math.pi * f / 2000.0) for f in freq_floats
    ]

    # Смесь U_сш
    sn_floats: list[float] = [
        math.sqrt(s**2 + n**2) + random.gauss(0.0, 0.1)
        for s, n in zip(signal_floats, noise_floats, strict=True)
    ]

    noise_lines: list[str] = [
        "# Тестовый спектр: ЧИСТЫЙ ШУМ (U_ш)\n",
        "[Параметры: 32000 строк, шаг 1.0]\n",
        *(f"{freq:.2f}\t{val:.3f}\n" for freq, val in zip(freq_floats, noise_floats, strict=True)),
    ]
    with open(file_n_path, "w", encoding="utf-8") as f_n:
        f_n.writelines(noise_lines)

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
