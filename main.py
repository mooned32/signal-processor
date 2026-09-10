import sys
from pathlib import Path

from gui.main_window import MainWindow
from gui.startup_dialog import StartupDialog
from PyQt6.QtWidgets import QApplication


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def main() -> None:
    app = QApplication(sys.argv)
    _ = app.setStyle("windowsvista")

    config_path = get_base_dir() / "config.toml"

    # Стартовое окно параметров
    startup = StartupDialog()
    if startup.exec() != StartupDialog.DialogCode.Accepted:
        sys.exit(0)

    device_name, category_index = startup.get_params()

    window = MainWindow(
        config_path=config_path,
        device_name=device_name,
        category_index=category_index,
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
