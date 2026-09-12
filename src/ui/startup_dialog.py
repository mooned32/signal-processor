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
    category: QComboBox

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.input_device = QLineEdit("Телевизор", self)
        self.category = QComboBox(self)

        self.setWindowTitle("Параметры объекта")
        self.setFixedWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        info = QLabel("Параметры новой серии измерений", self)
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        for category_name in ("Категория 1", "Категория 2", "Категория 3"):
            self.category.addItem(category_name)

        form.addRow(QLabel("Название устройства:", self), self.input_device)
        form.addRow(QLabel("Категория объекта:", self), self.category)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        cancel = QPushButton("Выход", self)
        start = QPushButton("Начать измерение", self)

        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(start)
        layout.addLayout(buttons)

        connect_action(cancel.clicked, self.reject)
        connect_action(start.clicked, self._on_start)

    def _on_start(self) -> None:
        if not self.input_device.text().strip():
            _ = QMessageBox.warning(
                self,
                "Внимание",
                "Укажите название проверяемого устройства.",
            )
            return

        self.accept()

    def parameters(self) -> tuple[str, int]:
        return self.input_device.text().strip(), self.category.currentIndex()
