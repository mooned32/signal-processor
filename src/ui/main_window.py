import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from calculation.calculation import calculate
from calculation.models import AppConfig, CalculationResult, LineType, MeasurementKind
from database.database import save_measurement
from ui.file_drop_line_edit import FileDropLineEdit
from ui.line_template_widget import LineTemplateWidget
from ui.table_model import MeasurementTableModel


class VoidSignal(Protocol):
    def connect(self, slot: Callable[[], None], /) -> object: ...


class IntSignal(Protocol):
    def connect(self, slot: Callable[[int], None], /) -> object: ...


def connect_action(signal: VoidSignal, slot: Callable[[], None]) -> None:
    _ = signal.connect(slot)


def connect_index(signal: IntSignal, slot: Callable[[int], None]) -> None:
    _ = signal.connect(slot)


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: AppConfig,
        device_name: str,
        category_index: int,
        base_directory: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.device_name = device_name
        self.category_index = category_index
        self.line_number = 1
        self.base_directory = base_directory
        self.signal_noise_path: Path | None = None
        self.noise_path: Path | None = None
        self.calculation_result: CalculationResult | None = None
        self.line_items: list[tuple[LineType, str]] = []

        self.signal_noise_edit = FileDropLineEdit(
            placeholder="Файл не выбран...",
            on_file_dropped=self._set_signal_noise_file,
            parent=self,
        )
        self.noise_edit = FileDropLineEdit(
            placeholder="Файл не выбран...",
            on_file_dropped=self._set_noise_file,
            parent=self,
        )
        self.current_radio = QRadioButton("Ток", self)
        self.voltage_radio = QRadioButton("Напряжение", self)
        self.measurement_group = QButtonGroup(self)
        self.resistance_edit = QLineEdit(self)
        self.line_combo = QComboBox(self)
        self.line_template = LineTemplateWidget(self)
        self.operation_mode = QComboBox(self)
        self.calculate_button = QPushButton("Рассчитать параметры", self)
        self.table_view = QTableView(self)
        self.table_model = MeasurementTableModel(self)
        self.status_label = QLabel("Ожидание запуска расчёта", self)
        self.status_card = QFrame(self)
        self.save_button = QPushButton("Сохранить измерение", self)

        self._load_line_templates()
        self._initialize_ui()
        self._load_operation_modes()
        self._update_window_title()

    def _update_window_title(self) -> None:
        self.setWindowTitle(f"{self.device_name}: (Линия №{self.line_number})")

    def _load_line_templates(self) -> None:
        for name in self.config.lines.symmetrical:
            self.line_items.append(("symmetrical", name))
        for name in self.config.lines.asymmetrical:
            self.line_items.append(("asymmetrical", name))
        for name in self.config.lines.power:
            self.line_items.append(("power", name))

    def _initialize_ui(self) -> None:
        self.resize(1080, 780)
        self.setMinimumSize(980, 720)

        main_widget = QWidget(self)
        root = QVBoxLayout(main_widget)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        cards.addWidget(self._create_input_files_card(), 1)
        cards.addWidget(self._create_line_control_card(), 1)
        root.addLayout(cards)
        root.addWidget(self._create_table_view(), 1)
        root.addLayout(self._create_bottom_bar())
        self.setCentralWidget(main_widget)

    def _create_input_files_card(self) -> QGroupBox:
        box = QGroupBox("Входные спектры и датчик", self)
        layout = QVBoxLayout(box)
        layout.addWidget(QLabel("Спектр смеси «Сигнал + Шум»:", box))

        signal_row = QHBoxLayout()
        signal_button = QPushButton("Обзор...", box)
        signal_row.addWidget(self.signal_noise_edit)
        signal_row.addWidget(signal_button)
        layout.addLayout(signal_row)

        layout.addWidget(QLabel("Спектр собственного шума:", box))
        noise_row = QHBoxLayout()
        noise_button = QPushButton("Обзор...", box)
        noise_row.addWidget(self.noise_edit)
        noise_row.addWidget(noise_button)
        layout.addLayout(noise_row)

        params_row = QHBoxLayout()
        params_row.addWidget(QLabel("Величина:", box))
        self.voltage_radio.setChecked(True)
        self.measurement_group.addButton(self.current_radio, 1)
        self.measurement_group.addButton(self.voltage_radio, 2)
        params_row.addWidget(self.voltage_radio)
        params_row.addWidget(self.current_radio)
        params_row.addSpacing(18)
        params_row.addWidget(QLabel("Сопротивление R:", box))
        self.resistance_edit.setFixedWidth(80)
        self.resistance_edit.setValidator(QDoubleValidator(0.0, 1e9, 4, self.resistance_edit))
        params_row.addWidget(self.resistance_edit)
        params_row.addWidget(QLabel("Ом", box))
        params_row.addStretch()
        layout.addLayout(params_row)

        connect_action(signal_button.clicked, self._select_signal_noise_file)
        connect_action(noise_button.clicked, self._select_noise_file)
        return box

    def _create_line_control_card(self) -> QGroupBox:
        box = QGroupBox("Параметры линии и расчёт", self)
        layout = QVBoxLayout(box)
        layout.addWidget(QLabel("Исследуемая линия:", box))

        line_row = QHBoxLayout()
        for _, name in self.line_items:
            self.line_combo.addItem(name)
        connect_index(self.line_combo.currentIndexChanged, self._on_line_changed)
        line_row.addWidget(self.line_combo)
        line_row.addWidget(self.line_template, 1)
        layout.addLayout(line_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Режим работы:", box))
        mode_row.addWidget(self.operation_mode)
        mode_row.addStretch()
        layout.addLayout(mode_row)
        layout.addStretch()
        connect_action(self.calculate_button.clicked, self._run_calculation)
        layout.addWidget(self.calculate_button)

        if self.line_items:
            self.line_template.set_template(self.line_items[0][1])
        return box

    def _load_operation_modes(self) -> None:
        for mode in self.config.operation_modes:
            self.operation_mode.addItem(mode)

    def _create_table_view(self) -> QTableView:
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        header = self.table_view.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return self.table_view

    def _create_bottom_bar(self) -> QHBoxLayout:
        bottom = QHBoxLayout()
        bottom.addWidget(self.status_card, 1)
        status_layout = QHBoxLayout(self.status_card)
        status_layout.addWidget(self.status_label)
        self.save_button.setEnabled(False)
        bottom.addWidget(self.save_button)
        connect_action(self.save_button.clicked, self._save_to_database)
        return bottom

    def _on_line_changed(self, index: int) -> None:
        if 0 <= index < len(self.line_items):
            self.line_template.set_template(self.line_items[index][1])

    def _set_signal_noise_file(self, path: Path) -> None:
        resolved = path.resolve()
        self.signal_noise_path = resolved
        self.signal_noise_edit.setText(str(resolved))
        self.signal_noise_edit.setToolTip(str(resolved))

    def _set_noise_file(self, path: Path) -> None:
        resolved = path.resolve()
        self.noise_path = resolved
        self.noise_edit.setText(str(resolved))
        self.noise_edit.setToolTip(str(resolved))

    def _select_signal_noise_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл смеси (Сигнал + Шум)",
            "",
            "Текстовые спектры (*.txt);;Все файлы (*.*)",
        )
        if path:
            self._set_signal_noise_file(Path(path))

    def _select_noise_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл собственного шума",
            "",
            "Текстовые спектры (*.txt);;Все файлы (*.*)",
        )
        if path:
            self._set_noise_file(Path(path))

    def _current_line_type(self) -> LineType:
        index = self.line_combo.currentIndex()
        if 0 <= index < len(self.line_items):
            return self.line_items[index][0]
        return "power"

    def _current_measurement_type(self) -> MeasurementKind:
        if self.current_radio.isChecked():
            return "current"
        return "voltage"

    def _read_resistance(self) -> float | None:
        text = self.resistance_edit.text().strip()
        if not text:
            return None
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return None

    def _run_calculation(self) -> None:
        if self.signal_noise_path is None or self.noise_path is None:
            _ = QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите оба файла спектров перед расчётом.",
            )
            return

        if not self.line_template.is_valid():
            _ = QMessageBox.warning(
                self,
                "Предупреждение",
                "Заполните параметры исследуемой линии.",
            )
            self.line_template.focus_first_empty()
            return

        measurement_type = self._current_measurement_type()
        resistance = self._read_resistance()

        try:
            result = calculate(
                signal_noise_path=self.signal_noise_path,
                noise_path=self.noise_path,
                config=self.config,
                category_index=self.category_index,
                line_type=self._current_line_type(),
                measurement_type=measurement_type,
                resistance=resistance,
            )
        except (FileNotFoundError, ValueError) as error:
            _ = QMessageBox.critical(self, "Ошибка расчёта", str(error))
            return

        self.calculation_result = result
        self.table_model.update_data(result.points, result.measurement_type)
        header = self.table_view.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._update_status(result)
        self.save_button.setEnabled(True)

    def _update_status(self, result: CalculationResult) -> None:
        if result.has_violations:
            self.status_label.setText("Обнаружены нарушения: Подтверждено АЭП")
        else:
            self.status_label.setText("Нарушения не обнаружены")

    def _save_to_database(self) -> None:
        if self.calculation_result is None:
            return

        index = self.line_combo.currentIndex()
        line_name = self.line_template.full_name()
        mode = self.operation_mode.currentText()
        resistance = self._read_resistance()

        try:
            save_measurement(
                db_path=self.base_directory / "measurements.db",
                device_name=self.device_name,
                category=self.category_index + 1,
                line_number=self.line_number,
                line_name=line_name,
                line_type=self._current_line_type() if index >= 0 else "power",
                operation_mode=mode,
                measurement_type=self.measurement_group.checkedId(),
                resistance=resistance,
                result=self.calculation_result,
            )
        except (OSError, sqlite3.Error, RuntimeError) as error:
            _ = QMessageBox.critical(self, "Ошибка сохранения", str(error))
            return

        _ = QMessageBox.information(self, "Успех", "Измерение сохранено в базу данных.")
        self.line_number += 1
        self._update_window_title()
        self.calculation_result = None
        self.table_model.clear()
        self.save_button.setEnabled(False)
