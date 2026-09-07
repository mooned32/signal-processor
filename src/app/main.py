import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.gui.main_window import MainWindow


def get_base_dir() -> Path:
    """Возвращает путь к директории с .exe или скриптом main.py."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def main() -> None:
    app = QApplication(sys.argv)

    # Настройки отображения для Windows
    _ = app.setStyle("windowsvista")

    config_path = get_base_dir() / "config.toml"
    window = MainWindow(config_path=config_path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
