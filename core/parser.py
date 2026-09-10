from pathlib import Path


def load_spectrum_map(file_path: Path | str) -> dict[int, float]:
    """
    Считывает спектральный файл и возвращает словарь {частота: напряжение}.
    Не использует сторонние библиотеки, исключая появление Any.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    spectrum: dict[int, float] = {}
    comment_chars = ("#", "[", "(")

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith(comment_chars):
                continue
            parts = stripped.replace(",", ".").split()
            if len(parts) >= 2:
                try:
                    freq = float(parts[0])
                    voltage = float(parts[1])
                    spectrum[int(round(freq))] = voltage
                except ValueError:
                    continue

    if not spectrum:
        raise ValueError(f"Файл {path.name} не содержит числовых данных.")

    return spectrum
