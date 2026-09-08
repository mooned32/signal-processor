from typing import override

import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QColor


class PandasTableModel(QAbstractTableModel):
    _data: pd.DataFrame
    _x_alerts: list[bool] | None
    _x_col_idx: int

    def __init__(self, data: pd.DataFrame | None = None) -> None:
        super().__init__()
        self._data = data if data is not None else pd.DataFrame()
        self._x_alerts = None
        self._x_col_idx = 6

    @override
    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return self._data.shape[0]

    @override
    def columnCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return self._data.shape[1]

    @override
    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.BackgroundRole:
            if col == self._x_col_idx and self._x_alerts is not None:
                if row < len(self._x_alerts) and self._x_alerts[row]:
                    return QColor(255, 120, 120)
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            val: object = self._data.iloc[row, col]
            if isinstance(val, (float, int)):
                return f"{float(val):.4f}"
            return str(val)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

        return None

    @override
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None

    def update_data(self, new_data: pd.DataFrame, x_alerts: list[bool] | None = None) -> None:
        self.beginResetModel()
        self._data = new_data
        self._x_alerts = x_alerts
        if "x" in new_data.columns:
            self._x_col_idx = list(new_data.columns).index("x")
        self.endResetModel()
