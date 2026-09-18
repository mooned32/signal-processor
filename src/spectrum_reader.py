from collections.abc import Sequence
from pathlib import Path

EXPECTED_FREQUENCY_COUNT = 20


def read_required_frequencies(file_path: Path, frequencies: Sequence[float]) -> list[float]:
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    if len(frequencies) != EXPECTED_FREQUENCY_COUNT:
        raise ValueError("Список контрольных частот должен содержать ровно 20 значений.")

    requested = {int(round(frequency)) for frequency in frequencies}
    found: dict[int, float] = {}
    comment_chars = ("#", "[", "(")

    with file_path.open(encoding="utf-8", errors="replace") as spectrum_file:
        for line in spectrum_file:
            stripped = line.strip()
            if not stripped or stripped.startswith(comment_chars):
                continue

            parts = stripped.replace(",", ".").split()
            if len(parts) < 2:
                continue

            try:
                frequency = int(round(float(parts[0])))
                voltage = float(parts[1])
            except ValueError:
                continue

            if frequency in requested:
                found[frequency] = voltage
                if len(found) == len(requested):
                    break

    missing = [frequency for frequency in frequencies if int(round(frequency)) not in found]
    if missing:
        raise ValueError(f"В файле {file_path.name} отсутствуют частоты: {missing}")

    return [found[int(round(frequency))] for frequency in frequencies]
