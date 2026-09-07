import sys
from pathlib import Path

from app.gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication


def get_base_dir() -> Path:
    """Возвращает путь к директории с .exe или скриптом main.py."""
    if getattr(sys, "frozen", False):
        # Запуск внутри упакованного .exe
        return Path(sys.executable).resolve().parent
    # Обычный запуск исходников
    return Path(__file__).resolve().parent.parent.parent


def main():
    app = QApplication(sys.argv)

    # Настройки отображения для Windows
    app.setStyle("windowsvista")

    config_path = get_base_dir() / "config.toml"
    window = MainWindow(config_path=config_path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
