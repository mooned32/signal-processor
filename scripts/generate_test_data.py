"""Скрипт генерации тестовых спектральных данных (32 000 строк)."""

import math
import random
from pathlib import Path


def generate_spectrum_files(
    output_dir: Path | None = None,
    num_points: int = 32_000,
) -> tuple[Path, Path]:
    target_dir = Path(__file__).resolve().parent / "test_data" if output_dir is None else output_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    file_sn_path = target_dir / "signal_noise.txt"
    file_n_path = target_dir / "noise.txt"
    frequencies = [float(index) for index in range(1, num_points + 1)]
    noise = [max(0.5, min(4.0, random.gauss(1.5, 0.3))) for _ in frequencies]
    signal = [5.0 + 3.0 * math.sin(2.0 * math.pi * f / 2000.0) for f in frequencies]
    signal_noise = [
        math.sqrt(s**2 + n**2) + random.gauss(0.0, 0.1) for s, n in zip(signal, noise, strict=True)
    ]

    file_n_path.write_text(
        "# Тестовый спектр: ЧИСТЫЙ ШУМ (U_ш)\n"
        "[Параметры: 32000 строк, шаг 1.0]\n"
        + "".join(f"{f:.2f}\t{n:.3f}\n" for f, n in zip(frequencies, noise, strict=True)),
        encoding="utf-8",
    )
    file_sn_path.write_text(
        "# Тестовый спектр: СИГНАЛ + ШУМ (U_сш)\n"
        "[Параметры: 32000 строк, шаг 1.0]\n"
        + "".join(f"{f:.2f}\t{v:.3f}\n" for f, v in zip(frequencies, signal_noise, strict=True)),
        encoding="utf-8",
    )
    return file_sn_path, file_n_path


if __name__ == "__main__":
    paths = generate_spectrum_files()
    print(f"Готово! Сгенерированы:\n - {paths[0]}\n - {paths[1]}")
