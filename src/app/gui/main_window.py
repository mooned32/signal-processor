from pathlib import Path
from typing import cast

import pandas as pd
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QGridLayout,
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

from ..core.calculator import calculate_data, load_config
from ..core.database import save_measurement_to_db
from .table_model import PandasTableModel


class MainWindow(QMainWindow):
    config_path: Path
    db_path: Path
    device_name: str
    category_index: int
    line_number: int

    file_sn_path: Path | None
    file_n_path: Path | None
    current_df: pd.DataFrame | None
    violations_mask: list[bool] | None
    has_violations: bool

    # UI Widgets
    lbl_sn: QLabel
    lbl_n: QLabel
    radio_current: QRadioButton
    radio_voltage: QRadioButton
    meas_type_group: QButtonGroup
    input_r: QLineEdit
    combo_line: QComboBox
    input_line_name: QLineEdit
    combo_mode: QComboBox
    btn_calc: QPushButton
    table_view: QTableView
    table_model: PandasTableModel
    lbl_status: QLabel
    btn_save_db: QPushButton

    # Данные линий из конфига: список кортежей (line_type, display_name)
    line_items: list[tuple[str, str]]

    def __init__(
        self,
        config_path: Path,
        device_name: str,
        category_index: int,
    ) -> None:
        super().__init__()
        self.config_path = config_path
        self.db_path = config_path.parent / "measurements.db"
        self.device_name = device_name
        self.category_index = category_index
        self.line_number = 1

        self.file_sn_path = None
        self.file_n_path = None
        self.current_df = None
        self.violations_mask = None
        self.has_violations = False
        self.line_items = []

        self._init_line_data()
        self._init_ui()
        self._update_window_title()

    def _update_window_title(self) -> None:
        self.setWindowTitle(f"{self.device_name}: линия №{self.line_number}")

    def _init_line_data(self) -> None:
        """Считывает шаблоны линий из конфига."""
        try:
            cfg = load_config(self.config_path)
            lines_sec = cast(dict[str, object], cfg.get("line", {}))
            for line_type, sub_val in lines_sec.items():
                if isinstance(sub_val, dict):
                    names = cast(list[object], sub_val.get("names", []))
                    for n in names:
                        self.line_items.append((line_type, str(n)))
        except Exception:
            self.line_items = [("power", "Заземление"), ("symmetrical", "ЛВС, пара {} - {}")]

    def _init_ui(self) -> None:
        self.resize(950, 700)
        main_widget = QWidget()
        root_layout = QVBoxLayout(main_widget)
        root_layout.setSpacing(10)

        # Верхняя панель управления (Сетка по эскизу Plan.svg)
        controls_box = QGroupBox("Параметры текущего измерения")
        controls_grid = QGridLayout(controls_box)
        controls_grid.setSpacing(10)

        # ЛЕВАЯ КОЛОНКА
        # Файл 1
        self.lbl_sn = QLabel("Файл 1: Не выбран")
        btn_sn = QPushButton("Обзор...")
        btn_sn.setFixedWidth(85)
        _ = btn_sn.clicked.connect(self._select_file_sn)
        controls_grid.addWidget(self.lbl_sn, 0, 0)
        controls_grid.addWidget(btn_sn, 0, 1)

        # Файл 2
        self.lbl_n = QLabel("Файл 2: Не выбран")
        btn_n = QPushButton("Обзор...")
        btn_n.setFixedWidth(85)
        _ = btn_n.clicked.connect(self._select_file_n)
        controls_grid.addWidget(self.lbl_n, 1, 0)
        controls_grid.addWidget(btn_n, 1, 1)

        # Ток / Напряжение
        meas_layout = QHBoxLayout()
        self.radio_current = QRadioButton("Ток")
        self.radio_voltage = QRadioButton("Напряжение")
        self.radio_voltage.setChecked(True)
        self.meas_type_group = QButtonGroup(self)
        self.meas_type_group.addButton(self.radio_current, 1)
        self.meas_type_group.addButton(self.radio_voltage, 2)
        meas_layout.addWidget(self.radio_current)
        meas_layout.addWidget(self.radio_voltage)
        controls_grid.addLayout(meas_layout, 2, 0, 1, 2)

        # Параметр R
        r_layout = QHBoxLayout()
        r_layout.addWidget(QLabel("Введите параметр R:"))
        self.input_r = QLineEdit()
        self.input_r.setPlaceholderText("Ом")
        r_validator = QDoubleValidator(0.0, 1e9, 4, self)
        r_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.input_r.setValidator(r_validator)
        r_layout.addWidget(self.input_r)
        controls_grid.addLayout(r_layout, 3, 0, 1, 2)

        # ПРАВАЯ КОЛОНКА
        # Исследуемая линия
        controls_grid.addWidget(QLabel("Исследуемая линия:"), 0, 2)
        line_select_box = QHBoxLayout()
        self.combo_line = QComboBox()
        for _, name in self.line_items:
            self.combo_line.addItem(name)
        _ = self.combo_line.currentIndexChanged.connect(self._on_line_template_changed)
        line_select_box.addWidget(self.combo_line)

        self.input_line_name = QLineEdit()
        if self.line_items:
            self.input_line_name.setText(self.line_items[0][1])
        line_select_box.addWidget(self.input_line_name)
        controls_grid.addLayout(line_select_box, 0, 3)

        # Режим работы
        controls_grid.addWidget(QLabel("Режим работы:"), 1, 2)
        self.combo_mode = QComboBox()
        try:
            cfg = load_config(self.config_path)
            modes_sec = cast(dict[str, object], cfg.get("operation_modes", {}))
            modes = cast(list[object], modes_sec.get("modes", ["ХХ", "ДР", "РР"]))
            self.combo_mode.addItems([str(m) for m in modes])
        except Exception:
            self.combo_mode.addItems(["ХХ", "ДР", "РР"])
        controls_grid.addWidget(self.combo_mode, 1, 3)

        # Кнопка Рассчитать
        self.btn_calc = QPushButton("Рассчитать")
        self.btn_calc.setFixedHeight(38)
        self.btn_calc.setStyleSheet(
            "font-weight: bold; font-size: 13px; background-color: #E2E8F0;"
        )
        _ = self.btn_calc.clicked.connect(self._run_calculation)
        controls_grid.addWidget(self.btn_calc, 2, 2, 2, 2)

        root_layout.addWidget(controls_box)

        # Таблица результатов
        self.table_view = QTableView()
        self.table_model = PandasTableModel()
        self.table_view.setModel(self.table_model)
        header = self.table_view.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        root_layout.addWidget(self.table_view)

        # Подвал (Статус и кнопка Внести в БД)
        bottom_layout = QHBoxLayout()
        self.lbl_status = QLabel("Статус: Ожидание расчёта")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #4B5563;")

        self.btn_save_db = QPushButton("Внести данные в БД")
        self.btn_save_db.setEnabled(False)
        self.btn_save_db.setFixedHeight(36)
        self.btn_save_db.setStyleSheet(
            "font-weight: bold; background-color: #10B981; color: white; padding: 0 16px;"
        )
        _ = self.btn_save_db.clicked.connect(self._save_to_database)

        bottom_layout.addWidget(self.lbl_status, stretch=1)
        bottom_layout.addWidget(self.btn_save_db)
        root_layout.addLayout(bottom_layout)

        self.setCentralWidget(main_widget)

    def _on_line_template_changed(self, idx: int) -> None:
        if 0 <= idx < len(self.line_items):
            self.input_line_name.setText(self.line_items[idx][1])

    def _select_file_sn(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл 1 (Сигнал + Шум)", "", "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if file:
            self.file_sn_path = Path(file)
            self.lbl_sn.setText(f"Файл 1: {self.file_sn_path.name}")

    def _select_file_n(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл 2 (Шум)", "", "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if file:
            self.file_n_path = Path(file)
            self.lbl_n.setText(f"Файл 2: {self.file_n_path.name}")

    def _run_calculation(self) -> None:
        if not self.file_sn_path or not self.file_n_path:
            _ = QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите оба файла!")
            return

        idx = self.combo_line.currentIndex()
        line_type = self.line_items[idx][0] if 0 <= idx < len(self.line_items) else "power"

        r_val = None
        if self.input_r.text().strip():
            try:
                r_val = float(self.input_r.text().replace(",", "."))
            except ValueError:
                pass

        try:
            df, mask, violations = calculate_data(
                file_sn_path=self.file_sn_path,
                file_n_path=self.file_n_path,
                config_path=self.config_path,
                category_index=self.category_index,
                line_type=line_type,
                r_param=r_val,
            )
            self.current_df = df
            self.violations_mask = mask
            self.has_violations = violations

            self.table_model.update_data(df, mask)

            if violations:
                self.lbl_status.setText("1. Обнаружены нарушения: Подтверждено АЭП")
                self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #B91C1C;")
            else:
                self.lbl_status.setText("2. Нарушения не обнаружены: Не подтверждено АЭП")
                self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #15803D;")

            self.btn_save_db.setEnabled(True)

        except Exception as e:
            _ = QMessageBox.critical(self, "Ошибка расчёта", str(e))

    def _save_to_database(self) -> None:
        if self.current_df is None or self.violations_mask is None:
            return

        idx = self.combo_line.currentIndex()
        line_type = self.line_items[idx][0] if 0 <= idx < len(self.line_items) else "power"
        line_display_name = self.input_line_name.text().strip() or self.combo_line.currentText()
        operation_mode = self.combo_mode.currentText()
        meas_type = self.meas_type_group.checkedId()  # 1: Ток, 2: Напряжение

        r_val = None
        if self.input_r.text().strip():
            try:
                r_val = float(self.input_r.text().replace(",", "."))
            except ValueError:
                pass

        try:
            _ = save_measurement_to_db(
                db_path=self.db_path,
                device_name=self.device_name,
                category=self.category_index + 1,
                line_number=self.line_number,
                line_name=line_display_name,
                line_type=line_type,
                operation_mode=operation_mode,
                measurement_type=meas_type,
                parameter_r=r_val,
                has_violations=self.has_violations,
                df_points=self.current_df,
                violations_mask=self.violations_mask,
            )

            _ = QMessageBox.information(
                self,
                "Успех",
                f"Измерение для линии №{self.line_number} успешно занесено в базу данных!",
            )

            # Сброс полей по схеме Plan.svg
            self.file_sn_path = None
            self.file_n_path = None
            self.lbl_sn.setText("Файл 1: Не выбран")
            self.lbl_n.setText("Файл 2: Не выбран")
            self.input_r.clear()
            self.current_df = None
            self.violations_mask = None
            self.table_model.update_data(pd.DataFrame(), None)
            self.lbl_status.setText("Статус: Ожидание расчёта")
            self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #4B5563;")
            self.btn_save_db.setEnabled(False)

            # Инкремент линии N + 1
            self.line_number += 1
            self._update_window_title()

        except Exception as e:
            _ = QMessageBox.critical(self, "Ошибка сохранения в БД", str(e))
