from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QEvent, QModelIndex, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from .config import CORE_FIELD_KEYS, FieldDefinition


@dataclass(slots=True)
class _ReceiptItem:
    row: Any
    custom: dict[str, Any]


@dataclass(slots=True)
class _GroupItem:
    label: str


class BrowseTableModel(QAbstractTableModel):
    """Lightweight model for the paged Browse table.

    Only the current database page is represented in memory. Group-by-date inserts
    lightweight heading rows instead of creating a QWidget for every receipt.
    """

    RECEIPT_ID_ROLE = Qt.ItemDataRole.UserRole + 1
    ROW_KIND_ROLE = Qt.ItemDataRole.UserRole + 2

    def __init__(
        self,
        fields: list[FieldDefinition],
        parent=None,
    ):
        super().__init__(parent)
        self._fields: list[FieldDefinition] = []
        self._visible_fields: list[FieldDefinition] = []
        self._items: list[_ReceiptItem | _GroupItem] = []
        self._source_rows: list[Any] = []
        self._grouped = False
        self.set_fields(fields)

    @property
    def actions_column(self) -> int:
        return len(self._visible_fields)

    @property
    def source_rows(self) -> list[Any]:
        return list(self._source_rows)

    def set_fields(self, fields: list[FieldDefinition]) -> None:
        self.beginResetModel()
        self._fields = list(fields)
        self._visible_fields = [field for field in fields if field.browse_column]
        self._items = []
        self._source_rows = []
        self.endResetModel()

    def set_rows(self, rows: list[Any], *, grouped: bool = False) -> None:
        self.beginResetModel()
        self._source_rows = list(rows)
        self._grouped = bool(grouped)
        self._items = self._build_items(self._source_rows, self._grouped)
        self.endResetModel()

    def _build_items(
        self,
        rows: list[Any],
        grouped: bool,
    ) -> list[_ReceiptItem | _GroupItem]:
        receipt_items = [
            _ReceiptItem(row=row, custom=self._parse_custom(row))
            for row in rows
        ]
        if not grouped:
            return receipt_items

        by_date: dict[str, list[_ReceiptItem]] = {}
        for item in receipt_items:
            date_key = str(item.row["transaction_date"] or "No date")
            by_date.setdefault(date_key, []).append(item)

        items: list[_ReceiptItem | _GroupItem] = []
        for date_key, date_rows in by_date.items():
            count = len(date_rows)
            suffix = "transaction" if count == 1 else "transactions"
            items.append(_GroupItem(f"{self._display_date(date_key)} — {count} {suffix}"))
            items.extend(date_rows)
        return items

    @staticmethod
    def _parse_custom(row: Any) -> dict[str, Any]:
        try:
            value = json.loads(row["custom_fields"] or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _display_date(value: str) -> str:
        if value == "No date":
            return value
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._visible_fields) + 1

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._visible_fields):
                return self._visible_fields[section].label.upper()
            if section == self.actions_column:
                return "ACTIONS"
            return None
        return section + 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]
        if isinstance(item, _GroupItem):
            if role == Qt.ItemDataRole.DisplayRole:
                return item.label if index.column() == 0 else ""
            if role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                return font
            if role == Qt.ItemDataRole.BackgroundRole:
                return QBrush(QColor("#f3ece8"))
            if role == Qt.ItemDataRole.ForegroundRole:
                return QBrush(QColor("#6d0813"))
            if role == self.ROW_KIND_ROLE:
                return "group"
            return None

        row = item.row
        if role == self.RECEIPT_ID_ROLE:
            return int(row["id"])
        if role == self.ROW_KIND_ROLE:
            return "receipt"

        if index.column() == self.actions_column:
            if role == Qt.ItemDataRole.DisplayRole:
                return ""
            if role == Qt.ItemDataRole.ToolTipRole:
                return "Edit or move this receipt to Trash"
            return None

        if not (0 <= index.column() < len(self._visible_fields)):
            return None

        field = self._visible_fields[index.column()]
        value = self._field_value(item, field.key)

        if role == Qt.ItemDataRole.DisplayRole:
            if field.key == "amount" and value not in {None, ""}:
                try:
                    return f"${float(value):,.2f}"
                except (TypeError, ValueError):
                    return str(value)
            return str(value or "")

        if role == Qt.ItemDataRole.ToolTipRole:
            text = str(value or "")
            return text if text else None

        if role == Qt.ItemDataRole.TextAlignmentRole and field.key == "amount":
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return None

    @staticmethod
    def _field_value(item: _ReceiptItem, key: str) -> Any:
        if key in CORE_FIELD_KEYS:
            return item.row[key]
        return item.custom.get(key, "")

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        item = self._items[index.row()]
        if isinstance(item, _GroupItem):
            return Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def receipt_id_at(self, index: QModelIndex) -> int | None:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if isinstance(item, _GroupItem):
            return None
        return int(item.row["id"])


class ReceiptActionsDelegate(QStyledItemDelegate):
    """Paint Edit/Delete controls without allocating child widgets per row."""

    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def _button_rects(self, option: QStyleOptionViewItem) -> tuple[QRect, QRect]:
        margin = 5
        gap = 6
        available = max(80, option.rect.width() - (margin * 2) - gap)
        edit_width = max(42, int(available * 0.43))
        delete_width = max(50, available - edit_width)
        height = min(32, max(24, option.rect.height() - 10))
        top = option.rect.top() + max(0, (option.rect.height() - height) // 2)
        left = option.rect.left() + margin
        edit_rect = QRect(left, top, edit_width, height)
        delete_rect = QRect(left + edit_width + gap, top, delete_width, height)
        return edit_rect, delete_rect

    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        receipt_id = index.data(BrowseTableModel.RECEIPT_ID_ROLE)
        if receipt_id is None:
            super().paint(painter, option, index)
            return

        # Paint the normal cell background first, then draw lightweight branded
        # action pills. This keeps the table efficient without allocating child
        # widgets for every row.
        super().paint(painter, option, index)
        edit_rect, delete_rect = self._button_rects(option)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        font = painter.font()
        font.setBold(True)
        if font.pointSizeF() > 0:
            font.setPointSizeF(max(9.0, font.pointSizeF() - 0.5))
        painter.setFont(font)

        # Edit: restrained Amethyst accent.
        painter.setBrush(QBrush(QColor("#fbf3fb")))
        painter.setPen(QPen(QColor("#e4bfe1"), 1))
        painter.drawRoundedRect(edit_rect, 10, 10)
        painter.setPen(QPen(QColor("#a846a0")))
        painter.drawText(edit_rect, Qt.AlignmentFlag.AlignCenter, "Edit")

        # Delete: soft Coral treatment.
        painter.setBrush(QBrush(QColor("#fff3f1")))
        painter.setPen(QPen(QColor("#f5c2bb"), 1))
        painter.drawRoundedRect(delete_rect, 10, 10)
        painter.setPen(QPen(QColor("#d85d50")))
        painter.drawText(delete_rect, Qt.AlignmentFlag.AlignCenter, "Delete")

        painter.restore()

    def editorEvent(self, event, model, option, index: QModelIndex) -> bool:
        receipt_id = index.data(BrowseTableModel.RECEIPT_ID_ROLE)
        if receipt_id is None:
            return False

        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            point = event.position().toPoint()
            edit_rect, delete_rect = self._button_rects(option)
            if edit_rect.contains(point):
                self.edit_requested.emit(int(receipt_id))
                return True
            if delete_rect.contains(point):
                self.delete_requested.emit(int(receipt_id))
                return True

        return super().editorEvent(event, model, option, index)
