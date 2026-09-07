from typing import Any, override

import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class PandasTableModel(QAbstractTableModel):
    _data: pd.DataFrame

    def __init__(self, data: pd.DataFrame | None = None) -> None:
        super().__init__()
        self._data = data if data is not None else pd.DataFrame()

    @override
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self._data.shape[0]

    @override
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self._data.shape[1]

    @override
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            val: Any = self._data.iloc[index.row(), index.column()]
            if isinstance(val, float):
                return f"{val:.4f}"
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
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None

    def update_data(self, new_data: pd.DataFrame) -> None:
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
