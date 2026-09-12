from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


class LineTemplateWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._template_string = ""
        self._inputs: list[QLineEdit] = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def set_template(self, value: str) -> None:
        self._template_string = value
        self._clear_layout()

        parts = value.split("{}")
        placeholder_count = len(parts) - 1
        if placeholder_count <= 0:
            self.setVisible(False)
            return

        self.setVisible(True)
        previous_input: QLineEdit | None = None
        self._layout.addWidget(QLabel("Параметры:", self))

        for index, text in enumerate(parts):
            clean_text = text.strip()
            if clean_text:
                self._layout.addWidget(QLabel(clean_text, self))

            if index < placeholder_count:
                input_widget = QLineEdit(self)
                input_widget.setFixedSize(46, 26)
                input_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                input_widget.setPlaceholderText("—")
                self._layout.addWidget(input_widget)
                self._inputs.append(input_widget)

                if previous_input is not None:
                    QWidget.setTabOrder(previous_input, input_widget)
                previous_input = input_widget

        self._layout.addStretch()
        if self._inputs:
            self._inputs[0].setFocus()

    def _clear_layout(self) -> None:
        self._inputs.clear()
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def is_valid(self) -> bool:
        if not self.isVisible() or not self._inputs:
            return True
        return all(input_widget.text().strip() for input_widget in self._inputs)

    def full_name(self) -> str:
        if not self.isVisible() or not self._inputs:
            return self._template_string
        result = self._template_string
        for input_widget in self._inputs:
            result = result.replace("{}", input_widget.text().strip(), 1)
        return result

    def focus_first_empty(self) -> None:
        if not self.isVisible():
            return
        for input_widget in self._inputs:
            if not input_widget.text().strip():
                input_widget.setFocus()
                input_widget.selectAll()
                return

    def clear_inputs(self) -> None:
        for input_widget in self._inputs:
            input_widget.clear()
        if self._inputs:
            self._inputs[0].setFocus()
