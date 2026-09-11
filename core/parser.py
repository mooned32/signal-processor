from pathlib import Path


def load_spectrum_values(
    file_path: Path | str,
    frequencies: set[int],
) -> dict[int, float]:
    """Считывает из спектрального файла только требуемые частоты."""
    if not frequencies:
        raise ValueError("Не задан список частот для извлечения.")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    spectrum: dict[int, float] = {}
    comment_chars = ("#", "[", "(")

    with path.open(encoding="utf-8", errors="replace") as file:
        for line in file:
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
                spectrum[frequency] = voltage

    missing = frequencies - spectrum.keys()
    if missing:
        missing_values = sorted(missing)
        raise ValueError(f"В файле {path.name} отсутствуют частоты: {missing_values}")

    return spectrum
