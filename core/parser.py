from pathlib import Path


def load_spectrum_values(file_path: Path, frequencies: set[int]) -> dict[int, float]:
    """Считывает только запрошенные частоты из спектрального файла."""
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    if not frequencies:
        return {}

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

            if frequency in frequencies:
                found[frequency] = voltage
                if len(found) == len(frequencies):
                    break

    if not found:
        raise ValueError(f"Файл {file_path.name} не содержит запрошенных числовых данных.")
    return found
