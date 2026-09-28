from __future__ import annotations

from pathlib import Path

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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...browse_model import BrowseTableModel, ReceiptActionsDelegate
from ...config import FieldDefinition
from ...database import ReceiptDatabase, SORT_OPTIONS
from ..icons import apply_button_icon


class BrowsePage(QWidget):
    """Paged receipt search/browse screen.

    Search, sorting, pagination, export and Trash presentation live here. Database
    mutations that belong to the wider application are requested through signals.
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
        self.last_rows: list = []
        self.active_receipt_count: int | None = None

        self.setObjectName("BrowsePage")

        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(250)
        self.search_debounce_timer.timeout.connect(self.refresh_results)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 30)
        layout.setSpacing(16)

        # Page heading ------------------------------------------------------
        eyebrow = QLabel("TRANSACTIONS")
        eyebrow.setObjectName("BrowseEyebrow")
        title = QLabel("Browse transactions")
        title.setObjectName("BrowseDisplayTitle")
        subtitle = QLabel(
            "Search the database using receipt numbers, names, member numbers, "
            "notes, dates or amounts."
        )
        subtitle.setObjectName("BrowseLead")
        subtitle.setWordWrap(True)

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Search / filter card --------------------------------------------
        filter_card = QFrame()
        filter_card.setObjectName("BrowseFilterCard")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(18, 16, 18, 16)
        filter_layout.setSpacing(14)

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

        self.group_by_date = QCheckBox("Group by date")
        self.group_by_date.setObjectName("BrowseGroupCheck")
        self.group_by_date.stateChanged.connect(self._browse_filters_changed)
        filter_layout.addWidget(self.group_by_date)
        layout.addWidget(filter_card)

        # Utility actions --------------------------------------------------
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(10)
        action_row.addStretch()

        export_btn = QPushButton("Export current page")
        export_btn.setObjectName("BrowseExportButton")
        export_btn.setToolTip(
            "Export only the rows currently loaded on this Browse page."
        )
        export_btn.clicked.connect(self.export_current_results)
        apply_button_icon(export_btn, "export", role="cyan", size=15)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("BrowseRefreshButton")
        refresh_btn.clicked.connect(self.refresh_results)
        apply_button_icon(refresh_btn, "refresh", role="muted", size=15)

        trash_btn = QPushButton("Trash")
        trash_btn.setObjectName("BrowseTrashButton")
        trash_btn.clicked.connect(self.open_trash)
        apply_button_icon(trash_btn, "trash", role="coral", size=15)

        action_row.addWidget(export_btn)
        action_row.addWidget(refresh_btn)
        action_row.addWidget(trash_btn)
        layout.addLayout(action_row)

        # Results card -----------------------------------------------------
        results_card = QFrame()
        results_card.setObjectName("BrowseResultsCard")
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(1, 1, 1, 1)
        results_layout.setSpacing(0)

        self.browse_model = BrowseTableModel(self.fields, self)
        self.results_view = QTableView()
        self.results_view.setObjectName("BrowseTableView")
        self.results_view.setModel(self.browse_model)
        self.results_view.setAlternatingRowColors(True)
        self.results_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.results_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.results_view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.results_view.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.results_view.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.results_view.setWordWrap(False)
        self.results_view.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.results_view.verticalHeader().setVisible(False)
        self.results_view.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self.results_view.verticalHeader().setDefaultSectionSize(50)
        self.results_view.horizontalHeader().setObjectName("BrowseHeader")
        self.results_view.horizontalHeader().setSectionsMovable(False)
        self.results_view.horizontalHeader().setMinimumHeight(46)
        self.results_view.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.results_view.doubleClicked.connect(self._edit_browse_index)

        self.actions_delegate = ReceiptActionsDelegate(self.results_view)
        self.actions_delegate.edit_requested.connect(self.edit_requested.emit)
        self.actions_delegate.delete_requested.connect(self.delete_requested.emit)
        self.results_view.setItemDelegateForColumn(
            self.browse_model.actions_column,
            self.actions_delegate,
        )
        self._configure_browse_columns()
        results_layout.addWidget(self.results_view, 1)

        footer = QFrame()
        footer.setObjectName("BrowseResultsFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(16, 13, 16, 14)
        footer_layout.setSpacing(8)

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

    @property
    def current_sort(self) -> str:
        return self.sort_combo.currentText()

    def schedule_refresh_results(self, *_args: object) -> None:
        """Coalesce rapid search edits into a single paged database/UI refresh."""
        self.current_page = 0
        self.search_debounce_timer.start()

    def _browse_filters_changed(self, *_args: object) -> None:
        """Reset paging when search presentation or sort order changes."""
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
        page_count = max(
            1,
            (self.total_results + self.page_size - 1) // self.page_size,
        )
        target = max(0, min(self.current_page + int(delta), page_count - 1))
        if target == self.current_page:
            return
        self.current_page = target
        self.refresh_results()

    def _configure_browse_columns(self) -> None:
        header = self.results_view.horizontalHeader()
        actions_column = self.browse_model.actions_column

        for column in range(self.browse_model.columnCount()):
            if column == actions_column:
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                self.results_view.setColumnWidth(column, 160)
            else:
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)

        self.results_view.setItemDelegateForColumn(
            actions_column,
            self.actions_delegate,
        )

    def _edit_browse_index(self, index) -> None:
        if index.column() == self.browse_model.actions_column:
            return
        receipt_id = self.browse_model.receipt_id_at(index)
        if receipt_id is not None:
            self.edit_requested.emit(receipt_id)

    def invalidate_active_count(self) -> None:
        self.active_receipt_count = None

    def refresh_results(self, *_args: object) -> None:
        query = self.search_input.text()
        sort = self.sort_combo.currentText()

        offset = self.current_page * self.page_size
        rows, total = self.db.browse_page(
            query=query,
            sort=sort,
            limit=self.page_size,
            offset=offset,
        )
        self.total_results = total

        page_count = max(
            1,
            (self.total_results + self.page_size - 1) // self.page_size,
        )
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
        self.browse_model.set_rows(
            self.last_rows,
            grouped=self.group_by_date.isChecked(),
        )
        self._configure_browse_columns()

        if self.total_results:
            first = (self.current_page * self.page_size) + 1
            last = first + len(self.last_rows) - 1
            self.result_count_label.setText(
                f"Showing {first:,}–{last:,} of {self.total_results:,} transaction(s)."
            )
        else:
            self.result_count_label.setText("No matching transactions.")

        self.page_label.setText(
            f"Page {self.current_page + 1:,} of {page_count:,}"
        )
        self.previous_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page + 1 < page_count)

        if not query:
            self.active_receipt_count = self.total_results
        elif self.active_receipt_count is None:
            self.active_receipt_count = self.db.count_active_receipts()

        if self.active_receipt_count is not None:
            self.active_count_changed.emit(self.active_receipt_count)

    def export_current_results(self) -> None:
        if not self.last_rows:
            QMessageBox.information(
                self,
                "Nothing to export",
                "There are no current results to export.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export results",
            str(Path.home() / "receipt-results.csv"),
            "CSV files (*.csv)",
        )
        if not path:
            return
        self.db.export_rows(self.last_rows, Path(path), self.fields)
        QMessageBox.information(self, "Export complete", f"Saved to {path}")

    def open_trash(self) -> None:
        """Show soft-deleted receipts and allow the user to restore them."""
        dialog = QDialog(self)
        dialog.setWindowTitle("ReceiptFlow Trash")
        dialog.resize(720, 460)

        layout = QVBoxLayout(dialog)

        heading = QLabel("Trash")
        heading.setObjectName("SectionTitle")
        helper = QLabel(
            "Deleted receipts remain in the database and can be restored here."
        )
        helper.setObjectName("Subtitle")
        helper.setWordWrap(True)

        layout.addWidget(heading)
        layout.addWidget(helper)

        trash_list = QListWidget()
        layout.addWidget(trash_list, 1)

        def populate() -> None:
            trash_list.clear()
            rows = self.db.trashed_receipts()

            if not rows:
                item = QListWidgetItem("Trash is empty")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                trash_list.addItem(item)
                return

            for row in rows:
                amount = (
                    f"${float(row['amount']):,.2f}"
                    if row["amount"] not in {None, ""}
                    else ""
                )
                name = row["name"] or row["receipt_no"] or "Unnamed receipt"
                deleted_at = row["deleted_at"] or ""
                text = (
                    f"{name} | {row['receipt_no'] or 'No receipt no'} | {amount}"
                    f"\nDeleted: {deleted_at}"
                )
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, int(row["id"]))
                trash_list.addItem(item)

        def restore_selected() -> None:
            item = trash_list.currentItem()
            if item is None:
                return

            receipt_id = item.data(Qt.ItemDataRole.UserRole)
            if receipt_id is None:
                return

            if self.db.restore_receipt(int(receipt_id)):
                self.invalidate_active_count()
                populate()
                self.refresh_results()
                self.receipt_restored.emit()

        populate()

        buttons = QHBoxLayout()
        restore_btn = QPushButton("Restore selected")
        restore_btn.setObjectName("PrimaryButton")
        restore_btn.clicked.connect(restore_selected)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)

        buttons.addWidget(restore_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        dialog.exec()

    def update_settings(
        self,
        fields: list[FieldDefinition],
        default_sort: str | None = None,
    ) -> None:
        self.fields = list(fields)
        self.browse_model.set_fields(self.fields)

        if default_sort and default_sort in SORT_OPTIONS:
            self.sort_combo.blockSignals(True)
            self.sort_combo.setCurrentText(default_sort)
            self.sort_combo.blockSignals(False)

        self._configure_browse_columns()
        self.current_page = 0
        self.invalidate_active_count()
        self.refresh_results()

    def shutdown(self) -> None:
        self.search_debounce_timer.stop()
