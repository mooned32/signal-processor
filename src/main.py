import sys
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMessageBox

from config.config_loader import load_config
from ui.main_window import MainWindow
from ui.startup_dialog import StartupDialog


def get_base_dir() -> Path:
    """Return the directory containing config.toml for dev and PyInstaller modes."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def main() -> int:
    app = QApplication(sys.argv)
    _ = app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))

    base_dir = get_base_dir()
    config_path = base_dir / "config.toml"

    try:
        config = load_config(config_path)
    except (OSError, ValueError) as error:
        _ = QMessageBox.critical(None, "Ошибка конфигурации", str(error))
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
