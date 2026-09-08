from pathlib import Path

import pandas as pd
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
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

from ..core.calculator import calculate_data
from .table_model import PandasTableModel


class MainWindow(QMainWindow):
    config_path: Path
    file_sn_path: Path | None
    file_n_path: Path | None
    current_df: pd.DataFrame | None
    lbl_sn: QLabel
    lbl_n: QLabel
    input_z: QLineEdit
    mode_group: QButtonGroup
    radio_modes: list[QRadioButton]
    btn_calc: QPushButton
    table_view: QTableView
    table_model: PandasTableModel
    lbl_w: QLabel

    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.file_sn_path = None
        self.file_n_path = None
        self.current_df = None

        self.setWindowTitle("Анализатор спектральных сигналов")
        self.resize(920, 650)
        self._init_ui()

    def _init_ui(self) -> None:
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)

        # Выбор Файла 1 (Сигнал + Шум)
        sn_layout = QHBoxLayout()
        self.lbl_sn = QLabel("Файл 1 (Сигнал + Шум): Не выбран")
        btn_sn = QPushButton("Обзор...")
        _ = btn_sn.clicked.connect(self._select_file_sn)
        sn_layout.addWidget(self.lbl_sn, stretch=1)
        sn_layout.addWidget(btn_sn)
        layout.addLayout(sn_layout)

        # Выбор Файла 2 (Шум)
        n_layout = QHBoxLayout()
        self.lbl_n = QLabel("Файл 2 (Шум): Не выбран")
        btn_n = QPushButton("Обзор...")
        _ = btn_n.clicked.connect(self._select_file_n)
        n_layout.addWidget(self.lbl_n, stretch=1)
        n_layout.addWidget(btn_n)
        layout.addLayout(n_layout)

        # Панель параметров
        params_layout = QHBoxLayout()

        box_modes = QGroupBox("Выбор режима работы")
        modes_inner = QHBoxLayout(box_modes)
        self.mode_group = QButtonGroup(self)
        self.radio_modes = [
            QRadioButton("Режим 1"),
            QRadioButton("Режим 2"),
            QRadioButton("Режим 3"),
        ]
        self.radio_modes[0].setChecked(True)
        for idx, r_btn in enumerate(self.radio_modes):
            self.mode_group.addButton(r_btn, idx)
            modes_inner.addWidget(r_btn)
        params_layout.addWidget(box_modes, stretch=2)

        box_z = QGroupBox("Параметр Z")
        z_inner = QHBoxLayout(box_z)
        z_label = QLabel("Значение Z:")
        self.input_z = QLineEdit("1.0000")
        validator = QDoubleValidator(-1e9, 1e9, 4, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.input_z.setValidator(validator)
        z_inner.addWidget(z_label)
        z_inner.addWidget(self.input_z)
        params_layout.addWidget(box_z, stretch=1)

        layout.addLayout(params_layout)

        # Кнопка Расчёта
        self.btn_calc = QPushButton("Рассчитать")
        self.btn_calc.setFixedHeight(36)
        self.btn_calc.setStyleSheet("font-weight: bold; font-size: 13px;")
        _ = self.btn_calc.clicked.connect(self._run_calculation)
        layout.addWidget(self.btn_calc)

        # Таблица результатов
        self.table_view = QTableView()
        self.table_model = PandasTableModel()
        self.table_view.setModel(self.table_model)

        header = self.table_view.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table_view)

        # Подвал
        bottom_layout = QHBoxLayout()
        self.lbl_w = QLabel("Итоговое значение W: —")
        self.lbl_w.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E3A8A;")
        bottom_layout.addWidget(self.lbl_w, stretch=1)
        layout.addLayout(bottom_layout)

        self.setCentralWidget(main_widget)

    @pyqtSlot()
    def _select_file_sn(self) -> None:
        file, _filter = QFileDialog.getOpenFileName(
            self, "Выберите файл (Сигнал + Шум)", "", "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if file:
            self.file_sn_path = Path(file)
            self.lbl_sn.setText(f"Файл 1: {self.file_sn_path.name}")

    @pyqtSlot()
    def _select_file_n(self) -> None:
        file, _filter = QFileDialog.getOpenFileName(
            self, "Выберите файл (Шум)", "", "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if file:
            self.file_n_path = Path(file)
            self.lbl_n.setText(f"Файл 2: {self.file_n_path.name}")

    @pyqtSlot()
    def _run_calculation(self) -> None:
        if not self.file_sn_path or not self.file_n_path:
            _ = QMessageBox.warning(
                self, "Предупреждение", "Пожалуйста, выберите оба файла перед расчетом!"
            )
            return

        selected_mode = self.mode_group.checkedId()
        if selected_mode < 0:
            selected_mode = 0

        raw_z_text = self.input_z.text().replace(",", ".")
        try:
            z_val = float(raw_z_text)
        except ValueError:
            _ = QMessageBox.warning(self, "Ошибка ввода", "Некорректное числовое значение для Z!")
            return

        try:
            df, w, x_alerts = calculate_data(
                self.file_sn_path,
                self.file_n_path,
                self.config_path,
                selected_mode,
                z_val,
            )
            self.current_df = df
            self.table_model.update_data(df, x_alerts)

            # Объединяем ячейку W на 20 строк таблицы
            self.table_view.clearSpans()
            col_w_idx: int = list(df.columns).index("W")
            self.table_view.setSpan(0, col_w_idx, 20, 1)

            self.lbl_w.setText(f"Итоговое значение W: {w:.4f}")
        except Exception as e:
            _ = QMessageBox.critical(self, "Ошибка расчёта", str(e))
