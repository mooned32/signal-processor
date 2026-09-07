import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, Qt


class PandasTableModel(QAbstractTableModel):
    def __init__(self, data: pd.DataFrame = pd.DataFrame()):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            val = self._data.iloc[index.row(), index.column()]
            if isinstance(val, float):
                return f"{val:.4f}"
            return str(val)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None

    def update_data(self, new_data: pd.DataFrame):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
