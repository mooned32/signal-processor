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

from core.calculator import calculate_data, load_config
from core.database import save_measurement_to_db
from core.models import AppConfig, CalculationResult, LineType

from .line_template_widget import LineTemplateWidget
from .table_model import MeasurementTableModel, TableGridDelegate


class VoidSignal(Protocol):
    def connect(self, slot: Callable[[], None], /) -> object: ...


class IntSignal(Protocol):
    def connect(self, slot: Callable[[int], None], /) -> object: ...


def connect_action(signal: VoidSignal, slot: Callable[[], None]) -> None:
    _ = signal.connect(slot)


def connect_index(signal: IntSignal, slot: Callable[[int], None]) -> None:
    _ = signal.connect(slot)


class MainWindow(QMainWindow):
    db_path: Path
    device_name: str
    category_index: int
    line_number: int

    file_sn_path: Path | None
    file_n_path: Path | None
    calc_result: CalculationResult | None

    input_file_sn: QLineEdit
    input_file_n: QLineEdit
    radio_current: QRadioButton
    radio_voltage: QRadioButton
    meas_type_group: QButtonGroup
    input_r: QLineEdit
    combo_line: QComboBox
    line_template_widget: LineTemplateWidget
    combo_mode: QComboBox
    btn_calc: QPushButton
    table_view: QTableView
    table_model: MeasurementTableModel
    lbl_status: QLabel
    status_card: QFrame
    btn_save_db: QPushButton

    config: AppConfig
    line_items: list[tuple[LineType, str]]

    def __init__(
        self,
        config_path: Path,
        device_name: str,
        category_index: int,
    ) -> None:
        super().__init__()
        self.config = load_config(config_path)
        self.db_path = config_path.parent / "measurements.db"
        self.device_name = device_name
        self.category_index = category_index
        self.line_number = 1

        self.file_sn_path = None
        self.file_n_path = None
        self.calc_result = None
        self.line_items = []

        self.input_file_sn = QLineEdit()
        self.input_file_n = QLineEdit()
        self.radio_current = QRadioButton("Ток")
        self.radio_voltage = QRadioButton("Напряжение")
        self.meas_type_group = QButtonGroup(self)
        self.input_r = QLineEdit()
        self.combo_line = QComboBox()
        self.line_template_widget = LineTemplateWidget()
        self.combo_mode = QComboBox()
        self.btn_calc = QPushButton("Рассчитать параметры")
        self.table_view = QTableView()
        self.table_model = MeasurementTableModel()
        self.lbl_status = QLabel("Ожидание запуска расчёта")
        self.status_card = QFrame()
        self.btn_save_db = QPushButton("Сохранить измерение")

        self._load_line_templates()
        self._init_ui()
        self._update_window_title()

    def _update_window_title(self) -> None:
        self.setWindowTitle(f"{self.device_name}: (Линия №{self.line_number})")

    def _load_line_templates(self) -> None:
        cfg = self.config
        for name in cfg.lines.symmetrical:
            self.line_items.append(("symmetrical", name))
        for name in cfg.lines.asymmetrical:
            self.line_items.append(("asymmetrical", name))
        for name in cfg.lines.power:
            self.line_items.append(("power", name))

    def _init_ui(self) -> None:
        self.resize(1080, 780)
        self.setMinimumSize(980, 720)

        main_widget = QWidget()
        root_layout = QVBoxLayout(main_widget)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        top_cards_layout = QHBoxLayout()
        top_cards_layout.setSpacing(10)
        top_cards_layout.addWidget(self._create_input_files_card(), stretch=5)
        top_cards_layout.addWidget(self._create_line_control_card(), stretch=5)
        root_layout.addLayout(top_cards_layout)

        root_layout.addWidget(self._create_table_view(), stretch=1)
        root_layout.addLayout(self._create_bottom_bar())

        self.setCentralWidget(main_widget)

    def _create_input_files_card(self) -> QGroupBox:
        box = QGroupBox("Входные спектры и датчик")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Спектр смеси «Сигнал + Шум» (U_сш):"))
        sn_row = QHBoxLayout()
        self.input_file_sn.setReadOnly(True)
        self.input_file_sn.setPlaceholderText("Файл не выбран...")
        btn_sn = QPushButton("Обзор...")
        btn_sn.setFixedWidth(75)
        connect_action(btn_sn.clicked, self._select_file_sn)
        sn_row.addWidget(self.input_file_sn)
        sn_row.addWidget(btn_sn)
        layout.addLayout(sn_row)

        layout.addWidget(QLabel("Спектр собственного шума (U_ш):"))
        n_row = QHBoxLayout()
        self.input_file_n.setReadOnly(True)
        self.input_file_n.setPlaceholderText("Файл не выбран...")
        btn_n = QPushButton("Обзор...")
        btn_n.setFixedWidth(75)
        connect_action(btn_n.clicked, self._select_file_n)
        n_row.addWidget(self.input_file_n)
        n_row.addWidget(btn_n)
        layout.addLayout(n_row)

        row_params = QHBoxLayout()
        row_params.setSpacing(12)

        meas_type_box = QHBoxLayout()
        meas_type_box.addWidget(QLabel("Величина:"))
        self.radio_voltage.setChecked(True)
        self.meas_type_group.addButton(self.radio_current, 1)
        self.meas_type_group.addButton(self.radio_voltage, 2)
        meas_type_box.addWidget(self.radio_voltage)
        meas_type_box.addWidget(self.radio_current)
        row_params.addLayout(meas_type_box)

        r_box = QHBoxLayout()
        r_box.addWidget(QLabel("Сопротивление R:"))
        self.input_r.setPlaceholderText("—")
        self.input_r.setFixedWidth(55)
        r_validator = QDoubleValidator(0.0, 1e9, 4, self)
        r_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.input_r.setValidator(r_validator)
        r_box.addWidget(self.input_r)
        r_box.addWidget(QLabel("Ом"))
        row_params.addLayout(r_box)

        row_params.addStretch()
        layout.addLayout(row_params)
        return box

    def _create_line_control_card(self) -> QGroupBox:
        box = QGroupBox("Параметры линии и расчёт")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Исследуемая линия:"))
        line_row = QHBoxLayout()
        for _, name in self.line_items:
            self.combo_line.addItem(name)
        connect_index(self.combo_line.currentIndexChanged, self._on_line_template_changed)
        self.combo_line.setMinimumWidth(160)
        line_row.addWidget(self.combo_line)

        line_row.addWidget(self.line_template_widget, stretch=1)
        layout.addLayout(line_row)

        if self.line_items:
            self.line_template_widget.set_template(self.line_items[0][1])

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Режим работы:"))
        self.combo_mode.setFixedWidth(90)
        self._load_operation_modes()
        mode_row.addWidget(self.combo_mode)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        layout.addStretch()

        self.btn_calc.setFixedHeight(34)
        self.btn_calc.setStyleSheet(
            "QPushButton { font-size: 12px; font-weight: 500; background-color: #0F6CBD; "
            + "color: white; border: none; border-radius: 4px; } "
            + "QPushButton:hover { background-color: #0D5A9B; } "
            + "QPushButton:pressed { background-color: #0B487B; }"
        )
        connect_action(self.btn_calc.clicked, self._run_calculation)
        layout.addWidget(self.btn_calc)

        return box

    def _load_operation_modes(self) -> None:
        for mode in self.config.operation_modes:
            self.combo_mode.addItem(mode)

    def _create_table_view(self) -> QTableView:
        self.table_view.setModel(self.table_model)
        self.table_view.setItemDelegate(TableGridDelegate(self.table_view))
        self.table_view.setShowGrid(False)

        v_header = self.table_view.verticalHeader()
        if v_header is not None:
            v_header.setVisible(False)
            v_header.setDefaultSectionSize(23)

        self.table_view.setAlternatingRowColors(True)
        self.table_view.setStyleSheet(
            "QTableView { border: 1px solid #CBD5E1; alternate-background-color: #F8FAFC; "
            + "selection-background-color: #E2E8F0; selection-color: black; font-size: 12px; }\n"
            + "QHeaderView::section { background-color: #F8FAFC; "
            + "font-weight: 500; font-size: 12px; "
            + "border: 1px solid #CBD5E1; padding: 3px 6px; color: #475569; }"
        )

        h_header = self.table_view.horizontalHeader()
        if h_header is not None:
            h_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        return self.table_view

    def _create_bottom_bar(self) -> QHBoxLayout:
        bottom_layout = QHBoxLayout()

        self.status_card.setStyleSheet(
            "QFrame { background: #F8FAFC; border: 1px solid #E2E8F0; "
            + "border-radius: 4px; padding: 2px 10px; }"
        )
        sc_layout = QHBoxLayout(self.status_card)
        sc_layout.setContentsMargins(6, 4, 6, 4)

        self.lbl_status.setStyleSheet("font-size: 12px; color: #64748B;")
        sc_layout.addWidget(self.lbl_status)
        bottom_layout.addWidget(self.status_card, stretch=1)

        self.btn_save_db.setEnabled(False)
        self.btn_save_db.setFixedHeight(34)
        self.btn_save_db.setStyleSheet(
            "QPushButton { font-size: 12px; font-weight: 500; background-color: #0F766E; "
            + "color: white; border: none; border-radius: 4px; padding: 0 16px; } "
            + "QPushButton:hover { background-color: #115E59; } "
            + "QPushButton:disabled { background-color: #E2E8F0; color: #94A3B8; }"
        )
        connect_action(self.btn_save_db.clicked, self._save_to_database)
        bottom_layout.addWidget(self.btn_save_db)

        return bottom_layout

    def _on_line_template_changed(self, idx: int) -> None:
        if 0 <= idx < len(self.line_items):
            template_str = self.line_items[idx][1]
            self.line_template_widget.set_template(template_str)

    def _select_file_sn(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл смеси (Сигнал + Шум)",
            "",
            "Текстовые спектры (*.txt);;Все файлы (*.*)",
        )
        if file:
            self.file_sn_path = Path(file)
            self.input_file_sn.setText(self.file_sn_path.name)
            self.input_file_sn.setToolTip(str(self.file_sn_path))

    def _select_file_n(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл собственного шума",
            "",
            "Текстовые спектры (*.txt);;Все файлы (*.*)",
        )
        if file:
            self.file_n_path = Path(file)
            self.input_file_n.setText(self.file_n_path.name)
            self.input_file_n.setToolTip(str(self.file_n_path))

    def _run_calculation(self) -> None:
        if not self.file_sn_path or not self.file_n_path:
            _ = QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите оба файла спектров перед расчётом.",
            )
            return

        if not self.line_template_widget.is_valid():
            _ = QMessageBox.warning(
                self,
                "Предупреждение",
                "Заполните параметры исследуемой линии.",
            )
            self.line_template_widget.focus_first_empty()
            return

        idx = self.combo_line.currentIndex()
        line_type: LineType = (
            self.line_items[idx][0] if 0 <= idx < len(self.line_items) else "power"
        )

        r_val: float | None = None
        if self.input_r.text().strip():
            try:
                r_val = float(self.input_r.text().replace(",", "."))
            except ValueError:
                r_val = None

        try:
            result = calculate_data(
                file_sn_path=self.file_sn_path,
                file_n_path=self.file_n_path,
                config=self.config,
                category_index=self.category_index,
                line_type=line_type,
                r_param=r_val,
            )
            self.calc_result = result
            self.table_model.update_data(result.points)

            header = self.table_view.horizontalHeader()
            if header is not None:
                header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

            if result.has_violations:
                self.lbl_status.setText("Обнаружены нарушения: Подтверждено АЭП")
                self.lbl_status.setStyleSheet("font-size: 12px; color: #991B1B; font-weight: 500;")
                self.status_card.setStyleSheet(
                    "QFrame { background: #FEF2F2; border: 1px solid #FECACA; "
                    + "border-radius: 4px; padding: 2px 10px; }"
                )
            else:
                self.lbl_status.setText("Нарушения не обнаружены")
                self.lbl_status.setStyleSheet("font-size: 12px; color: #166534; font-weight: 500;")
                self.status_card.setStyleSheet(
                    "QFrame { background: #F0FDF4; border: 1px solid #BBF7D0; "
                    + "border-radius: 4px; padding: 2px 10px; }"
                )

            self.btn_save_db.setEnabled(True)

        except Exception as e:
            _ = QMessageBox.critical(self, "Ошибка расчёта", str(e))

    def _save_to_database(self) -> None:
        if self.calc_result is None:
            return

        idx = self.combo_line.currentIndex()
        line_type: LineType = (
            self.line_items[idx][0] if 0 <= idx < len(self.line_items) else "power"
        )
        line_full_name = self.line_template_widget.get_full_name()
        operation_mode = self.combo_mode.currentText()
        meas_type = self.meas_type_group.checkedId()

        r_val: float | None = None
        if self.input_r.text().strip():
            try:
                r_val = float(self.input_r.text().replace(",", "."))
            except ValueError:
                r_val = None

        try:
            _ = save_measurement_to_db(
                db_path=self.db_path,
                device_name=self.device_name,
                category=self.category_index + 1,
                line_number=self.line_number,
                line_name=line_full_name,
                line_type=line_type,
                operation_mode=operation_mode,
                measurement_type=meas_type,
                parameter_r=r_val,
                has_violations=self.calc_result.has_violations,
                points=self.calc_result.points,
            )

            _ = QMessageBox.information(
                self,
                "Успех",
                f"Измерение для линии «{line_full_name}» сохранено в базу данных.",
            )

            self._reset_form_for_next_line()

        except Exception as e:
            _ = QMessageBox.critical(self, "Ошибка сохранения", str(e))

    def _reset_form_for_next_line(self) -> None:
        self.file_sn_path = None
        self.file_n_path = None
        self.input_file_sn.clear()
        self.input_file_n.clear()
        self.input_r.clear()
        self.line_template_widget.clear_inputs()

        self.calc_result = None
        self.table_model.update_data([])

        self.lbl_status.setText("Ожидание запуска расчёта")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #64748B;")
        self.status_card.setStyleSheet(
            "QFrame { background: #F8FAFC; border: 1px solid #E2E8F0; "
            + "border-radius: 4px; padding: 2px 10px; }"
        )
        self.btn_save_db.setEnabled(False)

        self.line_number += 1
        self._update_window_title()
