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


class StartupDialog(QDialog):
    """Стартовое окно выбора устройства и категории измерений."""

    input_device: QLineEdit
    combo_category: QComboBox

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Параметры объекта измерения")
        self.setFixedSize(420, 200)

        layout = QVBoxLayout(self)

        title = QLabel("Введите параметры для начала серии измерений:")
        title.setStyleSheet("font-weight: bold; font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.input_device = QLineEdit("Телевизор")
        self.combo_category = QComboBox()
        self.combo_category.addItems(["Категория 1", "Категория 2", "Категория 3"])

        form.addRow(QLabel("Название устройства:"), self.input_device)
        form.addRow(QLabel("Категория объекта:"), self.combo_category)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_start = QPushButton("Начать измерение")
        btn_start.setFixedHeight(34)
        btn_start.setStyleSheet("font-weight: bold; background-color: #2563EB; color: white;")
        _ = btn_start.clicked.connect(self._on_start)

        btn_cancel = QPushButton("Выход")
        btn_cancel.setFixedHeight(34)
        _ = btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_start)
        layout.addLayout(btn_layout)

    def _on_start(self) -> None:
        name = self.input_device.text().strip()
        if not name:
            _ = QMessageBox.warning(self, "Внимание", "Введите название проверяемого устройства!")
            return
        self.accept()

    def get_params(self) -> tuple[str, int]:
        """Возвращает (имя устройства, индекс категории 0..2)."""
        return self.input_device.text().strip(), self.combo_category.currentIndex()
