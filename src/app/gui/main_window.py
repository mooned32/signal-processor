from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd
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

from ..core.calculator import calculate_data, load_config
from ..core.report_generator import generate_docx_report
from .table_model import PandasTableModel
from .template_dialog import TemplateFieldsDialog


class MainWindow(QMainWindow):
    config_path: Path
    file_sn_path: Path | None
    file_n_path: Path | None
    preview_df: pd.DataFrame | None
    extended_df: pd.DataFrame | None
    x_alerts: list[bool] | None
    violating_c: list[int]
    lbl_sn: QLabel
    lbl_n: QLabel
    input_z: QLineEdit
    mode_group: QButtonGroup
    radio_modes: list[QRadioButton]
    btn_calc: QPushButton
    table_view: QTableView
    table_model: PandasTableModel
    lbl_status: QLabel
    btn_report: QPushButton

    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.file_sn_path = None
        self.file_n_path = None
        self.preview_df = None
        self.extended_df = None
        self.x_alerts = None
        self.violating_c = []

        self.setWindowTitle("Анализатор спектральных сигналов")
        self.resize(920, 680)
        self._init_ui()

    def _init_ui(self) -> None:
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)

        # Выбор Файла 1 и 2
        sn_layout = QHBoxLayout()
        self.lbl_sn = QLabel("Файл 1 (Сигнал + Шум): Не выбран")
        btn_sn = QPushButton("Обзор...")
        _ = btn_sn.clicked.connect(self._select_file_sn)
        sn_layout.addWidget(self.lbl_sn, stretch=1)
        sn_layout.addWidget(btn_sn)
        layout.addLayout(sn_layout)

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

        # Таблица результатов (превью)
        self.table_view = QTableView()
        self.table_model = PandasTableModel()
        self.table_view.setModel(self.table_model)

        header = self.table_view.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table_view)

        # Подвал: Статус проверки и кнопка отчета
        bottom_layout = QHBoxLayout()
        self.lbl_status = QLabel("Статус: Ожидание расчёта")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #4B5563;")

        self.btn_report = QPushButton("Заполнить шаблон и создать отчёт...")
        self.btn_report.setEnabled(False)
        self.btn_report.setFixedHeight(34)
        self.btn_report.setStyleSheet("font-weight: bold; padding: 0 12px;")
        _ = self.btn_report.clicked.connect(self._open_report_dialog)

        bottom_layout.addWidget(self.lbl_status, stretch=1)
        bottom_layout.addWidget(self.btn_report)
        layout.addLayout(bottom_layout)

        self.setCentralWidget(main_widget)

    def _select_file_sn(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл (Сигнал + Шум)", "", "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if file:
            self.file_sn_path = Path(file)
            self.lbl_sn.setText(f"Файл 1: {self.file_sn_path.name}")

    def _select_file_n(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл (Шум)", "", "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if file:
            self.file_n_path = Path(file)
            self.lbl_n.setText(f"Файл 2: {self.file_n_path.name}")

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
            p_df, e_df, alerts, bad_c = calculate_data(
                self.file_sn_path,
                self.file_n_path,
                self.config_path,
                selected_mode,
                z_val,
            )
            self.preview_df = p_df
            self.extended_df = e_df
            self.x_alerts = alerts
            self.violating_c = bad_c

            # Выводим в превью таблицу ДО 'x' включительно
            self.table_model.update_data(p_df, alerts)

            # Отображаем вердикт
            if not bad_c:
                self.lbl_status.setText("При проверке не обнаружено нарушений")
                self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #15803D;")
            else:
                c_str = ", ".join(str(c) for c in bad_c)
                self.lbl_status.setText(f"Обнаружены нарушения на C: {c_str}")
                self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #B91C1C;")

            self.btn_report.setEnabled(True)

        except Exception as e:
            _ = QMessageBox.critical(self, "Ошибка расчёта", str(e))

    def _open_report_dialog(self) -> None:
        if self.preview_df is None or self.extended_df is None or self.x_alerts is None:
            return

        # 1. Читаем секцию [report_fields] из config.toml
        try:
            config = load_config(self.config_path)
            fields_obj = config.get("report_fields", {})
            fields_dict: dict[str, object] = (
                cast(dict[str, object], fields_obj) if isinstance(fields_obj, dict) else {}
            )
        except Exception as e:
            _ = QMessageBox.critical(
                self, "Ошибка конфига", f"Не удалось прочитать поля отчёта: {e}"
            )
            return

        dialog = TemplateFieldsDialog(fields_dict, self)
        if dialog.exec() != TemplateFieldsDialog.DialogCode.Accepted:
            return

        report_data = dialog.get_data()

        # 2. Имя файла по умолчанию: Акт_№_{ACT_NUMBER}_{DD_MM_YYYY}.docx
        act_num = report_data.get("ACT_NUMBER", "001")
        date_str = report_data.get("DATE", datetime.now().strftime("%d_%m_%Y")).replace(".", "_")
        default_filename = f"Акт_№_{act_num}_{date_str}.docx"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить акт проверки",
            default_filename,
            "Документы Word (*.docx)",
        )
        if not save_path:
            return

        # 3. Путь к шаблону template.docx (рядом с программой/конфигом)
        template_path = self.config_path.parent / "template.docx"
        if not template_path.exists():
            _ = QMessageBox.critical(
                self,
                "Ошибка",
                f"Файл шаблона 'template.docx' не найден рядом с программой:\n{template_path}",
            )
            return

        try:
            generate_docx_report(
                template_path=template_path,
                output_path=Path(save_path),
                report_data=report_data,
                preview_df=self.preview_df,
                extended_df=self.extended_df,
                x_alerts=self.x_alerts,
                violating_c=self.violating_c,
            )
            _ = QMessageBox.information(self, "Успех", f"Отчёт успешно сформирован:\n{save_path}")
        except Exception as e:
            _ = QMessageBox.critical(self, "Ошибка создания отчёта", str(e))
