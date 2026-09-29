from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...config import CORE_FIELD_KEYS, FieldDefinition
from ...database import ReceiptDatabase, SORT_OPTIONS
from ..icons import apply_button_icon
from ..dialogs.trash_dialog import TrashDialog


class BrowsePage(QWidget):
    """Paged receipt search/browse screen grouped into collapsible date sections.

    Receipts are always grouped by transaction date. Each date section can be
    expanded/collapsed and has a date-level Select all control. Individual
    receipts can also be selected for export.
    """

    edit_requested = Signal(int)
    delete_requested = Signal(int)
    receipt_restored = Signal()
    active_count_changed = Signal(int)

    def __init__(
        self,
        db: ReceiptDatabase,
        fields: list[FieldDefinition],
        default_sort: str = "Newest first",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.db = db
        self.fields = list(fields)
        self.current_page = 0
        self.page_size = 100
        self.total_results = 0
        self.last_rows: list[Any] = []
        self.active_receipt_count: int | None = None

        self.selected_receipt_ids: set[int] = set()
        self._expanded_dates: set[str] = set()
        self._receipt_checkboxes: dict[int, QCheckBox] = {}
        self._group_checkboxes: dict[str, list[QCheckBox]] = {}
        self._group_select_all: dict[str, QCheckBox] = {}
        self._date_receipt_ids_cache: dict[str, set[int]] = {}
        self._search_result_ids: set[int] = set()
        self._last_query = ""
        self._group_tables: list[tuple[QTableWidget, list[FieldDefinition]]] = []
        self._responsive_mode = "regular"

        self.setObjectName("BrowsePage")

        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(250)
        self.search_debounce_timer.timeout.connect(self.refresh_results)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(34, 28, 34, 30)
        self.main_layout.setSpacing(16)
        layout = self.main_layout

        # Page heading ------------------------------------------------------
        eyebrow = QLabel("TRANSACTIONS")
        eyebrow.setObjectName("BrowseEyebrow")
        title = QLabel("Browse transactions")
        title.setObjectName("BrowseDisplayTitle")
        subtitle = QLabel(
            "Search the database using receipt numbers, names, member numbers, "
            "notes, dates or amounts. Receipts are grouped by date until you search."
        )
        subtitle.setObjectName("BrowseLead")
        subtitle.setWordWrap(True)

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Search / sort -----------------------------------------------------
        self.filter_card = QFrame()
        self.filter_card.setObjectName("BrowseFilterCard")
        self.filter_layout = QHBoxLayout(self.filter_card)
        self.filter_layout.setContentsMargins(18, 16, 18, 16)
        self.filter_layout.setSpacing(14)
        filter_layout = self.filter_layout

        self.search_input = QLineEdit()
        self.search_input.setObjectName("BrowseSearchInput")
        self.search_input.setPlaceholderText(
            "Search anything, e.g. Smith, 2026-05-16, 45.00, card, receipt number"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.schedule_refresh_results)
        filter_layout.addWidget(self.search_input, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.setObjectName("BrowseSortCombo")
        self.sort_combo.addItems(list(SORT_OPTIONS.keys()))
        sort_value = default_sort if default_sort in SORT_OPTIONS else "Newest first"
        self.sort_combo.setCurrentText(sort_value)
        self.sort_combo.setMinimumWidth(180)
        self.sort_combo.currentTextChanged.connect(self._browse_filters_changed)
        filter_layout.addWidget(self.sort_combo)
        layout.addWidget(self.filter_card)

        # Selection / utility actions --------------------------------------
        self.action_row = QHBoxLayout()
        self.action_row.setContentsMargins(0, 0, 0, 0)
        self.action_row.setSpacing(10)

        self.selection_label = QLabel("No receipts selected")
        self.selection_label.setObjectName("BrowseSelectionStatus")
        self.action_row.addWidget(self.selection_label)

        self.search_select_all_btn = QPushButton("Select all results")
        self.search_select_all_btn.setObjectName("BrowseSearchSelectAllButton")
        self.search_select_all_btn.setToolTip(
            "Select every receipt matching the current search, including other result pages."
        )
        self.search_select_all_btn.clicked.connect(self._toggle_search_select_all)
        self.search_select_all_btn.setVisible(False)
        self.action_row.addWidget(self.search_select_all_btn)

        self.action_row.addStretch()

        self.export_btn = QPushButton("Export selected")
        self.export_btn.setObjectName("BrowseExportButton")
        self.export_btn.setToolTip("Export only the receipts you have selected.")
        self.export_btn.clicked.connect(self.export_selected_results)
        apply_button_icon(self.export_btn, "export", role="cyan", size=15)
        self.export_btn.setVisible(False)

        self.delete_selected_btn = QPushButton("Delete selected")
        self.delete_selected_btn.setObjectName("BrowseDeleteSelectedButton")
        self.delete_selected_btn.setToolTip("Move the selected receipts to Trash.")
        self.delete_selected_btn.clicked.connect(self.delete_selected_receipts)
        apply_button_icon(self.delete_selected_btn, "trash", role="coral", size=15)
        self.delete_selected_btn.setVisible(False)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("BrowseRefreshButton")
        self.refresh_btn.clicked.connect(self.refresh_results)
        apply_button_icon(self.refresh_btn, "refresh", role="muted", size=15)

        self.trash_btn = QPushButton("Trash")
        self.trash_btn.setObjectName("BrowseTrashButton")
        self.trash_btn.clicked.connect(self.open_trash)
        apply_button_icon(self.trash_btn, "trash", role="coral", size=15)

        self._action_buttons = [
            self.search_select_all_btn,
            self.export_btn,
            self.delete_selected_btn,
            self.refresh_btn,
            self.trash_btn,
        ]
        for button in self._action_buttons:
            button.setFixedSize(142, 40)

        self.action_row.addWidget(self.export_btn)
        self.action_row.addWidget(self.delete_selected_btn)
        self.action_row.addWidget(self.refresh_btn)
        self.action_row.addWidget(self.trash_btn)
        layout.addLayout(self.action_row)

        # Results card ------------------------------------------------------
        results_card = QFrame()
        results_card.setObjectName("BrowseResultsCard")
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(1, 1, 1, 1)
        results_layout.setSpacing(0)

        self.groups_scroll = QScrollArea()
        self.groups_scroll.setObjectName("BrowseGroupsScroll")
        self.groups_scroll.setWidgetResizable(True)
        self.groups_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.groups_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.groups_container = QWidget()
        self.groups_container.setObjectName("BrowseGroupsContainer")
        self.groups_layout = QVBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(14, 14, 14, 14)
        self.groups_layout.setSpacing(12)
        self.groups_layout.addStretch()
        self.groups_scroll.setWidget(self.groups_container)
        results_layout.addWidget(self.groups_scroll, 1)

        footer = QFrame()
        footer.setObjectName("BrowseResultsFooter")
        self.footer_layout = QVBoxLayout(footer)
        self.footer_layout.setContentsMargins(16, 13, 16, 14)
        self.footer_layout.setSpacing(8)
        footer_layout = self.footer_layout

        pagination = QHBoxLayout()
        pagination.setSpacing(8)

        self.previous_page_btn = QPushButton("Previous")
        self.previous_page_btn.setObjectName("BrowsePreviousButton")
        self.previous_page_btn.clicked.connect(lambda: self._change_browse_page(-1))
        pagination.addWidget(self.previous_page_btn)

        self.next_page_btn = QPushButton("Next")
        self.next_page_btn.setObjectName("BrowseNextButton")
        self.next_page_btn.clicked.connect(lambda: self._change_browse_page(1))
        pagination.addWidget(self.next_page_btn)

        self.page_label = QLabel("")
        self.page_label.setObjectName("PaginationStatus")
        pagination.addWidget(self.page_label)
        pagination.addStretch()

        rows_label = QLabel("Rows per page")
        rows_label.setObjectName("PaginationStatus")
        pagination.addWidget(rows_label)

        self.page_size_combo = QComboBox()
        self.page_size_combo.setObjectName("BrowsePageSizeCombo")
        self.page_size_combo.addItems(["50", "100", "200"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentTextChanged.connect(self._page_size_changed)
        pagination.addWidget(self.page_size_combo)
        footer_layout.addLayout(pagination)

        self.result_count_label = QLabel("")
        self.result_count_label.setObjectName("BrowseResultCount")
        footer_layout.addWidget(self.result_count_label)

        results_layout.addWidget(footer)
        layout.addWidget(results_card, 1)
        QTimer.singleShot(0, self._apply_responsive_layout)

    @property
    def current_sort(self) -> str:
        return self.sort_combo.currentText()

    # ------------------------------------------------------------------
    # Search / paging
    # ------------------------------------------------------------------
    def schedule_refresh_results(self, *_args: object) -> None:
        self.current_page = 0
        self.search_debounce_timer.start()

    def _browse_filters_changed(self, *_args: object) -> None:
        self.current_page = 0
        self.refresh_results()

    def _page_size_changed(self, value: str) -> None:
        try:
            page_size = int(value)
        except (TypeError, ValueError):
            page_size = 100
        self.page_size = max(25, min(page_size, 500))
        self.current_page = 0
        self.refresh_results()

    def _change_browse_page(self, delta: int) -> None:
        page_count = max(1, (self.total_results + self.page_size - 1) // self.page_size)
        target = max(0, min(self.current_page + int(delta), page_count - 1))
        if target == self.current_page:
            return
        self.current_page = target
        self.refresh_results()

    def invalidate_active_count(self) -> None:
        self.active_receipt_count = None

    # ------------------------------------------------------------------
    # Date groups
    # ------------------------------------------------------------------
    @staticmethod
    def _row_date_key(row: Any) -> str:
        try:
            return str(row["transaction_date"] or "").strip()
        except Exception:
            return ""

    @staticmethod
    def _date_label(value: str) -> str:
        raw = str(value or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(raw, fmt)
                return f"{parsed.strftime('%A')} · {parsed.day} {parsed.strftime('%B %Y')}"
            except ValueError:
                continue
        return raw or "Unknown date"

    def _visible_fields(self) -> list[FieldDefinition]:
        # Date is already represented by the accordion header, so displaying it
        # again in every row adds noise without adding information.
        return [
            field
            for field in self.fields
            if field.browse_column and field.key != "transaction_date"
        ]

    def _search_visible_fields(self) -> list[FieldDefinition]:
        """Fields used by the flat table shown while a search is active.

        Date is always included in search mode because the date accordion headers
        are intentionally removed while searching.
        """
        visible = [field for field in self.fields if field.browse_column]
        if not any(field.key == "transaction_date" for field in visible):
            date_field = next(
                (field for field in self.fields if field.key == "transaction_date"),
                None,
            )
            if date_field is not None:
                insert_at = 1 if visible and visible[0].key == "receipt_no" else 0
                visible.insert(insert_at, date_field)
        return visible

    @staticmethod
    def _custom_values(row: Any) -> dict[str, Any]:
        try:
            raw = row["custom_fields"] or "{}"
        except Exception:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    def _field_value(self, row: Any, field: FieldDefinition) -> Any:
        if field.key in CORE_FIELD_KEYS:
            try:
                return row[field.key]
            except Exception:
                return ""
        return self._custom_values(row).get(field.key, "")

    def _display_value(self, row: Any, field: FieldDefinition) -> str:
        value = self._field_value(row, field)
        if field.key == "amount" and value not in {None, ""}:
            try:
                return f"${float(value):,.2f}"
            except (TypeError, ValueError):
                pass
        return str(value or "")

    def _clear_groups(self) -> None:
        self._receipt_checkboxes.clear()
        self._group_checkboxes.clear()
        self._group_select_all.clear()
        self._date_receipt_ids_cache.clear()
        self._group_tables.clear()

        while self.groups_layout.count() > 1:
            item = self.groups_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _rebuild_groups(self) -> None:
        """Render grouped date accordions normally, or one flat table for searches."""
        self._clear_groups()

        if not self.last_rows:
            empty = QFrame()
            empty.setObjectName("BrowseEmptyState")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(24, 34, 24, 34)
            empty_label = QLabel("No matching transactions")
            empty_label.setObjectName("BrowseEmptyTitle")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(empty_label)
            self.groups_layout.insertWidget(0, empty)
            return

        if self.search_input.text().strip():
            search_table = self._build_search_results_table(self.last_rows)
            self.groups_layout.insertWidget(0, search_table)
            return

        grouped: OrderedDict[str, list[Any]] = OrderedDict()
        for row in self.last_rows:
            grouped.setdefault(self._row_date_key(row), []).append(row)

        if not self._expanded_dates and grouped:
            self._expanded_dates.add(next(iter(grouped)))

        insert_index = 0
        for date_key, rows in grouped.items():
            group_widget = self._build_date_group(date_key, rows)
            self.groups_layout.insertWidget(insert_index, group_widget)
            insert_index += 1

    def _build_search_results_table(self, rows: list[Any]) -> QTableWidget:
        """Build the ungrouped, ordered receipt table used while searching."""
        visible_fields = self._search_visible_fields()
        table = QTableWidget(len(rows), len(visible_fields) + 2)
        table.setObjectName("BrowseSearchTable")
        table.setHorizontalHeaderLabels(
            [""] + [field.label for field in visible_fields] + ["Actions"]
        )
        table.horizontalHeader().setObjectName("BrowseDateTableHeader")
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setWordWrap(False)
        table.setShowGrid(False)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        header = table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        header.setMinimumHeight(42)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 44)

        actions_column = len(visible_fields) + 1
        header.setSectionResizeMode(actions_column, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(actions_column, 150)
        for column in range(1, actions_column):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)

        for row_index, row in enumerate(rows):
            receipt_id = int(row["id"])

            check = QCheckBox()
            check.setObjectName("BrowseReceiptCheck")
            check.setChecked(receipt_id in self.selected_receipt_ids)
            check.stateChanged.connect(
                lambda state, rid=receipt_id: self._search_receipt_selection_changed(
                    rid, state
                )
            )
            check_wrap = QWidget()
            check_layout = QHBoxLayout(check_wrap)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check_layout.addWidget(check)
            table.setCellWidget(row_index, 0, check_wrap)
            self._receipt_checkboxes[receipt_id] = check

            for field_index, field in enumerate(visible_fields, start=1):
                item = QTableWidgetItem(self._display_value(row, field))
                item.setData(Qt.ItemDataRole.UserRole, receipt_id)
                if field.key == "amount":
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                table.setItem(row_index, field_index, item)

            actions = QWidget()
            actions.setObjectName("BrowseRowActions")
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)

            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("BrowseEditButton")
            edit_btn.clicked.connect(
                lambda _checked=False, rid=receipt_id: self.edit_requested.emit(rid)
            )

            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("BrowseDeleteButton")
            delete_btn.clicked.connect(
                lambda _checked=False, rid=receipt_id: self.delete_requested.emit(rid)
            )

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            table.setCellWidget(row_index, actions_column, actions)
            table.setRowHeight(row_index, 52)

        table.cellDoubleClicked.connect(
            lambda row_index, column, search_rows=rows, action_col=actions_column: (
                self.edit_requested.emit(int(search_rows[row_index]["id"]))
                if column not in {0, action_col}
                else None
            )
        )

        header_height = max(44, header.minimumHeight(), header.sizeHint().height())
        body_height = sum(table.rowHeight(index) for index in range(table.rowCount()))
        table.setFixedHeight(header_height + body_height + 8)

        self._group_tables.append((table, visible_fields))
        QTimer.singleShot(0, self._apply_responsive_table_columns)
        return table

    def _build_date_group(self, date_key: str, rows: list[Any]) -> QFrame:
        group = QFrame()
        group.setObjectName("BrowseDateGroup")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("BrowseDateHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 12, 0)
        header_layout.setSpacing(8)

        toggle = QPushButton()
        toggle.setObjectName("BrowseDateToggle")
        toggle.setCheckable(True)
        toggle.setChecked(date_key in self._expanded_dates)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setText(self._toggle_text(date_key, toggle.isChecked()))
        header_layout.addWidget(toggle, 1)

        count_label = QLabel(f"{len(rows):,} receipt{'s' if len(rows) != 1 else ''}")
        count_label.setObjectName("BrowseDateCount")
        header_layout.addWidget(count_label)

        select_all = QCheckBox("Select all")
        select_all.setObjectName("BrowseDateSelectAll")
        select_all.setTristate(True)
        select_all.setToolTip("Select every receipt for this date.")
        header_layout.addWidget(select_all)
        group_layout.addWidget(header)

        content = QFrame()
        content.setObjectName("BrowseDateContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        table = self._build_group_table(date_key, rows)
        content_layout.addWidget(table)
        content.setVisible(toggle.isChecked())
        group_layout.addWidget(content)

        toggle.toggled.connect(
            lambda expanded, key=date_key, btn=toggle, body=content: self._toggle_date_group(
                key, expanded, btn, body
            )
        )
        select_all.stateChanged.connect(
            lambda state, key=date_key: self._date_select_all_changed(key, state)
        )
        self._group_select_all[date_key] = select_all
        self._update_group_select_all_state(date_key)
        return group

    def _toggle_text(self, date_key: str, expanded: bool) -> str:
        arrow = "▾" if expanded else "▸"
        return f"{arrow}  {self._date_label(date_key)}"

    def _toggle_date_group(
        self,
        date_key: str,
        expanded: bool,
        button: QPushButton,
        content: QFrame,
    ) -> None:
        if expanded:
            self._expanded_dates.add(date_key)
        else:
            self._expanded_dates.discard(date_key)
        content.setVisible(expanded)
        button.setText(self._toggle_text(date_key, expanded))

    def _build_group_table(self, date_key: str, rows: list[Any]) -> QTableWidget:
        visible_fields = self._visible_fields()
        table = QTableWidget(len(rows), len(visible_fields) + 2)
        table.setObjectName("BrowseDateTable")
        table.setHorizontalHeaderLabels([""] + [field.label for field in visible_fields] + ["Actions"])
        table.horizontalHeader().setObjectName("BrowseDateTableHeader")
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setWordWrap(False)
        table.setShowGrid(False)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        header = table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setMinimumHeight(42)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 44)

        actions_column = len(visible_fields) + 1
        header.setSectionResizeMode(actions_column, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(actions_column, 150)
        for column in range(1, actions_column):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)

        group_checks: list[QCheckBox] = []
        row_ids: list[int] = []

        for row_index, row in enumerate(rows):
            receipt_id = int(row["id"])
            row_ids.append(receipt_id)

            check = QCheckBox()
            check.setObjectName("BrowseReceiptCheck")
            check.setChecked(receipt_id in self.selected_receipt_ids)
            check.stateChanged.connect(
                lambda state, rid=receipt_id, key=date_key: self._receipt_selection_changed(
                    rid, key, state
                )
            )
            check_wrap = QWidget()
            check_layout = QHBoxLayout(check_wrap)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check_layout.addWidget(check)
            table.setCellWidget(row_index, 0, check_wrap)
            self._receipt_checkboxes[receipt_id] = check
            group_checks.append(check)

            for field_index, field in enumerate(visible_fields, start=1):
                item = QTableWidgetItem(self._display_value(row, field))
                item.setData(Qt.ItemDataRole.UserRole, receipt_id)
                if field.key == "amount":
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                table.setItem(row_index, field_index, item)

            actions = QWidget()
            actions.setObjectName("BrowseRowActions")
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)

            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("BrowseEditButton")
            edit_btn.clicked.connect(
                lambda _checked=False, rid=receipt_id: self.edit_requested.emit(rid)
            )
            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("BrowseDeleteButton")
            delete_btn.clicked.connect(
                lambda _checked=False, rid=receipt_id: self.delete_requested.emit(rid)
            )
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            table.setCellWidget(row_index, actions_column, actions)
            table.setRowHeight(row_index, 52)

        self._group_checkboxes[date_key] = group_checks

        table.cellDoubleClicked.connect(
            lambda row_index, column, group_rows=rows, action_col=actions_column: (
                self.edit_requested.emit(int(group_rows[row_index]["id"]))
                if column not in {0, action_col}
                else None
            )
        )

        # Keep the whole group visually bounded. The previous fixed-height
        # calculation could clip the bottom of the action widgets on macOS.
        header_height = max(44, header.minimumHeight(), header.sizeHint().height())
        body_height = sum(table.rowHeight(index) for index in range(table.rowCount()))
        table.setFixedHeight(header_height + body_height + 8)

        self._group_tables.append((table, visible_fields))
        QTimer.singleShot(0, self._apply_responsive_table_columns)
        return table

    # ------------------------------------------------------------------
    # Selection / export
    # ------------------------------------------------------------------
    def _receipt_selection_changed(self, receipt_id: int, date_key: str, state: int) -> None:
        if state == Qt.CheckState.Checked.value:
            self.selected_receipt_ids.add(receipt_id)
        else:
            self.selected_receipt_ids.discard(receipt_id)
        self._update_group_select_all_state(date_key)
        self._update_selection_ui()

    def _all_receipt_ids_for_date(self, date_key: str) -> set[int]:
        cached = self._date_receipt_ids_cache.get(date_key)
        if cached is not None:
            return cached
        rows = self.db.receipts_for_date(date_key, limit=5000)
        ids = {int(row["id"]) for row in rows}
        self._date_receipt_ids_cache[date_key] = ids
        return ids

    def _update_group_select_all_state(self, date_key: str) -> None:
        header_check = self._group_select_all.get(date_key)
        if header_check is None:
            return

        all_ids = self._all_receipt_ids_for_date(date_key)
        selected_count = len(all_ids & self.selected_receipt_ids)
        header_check.blockSignals(True)
        if all_ids and selected_count == len(all_ids):
            header_check.setCheckState(Qt.CheckState.Checked)
        elif selected_count:
            header_check.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            header_check.setCheckState(Qt.CheckState.Unchecked)
        header_check.blockSignals(False)

    def _date_select_all_changed(self, date_key: str, state: int) -> None:
        # Select all applies to the whole date, not only the rows visible on the
        # current Browse page. That makes the date-level checkbox predictable.
        should_select = state != Qt.CheckState.Unchecked.value
        all_ids = self._all_receipt_ids_for_date(date_key)
        if should_select:
            self.selected_receipt_ids.update(all_ids)
        else:
            self.selected_receipt_ids.difference_update(all_ids)

        for receipt_id, checkbox in self._receipt_checkboxes.items():
            if receipt_id not in all_ids:
                continue
            checkbox.blockSignals(True)
            checkbox.setChecked(should_select)
            checkbox.blockSignals(False)

        self._update_group_select_all_state(date_key)
        self._update_selection_ui()

    def _search_receipt_selection_changed(self, receipt_id: int, state: int) -> None:
        if state == Qt.CheckState.Checked.value:
            self.selected_receipt_ids.add(receipt_id)
        else:
            self.selected_receipt_ids.discard(receipt_id)
        self._update_selection_ui()

    def _toggle_search_select_all(self) -> None:
        if not self._search_result_ids:
            return

        all_selected = self._search_result_ids.issubset(self.selected_receipt_ids)
        if all_selected:
            self.selected_receipt_ids.difference_update(self._search_result_ids)
        else:
            self.selected_receipt_ids.update(self._search_result_ids)

        for receipt_id, checkbox in self._receipt_checkboxes.items():
            if receipt_id not in self._search_result_ids:
                continue
            checkbox.blockSignals(True)
            checkbox.setChecked(not all_selected)
            checkbox.blockSignals(False)

        self._update_selection_ui()

    def _update_selection_ui(self) -> None:
        count = len(self.selected_receipt_ids)
        has_selection = count > 0
        search_active = bool(self.search_input.text().strip())

        if search_active and self.total_results:
            selected_in_search = len(
                self.selected_receipt_ids & self._search_result_ids
            )
            self.selection_label.setText(
                f"{selected_in_search:,} of {self.total_results:,} selected"
                if selected_in_search
                else "No receipts selected"
            )
            all_search_selected = bool(self._search_result_ids) and (
                self._search_result_ids.issubset(self.selected_receipt_ids)
            )
            self.search_select_all_btn.setText(
                "Clear selection" if all_search_selected else "Select all results"
            )
            self.search_select_all_btn.setVisible(True)
        else:
            self.search_select_all_btn.setVisible(False)
            if has_selection:
                self.selection_label.setText(
                    f"{count:,} receipt{'s' if count != 1 else ''} selected"
                )
            else:
                self.selection_label.setText("No receipts selected")

        self.export_btn.setText("Export selected")
        self.delete_selected_btn.setText("Delete selected")

        # Selection actions should not occupy space when there is nothing to act on.
        self.export_btn.setVisible(has_selection)
        self.delete_selected_btn.setVisible(has_selection)

    def delete_selected_receipts(self) -> None:
        if not self.selected_receipt_ids:
            return

        count = len(self.selected_receipt_ids)
        confirm = QMessageBox.question(
            self,
            "Move selected receipts to Trash",
            f"Move {count:,} selected receipt{'s' if count != 1 else ''} to Trash? "
            "You can restore them later.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        deleted = 0
        for receipt_id in list(self.selected_receipt_ids):
            if self.db.delete_receipt(receipt_id):
                deleted += 1

        self.selected_receipt_ids.clear()
        self.invalidate_active_count()
        self.refresh_results()

        # Existing MainWindow wiring uses this signal to refresh the floating
        # receipt panel after database mutations, so keep using it here too.
        self.receipt_restored.emit()

        QMessageBox.information(
            self,
            "Moved to Trash",
            f"{deleted:,} receipt{'s' if deleted != 1 else ''} moved to Trash.",
        )

    @staticmethod
    def _responsive_field_priority(field: FieldDefinition) -> int:
        # Receipt number is the anchor column. Every other receipt field may
        # progressively collapse as horizontal space becomes constrained.
        priorities = {
            "receipt_no": 1000,
            "amount": 90,
            "name": 80,
            "receipt_category": 70,
            "description": 60,
            "payment_type": 50,
            "member_no": 40,
            "event_number": 30,
            "quantity": 20,
            "notes": 10,
        }
        return priorities.get(field.key, 15)

    @staticmethod
    def _responsive_field_width(field: FieldDefinition) -> int:
        minimums = {
            "receipt_no": 105,
            "receipt_category": 115,
            "description": 135,
            "name": 135,
            "amount": 90,
            "payment_type": 115,
            "member_no": 100,
            "event_number": 110,
            "quantity": 80,
            "notes": 150,
        }
        return minimums.get(field.key, 120)

    def _apply_responsive_table_columns(self) -> None:
        for table, fields in list(self._group_tables):
            if table is None:
                continue

            header = table.horizontalHeader()
            actions_column = len(fields) + 1
            available = max(0, table.viewport().width())
            if available <= 0:
                continue

            # Reset before recalculating so widening the window restores columns.
            for column in range(1, actions_column):
                table.setColumnHidden(column, False)

            fixed_width = 44 + 150
            required_width = fixed_width + sum(
                self._responsive_field_width(field) for field in fields
            )

            collapsible = sorted(
                (
                    (self._responsive_field_priority(field), column, field)
                    for column, field in enumerate(fields, start=1)
                    if field.key != "receipt_no"
                ),
                key=lambda item: item[0],
            )

            for _priority, column, field in collapsible:
                if required_width <= available:
                    break
                table.setColumnHidden(column, True)
                required_width -= self._responsive_field_width(field)

            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(0, 44)
            header.setSectionResizeMode(actions_column, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(actions_column, 150)

            for column in range(1, actions_column):
                if table.isColumnHidden(column):
                    continue
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)

    def _apply_responsive_layout(self) -> None:
        height = self.height()
        width = self.width()

        if height < 650:
            mode = "dense"
            self.main_layout.setContentsMargins(22, 16, 22, 18)
            self.main_layout.setSpacing(10)
            self.filter_layout.setContentsMargins(14, 10, 14, 10)
            self.groups_layout.setContentsMargins(10, 10, 10, 10)
            self.groups_layout.setSpacing(8)
            self.footer_layout.setContentsMargins(12, 9, 12, 10)
        elif height < 780:
            mode = "compact"
            self.main_layout.setContentsMargins(28, 20, 28, 22)
            self.main_layout.setSpacing(12)
            self.filter_layout.setContentsMargins(16, 12, 16, 12)
            self.groups_layout.setContentsMargins(12, 12, 12, 12)
            self.groups_layout.setSpacing(10)
            self.footer_layout.setContentsMargins(14, 10, 14, 11)
        else:
            mode = "regular"
            self.main_layout.setContentsMargins(34, 28, 34, 30)
            self.main_layout.setSpacing(16)
            self.filter_layout.setContentsMargins(18, 16, 18, 16)
            self.groups_layout.setContentsMargins(14, 14, 14, 14)
            self.groups_layout.setSpacing(12)
            self.footer_layout.setContentsMargins(16, 13, 16, 14)

        if mode != self._responsive_mode:
            self._responsive_mode = mode

        action_width = 132 if width < 900 else 142
        for button in self._action_buttons:
            button.setFixedSize(action_width, 40)

        QTimer.singleShot(0, self._apply_responsive_table_columns)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def export_selected_results(self) -> None:
        if not self.selected_receipt_ids:
            QMessageBox.information(
                self,
                "Nothing selected",
                "Select one or more receipts before exporting.",
            )
            return

        rows: list[Any] = []
        missing_ids: list[int] = []
        for receipt_id in sorted(self.selected_receipt_ids):
            row = self.db.get_receipt(receipt_id)
            if row is None:
                missing_ids.append(receipt_id)
            else:
                rows.append(row)

        for receipt_id in missing_ids:
            self.selected_receipt_ids.discard(receipt_id)

        if not rows:
            self._update_selection_ui()
            QMessageBox.information(
                self,
                "Nothing to export",
                "The selected receipts are no longer available.",
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export selected receipts",
            str(Path.home() / "receipt-selection.csv"),
            "CSV files (*.csv)",
        )
        if not path:
            return

        self.db.export_rows(rows, Path(path), self.fields)
        QMessageBox.information(
            self,
            "Export complete",
            f"Exported {len(rows):,} selected receipt(s) to {path}",
        )
        self._update_selection_ui()

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------
    def refresh_results(self, *_args: object) -> None:
        query = self.search_input.text().strip()
        sort = self.sort_combo.currentText()

        # A changed search is a new selection context. This avoids hidden
        # selections from an earlier grouped view or different search term.
        if query != self._last_query:
            self.selected_receipt_ids.clear()
            self._search_result_ids.clear()
            self._last_query = query

        offset = self.current_page * self.page_size
        rows, total = self.db.browse_page(
            query=query,
            sort=sort,
            limit=self.page_size,
            offset=offset,
        )
        self.total_results = total

        page_count = max(1, (self.total_results + self.page_size - 1) // self.page_size)
        if self.current_page >= page_count:
            self.current_page = page_count - 1
            offset = self.current_page * self.page_size
            rows, total = self.db.browse_page(
                query=query,
                sort=sort,
                limit=self.page_size,
                offset=offset,
            )
            self.total_results = total

        self.last_rows = list(rows)

        # Search mode is intentionally flat rather than date-grouped. Cache every
        # matching receipt ID so "Select all results" applies across result pages.
        if query and self.total_results:
            all_rows, _ = self.db.browse_page(
                query=query,
                sort=sort,
                limit=max(1, self.total_results),
                offset=0,
            )
            self._search_result_ids = {int(row["id"]) for row in all_rows}
            self.selected_receipt_ids.intersection_update(self._search_result_ids)
        else:
            self._search_result_ids.clear()

        self._rebuild_groups()
        self._update_selection_ui()

        if self.total_results:
            first = (self.current_page * self.page_size) + 1
            last = first + len(self.last_rows) - 1
            self.result_count_label.setText(
                f"Showing {first:,}–{last:,} of {self.total_results:,} transaction(s)."
            )
        else:
            self.result_count_label.setText("No matching transactions.")

        self.page_label.setText(f"Page {self.current_page + 1:,} of {page_count:,}")
        self.previous_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page + 1 < page_count)

        if not query:
            self.active_receipt_count = self.total_results
        elif self.active_receipt_count is None:
            self.active_receipt_count = self.db.count_active_receipts()

        if self.active_receipt_count is not None:
            self.active_count_changed.emit(self.active_receipt_count)

    # ------------------------------------------------------------------
    # Trash
    # ------------------------------------------------------------------
    def open_trash(self) -> None:
        """Open the branded recovery dialog for soft-deleted receipts."""
        dialog = TrashDialog(self.db, self)
        dialog.receipts_restored.connect(self._trash_receipts_restored)
        dialog.exec()

    def _trash_receipts_restored(self) -> None:
        self.invalidate_active_count()
        self.refresh_results()
        self.receipt_restored.emit()

    def update_settings(
        self,
        fields: list[FieldDefinition],
        default_sort: str | None = None,
    ) -> None:
        self.fields = list(fields)

        if default_sort and default_sort in SORT_OPTIONS:
            self.sort_combo.blockSignals(True)
            self.sort_combo.setCurrentText(default_sort)
            self.sort_combo.blockSignals(False)

        self.current_page = 0
        self.invalidate_active_count()
        self.refresh_results()

    def shutdown(self) -> None:
        self.search_debounce_timer.stop()
