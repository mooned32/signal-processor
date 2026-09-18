from collections.abc import Sequence
from pathlib import Path

from error import (
    CalculationError,
    SpectrumFormatError,
    SpectrumMissingFrequencyError,
    SpectrumNotFoundError,
)


def read_required_frequencies(file_path: Path, frequencies: Sequence[float]) -> list[float]:
    if not file_path.exists():
        raise SpectrumNotFoundError(str(file_path))

    if not frequencies:
        raise CalculationError("Список контрольных частот не должен быть пустым.")

    requested = {int(round(frequency)) for frequency in frequencies}
    found: dict[int, float] = {}
    comment_chars = ("#", "[", "(")

    try:
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
    except OSError as err:
        raise SpectrumFormatError(
            f"Не удалось прочитать файл спектра '{file_path.name}': {err}"
        ) from err

    missing = [frequency for frequency in frequencies if int(round(frequency)) not in found]
    if missing:
        raise SpectrumMissingFrequencyError(file_path.name, missing)

    return [found[int(round(frequency))] for frequency in frequencies]
