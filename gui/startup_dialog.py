from collections.abc import Callable
from typing import Protocol

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class VoidSignal(Protocol):
    def connect(self, slot: Callable[[], None], /) -> object: ...


def connect_action(signal: VoidSignal, slot: Callable[[], None]) -> None:
    _ = signal.connect(slot)


class StartupDialog(QDialog):
    input_device: QLineEdit
    combo_category: QComboBox

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Параметры объекта")
        self.setFixedWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        lbl_info = QLabel("Параметры новой серии измерений")
        lbl_info.setStyleSheet("font-size: 13px; color: #1E293B; font-weight: 500;")
        layout.addWidget(lbl_info)

        form = QFormLayout()
        form.setSpacing(10)

        self.input_device = QLineEdit("Телевизор")
        self.input_device.setFixedHeight(30)
        self.combo_category = QComboBox()
        self.combo_category.setFixedHeight(30)
        for cat in ["Категория 1", "Категория 2", "Категория 3"]:
            self.combo_category.addItem(cat)

        form.addRow(QLabel("Название устройства:"), self.input_device)
        form.addRow(QLabel("Категория объекта:"), self.combo_category)
        layout.addLayout(form)

        layout.addSpacing(6)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        btn_cancel = QPushButton("Выход")
        btn_cancel.setFixedHeight(32)
        btn_cancel.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; "
            + "border-radius: 4px; padding: 0 16px; font-size: 12px; } "
            + "QPushButton:hover { background-color: #E2E8F0; }"
        )
        connect_action(btn_cancel.clicked, self.reject)

        btn_start = QPushButton("Начать измерение")
        btn_start.setFixedHeight(32)
        btn_start.setStyleSheet(
            "QPushButton { background-color: #0F6CBD; color: white; border: none; "
            + "border-radius: 4px; padding: 0 18px; font-size: 12px; font-weight: 500; } "
            + "QPushButton:hover { background-color: #0D5A9B; } "
            + "QPushButton:pressed { background-color: #0B487B; }"
        )
        connect_action(btn_start.clicked, self._on_start)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_start)
        layout.addLayout(btn_layout)

    def _on_start(self) -> None:
        name = self.input_device.text().strip()
        if not name:
            _ = QMessageBox.warning(self, "Внимание", "Укажите название проверяемого устройства.")
            return
        self.accept()

    def get_params(self) -> tuple[str, int]:
        return self.input_device.text().strip(), self.combo_category.currentIndex()
