import os
import sys
import traceback
from pathlib import Path
from types import TracebackType

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMessageBox

from config_loader import load_config
from database import init_database
from error import ConfigError, DatabaseError
from ui.main_window import MainWindow
from ui.startup_dialog import StartupDialog


def handle_unhandled_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Show unhandled exceptions in a critical message dialog with stack trace."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    traceback_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    traceback_text = "".join(traceback_lines)

    dialog = QMessageBox()
    dialog.setIcon(QMessageBox.Icon.Critical)
    dialog.setWindowTitle("Непредвиденная ошибка")
    dialog.setText(f"Произошла непредвиденная системная ошибка:\n{exc_value}")
    dialog.setDetailedText(traceback_text)
    _ = dialog.exec()


def get_base_dir() -> Path:
    """Return the directory containing config.toml for dev and PyInstaller modes."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def main() -> int:
    base_dir = get_base_dir()
    os.chdir(base_dir)

    sys.excepthook = handle_unhandled_exception

    app = QApplication(sys.argv)
    _ = app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))

    config_path = base_dir / "config.toml"

    try:
        config = load_config(config_path)
    except ConfigError as error:
        _ = QMessageBox.critical(None, "Ошибка конфигурации", str(error))
        return 1

    try:
        init_database(base_dir / "measurements.db")
    except DatabaseError as error:
        _ = QMessageBox.critical(None, "Ошибка базы данных", str(error))
        return 1

    startup = StartupDialog()
    if startup.exec() != StartupDialog.DialogCode.Accepted:
        return 0

    device_name, category_index = startup.parameters()
    window = MainWindow(
        config=config,
        device_name=device_name,
        category_index=category_index,
        base_directory=base_dir,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
