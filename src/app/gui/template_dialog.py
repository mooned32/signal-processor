from datetime import datetime

from PyQt6.QtWidgets import (
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


class TemplateFieldsDialog(QDialog):
    """Диалог динамического ввода полей для шаблона Word."""

    _fields_inputs: dict[str, QLineEdit]

    def __init__(
        self,
        fields_config: dict[str, object],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Заполнение данных отчёта")
        self.resize(450, 200 + len(fields_config) * 35)
        self._fields_inputs = {}

        layout = QVBoxLayout(self)

        info_lbl = QLabel("Заполните данные для формирования официального документа:")
        info_lbl.setStyleSheet("font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(info_lbl)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Текущая дата по умолчанию
        current_date_str = datetime.now().strftime("%d.%m.%Y")

        for key, label_obj in fields_config.items():
            label_text = str(label_obj)
            line_edit = QLineEdit()

            # Предзаполнение даты
            if "DATE" in key.upper():
                line_edit.setText(current_date_str)
            elif "ACT" in key.upper():
                line_edit.setText("001")

            form_layout.addRow(QLabel(f"{label_text}:"), line_edit)
            self._fields_inputs[key] = line_edit

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_submit = QPushButton("Сформировать документ...")
        btn_submit.setFixedHeight(34)
        btn_submit.setStyleSheet("font-weight: bold; background-color: #2563EB; color: white;")
        _ = btn_submit.clicked.connect(self._on_submit)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setFixedHeight(34)
        _ = btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_submit)
        layout.addLayout(btn_layout)

    def _on_submit(self) -> None:
        # Проверка на пустые поля
        for key, edit in self._fields_inputs.items():
            if not edit.text().strip():
                _ = QMessageBox.warning(
                    self,
                    "Внимание",
                    f"Пожалуйста, заполните поле '{key}'!",
                )
                return
        self.accept()

    def get_data(self) -> dict[str, str]:
        return {key: edit.text().strip() for key, edit in self._fields_inputs.items()}
