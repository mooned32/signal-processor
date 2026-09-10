from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


class LineTemplateWidget(QWidget):
    """
    Составной виджет для изменяемых параметров шаблона линии.
    Скрывается, если в шаблоне отсутствуют фигурные скобки.
    """

    _template_str: str
    _input_slots: list[QLineEdit]
    _layout: QHBoxLayout

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._template_str = ""
        self._input_slots = []

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def set_template(self, template_str: str) -> None:
        self._template_str = template_str
        self._clear_layout()

        parts = template_str.split("{}")
        num_slots = len(parts) - 1

        if num_slots <= 0:
            self.setVisible(False)
            return

        self.setVisible(True)
        prev_input: QLineEdit | None = None

        lbl_prefix = QLabel("Параметры:", self)
        lbl_prefix.setStyleSheet("color: #64748B; font-size: 12px;")
        self._layout.addWidget(lbl_prefix)

        for idx, text_part in enumerate(parts):
            clean_part = text_part.strip()
            if clean_part:
                lbl = QLabel(clean_part, self)
                lbl.setStyleSheet("font-size: 13px; color: #334155;")
                self._layout.addWidget(lbl)

            if idx < num_slots:
                slot_input = QLineEdit(self)
                slot_input.setFixedWidth(46)
                slot_input.setFixedHeight(26)
                slot_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
                slot_input.setPlaceholderText("—")
                slot_input.setStyleSheet(
                    "QLineEdit { border: 1px solid #CBD5E1; border-radius: 4px; "
                    + "background: white; font-size: 12px; color: #1E293B; } "
                    + "QLineEdit:focus { border: 1px solid #0F6CBD; }"
                )
                self._layout.addWidget(slot_input)
                self._input_slots.append(slot_input)

                if prev_input is not None:
                    QWidget.setTabOrder(prev_input, slot_input)
                prev_input = slot_input

        self._layout.addStretch()
        self.focus_first()

    def _clear_layout(self) -> None:
        self._input_slots.clear()
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def is_valid(self) -> bool:
        if not self.isVisible() or not self._input_slots:
            return True
        return all(bool(slot.text().strip()) for slot in self._input_slots)

    def get_full_name(self) -> str:
        if not self._input_slots or not self.isVisible():
            return self._template_str

        values = [slot.text().strip() for slot in self._input_slots]
        try:
            return self._template_str.format(*values)
        except (IndexError, ValueError):
            return self._template_str

    def focus_first_empty(self) -> None:
        if not self.isVisible():
            return
        for slot in self._input_slots:
            if not slot.text().strip():
                slot.setFocus()
                slot.selectAll()
                return

    def focus_first(self) -> None:
        if self.isVisible() and self._input_slots:
            self._input_slots[0].setFocus()

    def clear_inputs(self) -> None:
        for slot in self._input_slots:
            slot.clear()
        self.focus_first()
