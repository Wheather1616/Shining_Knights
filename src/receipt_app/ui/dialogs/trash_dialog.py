from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...database import ReceiptDatabase
from ..icons import apply_label_icon


class TrashDialog(QDialog):
    """Branded recovery dialog for soft-deleted receipts."""

    receipts_restored = Signal()

    def __init__(
        self,
        db: ReceiptDatabase,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = db
        self.selected_receipt_ids: set[int] = set()
        self._row_checkboxes: dict[int, QCheckBox] = {}
        self._rows: list[Any] = []
        self._updating_header = False

        self.setObjectName("TrashDialog")
        self.setWindowTitle("ReceiptFlow Trash")
        self.resize(1050, 640)
        self.setMinimumSize(860, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 30, 34, 30)
        root.setSpacing(22)

        # Heading ---------------------------------------------------------
        heading_row = QHBoxLayout()
        heading_row.setSpacing(18)

        heading_stack = QVBoxLayout()
        heading_stack.setSpacing(8)

        eyebrow = QLabel("RECOVERY")
        eyebrow.setObjectName("TrashEyebrow")
        title = QLabel("Trash")
        title.setObjectName("TrashDisplayTitle")
        subtitle = QLabel(
            "Restore receipts that have been removed from the active database."
        )
        subtitle.setObjectName("TrashLead")
        subtitle.setWordWrap(True)

        heading_stack.addWidget(eyebrow)
        heading_stack.addWidget(title)
        heading_stack.addWidget(subtitle)
        heading_row.addLayout(heading_stack, 1)

        icon_tile = QFrame()
        icon_tile.setObjectName("TrashIconTile")
        icon_tile.setFixedSize(72, 72)
        icon_layout = QVBoxLayout(icon_tile)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setObjectName("TrashIcon")
        apply_label_icon(icon_label, "trash", role="coral", size=30)
        icon_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        heading_row.addWidget(icon_tile, 0, Qt.AlignmentFlag.AlignTop)

        root.addLayout(heading_row)

        # Summary / actions ---------------------------------------------
        summary_card = QFrame()
        summary_card.setObjectName("TrashSummaryCard")
        summary_layout = QHBoxLayout(summary_card)
        summary_layout.setContentsMargins(22, 18, 18, 18)
        summary_layout.setSpacing(18)

        summary_copy = QVBoxLayout()
        summary_copy.setSpacing(4)
        self.deleted_count_label = QLabel("")
        self.deleted_count_label.setObjectName("TrashSummaryTitle")
        summary_help = QLabel(
            "Select one or more receipts to return them to the active database."
        )
        summary_help.setObjectName("TrashSummaryHelp")
        summary_help.setWordWrap(True)
        summary_copy.addWidget(self.deleted_count_label)
        summary_copy.addWidget(summary_help)
        summary_layout.addLayout(summary_copy, 1)

        self.restore_selected_btn = QPushButton("Restore selected")
        self.restore_selected_btn.setObjectName("TrashRestoreSelectedButton")
        self.restore_selected_btn.setMinimumWidth(170)
        self.restore_selected_btn.clicked.connect(self._restore_selected)
        self.restore_selected_btn.setEnabled(False)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("TrashCloseButton")
        close_btn.setMinimumWidth(105)
        close_btn.clicked.connect(self.accept)

        summary_layout.addWidget(self.restore_selected_btn)
        summary_layout.addWidget(close_btn)
        root.addWidget(summary_card)

        # Results card ---------------------------------------------------
        self.results_card = QFrame()
        self.results_card.setObjectName("TrashResultsCard")
        results_layout = QVBoxLayout(self.results_card)
        results_layout.setContentsMargins(12, 12, 12, 12)
        results_layout.setSpacing(10)

        selection_row = QHBoxLayout()
        selection_row.setContentsMargins(4, 0, 4, 0)
        self.selection_label = QLabel("No receipts selected")
        self.selection_label.setObjectName("TrashSelectionStatus")
        selection_row.addWidget(self.selection_label)
        selection_row.addStretch()

        self.select_all = QCheckBox("Select all")
        self.select_all.setObjectName("TrashSelectAll")
        self.select_all.setTristate(True)
        self.select_all.stateChanged.connect(self._select_all_changed)
        selection_row.addWidget(self.select_all)
        results_layout.addLayout(selection_row)

        self.table = QTableWidget()
        self.table.setObjectName("TrashTable")
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                "Receipt no",
                "Name / Customer",
                "Amount",
                "Transaction date",
                "Deleted",
                "Actions",
            ]
        )
        self.table.horizontalHeader().setObjectName("TrashTableHeader")
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)

        header = self.table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setMinimumHeight(44)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 46)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 112)

        results_layout.addWidget(self.table, 1)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("TrashEmptyState")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 44, 24, 44)
        empty_layout.setSpacing(8)
        empty_title = QLabel("Trash is empty")
        empty_title.setObjectName("TrashEmptyTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_body = QLabel(
            "Deleted receipts will appear here until they are restored."
        )
        empty_body.setObjectName("TrashEmptyBody")
        empty_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_body.setWordWrap(True)
        empty_layout.addStretch()
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_body)
        empty_layout.addStretch()
        results_layout.addWidget(self.empty_state, 1)

        root.addWidget(self.results_card, 1)
        self._populate()

    @staticmethod
    def _format_transaction_date(value: Any) -> str:
        raw = str(value or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
            except ValueError:
                continue
        return raw

    @staticmethod
    def _format_deleted_at(value: Any) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        parsed: datetime | None = None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S.%f",
            ):
                try:
                    parsed = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
        if parsed is None:
            return raw
        hour = parsed.strftime("%I").lstrip("0") or "0"
        return f"{parsed.day} {parsed.strftime('%b %Y')} · {hour}:{parsed.strftime('%M %p').lower()}"

    @staticmethod
    def _row_value(row: Any, key: str, default: Any = "") -> Any:
        try:
            value = row[key]
        except Exception:
            return default
        return default if value is None else value

    def _populate(self) -> None:
        self.selected_receipt_ids.clear()
        self._row_checkboxes.clear()
        self._rows = list(self.db.trashed_receipts())

        count = len(self._rows)
        self.deleted_count_label.setText(
            f"{count:,} deleted receipt{'s' if count != 1 else ''}"
        )
        self.table.setVisible(bool(self._rows))
        self.empty_state.setVisible(not self._rows)
        self.select_all.setEnabled(bool(self._rows))

        self.table.setRowCount(count)
        for row_index, row in enumerate(self._rows):
            receipt_id = int(self._row_value(row, "id", 0))

            checkbox = QCheckBox()
            checkbox.setObjectName("TrashReceiptCheck")
            checkbox.stateChanged.connect(
                lambda state, rid=receipt_id: self._selection_changed(rid, state)
            )
            check_wrap = QWidget()
            check_wrap.setObjectName("TrashCheckWrap")
            check_layout = QHBoxLayout(check_wrap)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check_layout.addWidget(checkbox)
            self.table.setCellWidget(row_index, 0, check_wrap)
            self._row_checkboxes[receipt_id] = checkbox

            receipt_no = str(self._row_value(row, "receipt_no", "") or "—")
            name = str(self._row_value(row, "name", "") or "Unnamed receipt")
            amount_value = self._row_value(row, "amount", "")
            try:
                amount = f"${float(amount_value):,.2f}" if amount_value != "" else ""
            except (TypeError, ValueError):
                amount = str(amount_value or "")
            transaction_date = self._format_transaction_date(
                self._row_value(row, "transaction_date", "")
            )
            deleted_at = self._format_deleted_at(
                self._row_value(row, "deleted_at", "")
            )

            values = [receipt_no, name, amount, transaction_date, deleted_at]
            for column, text in enumerate(values, start=1):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, receipt_id)
                if column == 3:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row_index, column, item)

            restore_btn = QPushButton("Restore")
            restore_btn.setObjectName("TrashRowRestoreButton")
            restore_btn.clicked.connect(
                lambda _checked=False, rid=receipt_id: self._restore_ids({rid})
            )
            actions = QWidget()
            actions.setObjectName("TrashRowActions")
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            actions_layout.addWidget(restore_btn)
            self.table.setCellWidget(row_index, 6, actions)
            self.table.setRowHeight(row_index, 48)

        self._update_selection_ui()

    def _selection_changed(self, receipt_id: int, state: int) -> None:
        if state == Qt.CheckState.Checked.value:
            self.selected_receipt_ids.add(receipt_id)
        else:
            self.selected_receipt_ids.discard(receipt_id)
        self._update_selection_ui()

    def _select_all_changed(self, state: int) -> None:
        if self._updating_header:
            return
        should_select = state != Qt.CheckState.Unchecked.value
        for receipt_id, checkbox in self._row_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(should_select)
            checkbox.blockSignals(False)
            if should_select:
                self.selected_receipt_ids.add(receipt_id)
            else:
                self.selected_receipt_ids.discard(receipt_id)
        self._update_selection_ui()

    def _update_selection_ui(self) -> None:
        count = len(self.selected_receipt_ids)
        self.selection_label.setText(
            f"{count:,} receipt{'s' if count != 1 else ''} selected"
            if count
            else "No receipts selected"
        )
        self.restore_selected_btn.setText(
            f"Restore selected ({count:,})" if count else "Restore selected"
        )
        self.restore_selected_btn.setEnabled(count > 0)

        total = len(self._row_checkboxes)
        self._updating_header = True
        self.select_all.blockSignals(True)
        if total and count == total:
            self.select_all.setCheckState(Qt.CheckState.Checked)
        elif count:
            self.select_all.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            self.select_all.setCheckState(Qt.CheckState.Unchecked)
        self.select_all.blockSignals(False)
        self._updating_header = False

    def _restore_selected(self) -> None:
        self._restore_ids(set(self.selected_receipt_ids))

    def _restore_ids(self, receipt_ids: set[int]) -> None:
        if not receipt_ids:
            return

        restored = 0
        for receipt_id in receipt_ids:
            if self.db.restore_receipt(int(receipt_id)):
                restored += 1

        if restored:
            self.receipts_restored.emit()
            self._populate()
