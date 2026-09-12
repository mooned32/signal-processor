from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    NONE = "none"
    CONFIG_FILE_NOT_FOUND = "config_file_not_found"
    INVALID_CONFIG = "invalid_config"
    SPECTRUM_FILE_NOT_FOUND = "spectrum_file_not_found"
    INVALID_SPECTRUM_FILE = "invalid_spectrum_file"
    MISSING_FREQUENCY = "missing_frequency"
    DATABASE_OPEN_FAILED = "database_open_failed"
    DATABASE_WRITE_FAILED = "database_write_failed"
    CALCULATION_FAILED = "calculation_failed"


@dataclass(frozen=True, slots=True)
class Error:
    code: ErrorCode
    message: str


class SignalProcessorError(Exception):
    def __init__(self, error: Error) -> None:
        super().__init__(error.message)
        self.error = error
