import sys
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.startup_dialog import StartupDialog


def get_base_dir() -> Path:
    """
    Возвращает директорию расположения исполняемого файла или скрипта.
    Учитывает различия Nuitka (--onefile через sys.argv[0]), PyInstaller и dev-режима.
    """
    # Проверка запуска в скомпилированном виде (Nuitka или PyInstaller)
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        if sys.argv and sys.argv[0]:
            candidate = Path(sys.argv[0]).resolve().parent
            if (candidate / "config.toml").exists():
                return candidate

            exec_dir = Path(sys.executable).resolve().parent
            if (exec_dir / "config.toml").exists():
                return exec_dir

            return candidate

        return Path(sys.executable).resolve().parent

    # Запуск из исходников в среде разработки
    return Path(__file__).resolve().parent


def main() -> None:
    app = QApplication(sys.argv)
    _ = app.setStyle("Fusion")

    app.setFont(QFont("Segoe UI", 9))

    config_path = get_base_dir() / "config.toml"

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
