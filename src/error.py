class SignalProcessorError(Exception):
    """Базовый класс для всех исключений приложения Signal Processor."""


class ConfigError(SignalProcessorError):
    """Базовое исключение для ошибок конфигурации."""


class ConfigNotFoundError(ConfigError):
    """Конфигурационный файл не найден."""

    def __init__(self, path: str) -> None:
        super().__init__(f"Конфигурационный файл не найден: {path}")
        self.path = path


class ConfigValidationError(ConfigError):
    """Некорректная структура или значения параметров конфигурации."""


class SpectrumError(SignalProcessorError):
    """Базовое исключение для ошибок при обработке спектральных файлов."""


class SpectrumNotFoundError(SpectrumError):
    """Файл спектра не найден на носителе."""

    def __init__(self, path: str) -> None:
        super().__init__(f"Файл спектра не найден: {path}")
        self.path = path


class SpectrumFormatError(SpectrumError):
    """Некорректный формат или структура данных в файле спектра."""


class SpectrumMissingFrequencyError(SpectrumError):
    """В файле спектра отсутствуют обязательные контрольные частоты."""

    def __init__(self, filename: str, missing_frequencies: list[float]) -> None:
        missing_str = ", ".join(
            str(int(f)) if f.is_integer() else f"{f:.2f}" for f in missing_frequencies
        )
        super().__init__(f"В файле '{filename}' отсутствуют обязательные частоты: {missing_str}")
        self.filename = filename
        self.missing_frequencies = missing_frequencies


class CalculationError(SignalProcessorError):
    """Некорректные параметры или ошибка выполнения расчёта."""


class DatabaseError(SignalProcessorError):
    """Ошибка доступа или выполнения операций с базой данных SQLite."""
