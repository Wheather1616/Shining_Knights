from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..backup import DatabaseBackupManager
from ..config import CORE_FIELD_KEYS, FieldDefinition, SettingsStore
from ..database import ReceiptDatabase, ReceiptRecord
from ..paths import default_backup_dir
from ..styles import APP_QSS
from .assets import ArtworkLabel, RECEIPT_ILLUSTRATION_PATH, app_icon
from .pages import BrowsePage, HomePage, SettingsPage
from .sidebar import Sidebar
from .widgets.desktop_panel import DesktopReceiptPanel
from .widgets.receipt_entry_form import ReceiptEntryForm

class ReceiptFormDialog(QDialog):
    """Branded dialog wrapper around the shared :class:`ReceiptEntryForm`."""

    def __init__(
        self,
        fields: list[FieldDefinition],
        parent: QWidget | None = None,
        title: str = "New Receipt",
        heading: str = "Add a receipt",
        subtitle: str = "Capture the transaction as soon as it is completed.",
        initial_values: dict[str, Any] | None = None,
        quick_only: bool = True,
        catalog: dict[str, dict[str, float]] | None = None,
        surcharge_rates: dict[str, float] | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("ReceiptFormDialog")
        self.setWindowTitle(title)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(900, 700)
        self.resize(980, 780)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 18)
        root.setSpacing(16)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(16)

        form_card = QFrame()
        form_card.setObjectName("ReceiptDialogFormCard")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(30, 26, 30, 26)
        form_layout.setSpacing(8)

        eyebrow_text = "EDIT RECEIPT" if title.strip().lower().startswith("edit") else "NEW RECEIPT"
        eyebrow = QLabel(eyebrow_text)
        eyebrow.setObjectName("ReceiptDialogEyebrow")
        title_label = QLabel(heading)
        title_label.setObjectName("ReceiptDialogTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("ReceiptDialogSubtitle")
        subtitle_label.setWordWrap(True)

        form_layout.addWidget(eyebrow)
        form_layout.addWidget(title_label)
        form_layout.addWidget(subtitle_label)
        form_layout.addSpacing(12)

        form_scroll = QScrollArea()
        form_scroll.setObjectName("ReceiptDialogFormScroll")
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_content = QWidget()
        form_content.setObjectName("ReceiptDialogFormContent")
        form_content_layout = QVBoxLayout(form_content)
        form_content_layout.setContentsMargins(0, 0, 6, 0)
        form_content_layout.setSpacing(0)

        self.entry_form = ReceiptEntryForm(
            fields,
            form_content,
            quick_only=quick_only,
            catalog=catalog,
            surcharge_rates=surcharge_rates,
            compact=False,
            field_label_object_name="ReceiptDialogFieldLabel",
        )
        self.entry_form.setObjectName("ReceiptDialogEntryForm")
        form_content_layout.addWidget(self.entry_form)
        form_content_layout.addStretch()
        form_scroll.setWidget(form_content)
        form_layout.addWidget(form_scroll, 1)

        helper_card = QFrame()
        helper_card.setObjectName("ReceiptDialogHelperCard")
        helper_card.setMinimumWidth(250)
        helper_card.setMaximumWidth(290)
        helper_layout = QVBoxLayout(helper_card)
        helper_layout.setContentsMargins(24, 24, 24, 24)
        helper_layout.setSpacing(12)

        illustration = QFrame()
        illustration.setObjectName("ReceiptDialogIllustration")
        illustration.setMinimumHeight(185)
        illustration_layout = QVBoxLayout(illustration)
        illustration_layout.setContentsMargins(12, 12, 12, 12)

        illustration_art = ArtworkLabel(RECEIPT_ILLUSTRATION_PATH, illustration)
        illustration_art.setObjectName("ReceiptDialogIllustrationArt")
        illustration_layout.addWidget(illustration_art, 1)
        helper_layout.addWidget(illustration)
        helper_layout.addSpacing(8)

        helper_title = QLabel("Keep it handy")
        helper_title.setObjectName("ReceiptDialogHelperTitle")
        helper_copy = QLabel(
            "Enter the key details from the receipt. This keeps records accurate "
            "and makes transactions easier to find later."
        )
        helper_copy.setObjectName("ReceiptDialogHelperBody")
        helper_copy.setWordWrap(True)
        helper_layout.addWidget(helper_title)
        helper_layout.addWidget(helper_copy)

        divider = QFrame()
        divider.setObjectName("ReceiptDialogDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        helper_layout.addWidget(divider)

        tips_title = QLabel("QUICK TIPS")
        tips_title.setObjectName("ReceiptDialogTipsTitle")
        helper_layout.addWidget(tips_title)
        helper_layout.addWidget(
            self._tip_row("coral", "Choose the right category for easier reporting.")
        )
        helper_layout.addWidget(
            self._tip_row("amethyst", "Include the payment type to track transactions.")
        )
        helper_layout.addWidget(
            self._tip_row("cyan", "Add notes when extra context will help later.")
        )
        helper_layout.addStretch()

        body.addWidget(form_card, 1)
        body.addWidget(helper_card)
        root.addLayout(body, 1)

        footer = QFrame()
        footer.setObjectName("ReceiptDialogFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(4, 14, 4, 0)
        footer_layout.setSpacing(12)

        footer_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ReceiptDialogCancelButton")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("ReceiptDialogSaveButton")
        save_btn.setMinimumWidth(130)
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        footer_layout.addWidget(save_btn)

        root.addWidget(footer)

        if initial_values:
            self.entry_form.set_values(initial_values)

    @staticmethod
    def _tip_row(accent: str, text: str) -> QFrame:
        row = QFrame()
        row.setObjectName("ReceiptDialogTipRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        dot = QLabel("")
        dot.setObjectName("ReceiptDialogTipDot")
        dot.setProperty("accent", accent)
        dot.setFixedSize(12, 12)
        copy = QLabel(text)
        copy.setObjectName("ReceiptDialogTipText")
        copy.setWordWrap(True)

        layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(copy, 1)
        return row

    def values(self) -> dict[str, Any]:
        return self.entry_form.values()

    def accept(self) -> None:
        issue = self.entry_form.validation_issue()
        if issue is not None:
            QMessageBox.warning(self, issue.title, issue.dialog_message)
            return
        super().accept()


class ReceiptMainWindow(QMainWindow):
    """Top-level ReceiptFlow shell and cross-component coordinator."""

    def __init__(self):
        super().__init__()
        self.store = SettingsStore()
        self.settings = self.store.load()
        self.db = ReceiptDatabase(self.settings.db_path)
        self.backup_manager = DatabaseBackupManager(
            self.settings.db_path,
            default_backup_dir(),
            self.db.key_hex,
        )
        self.tray: QSystemTrayIcon | None = None
        self.tray_menu: QMenu | None = None
        self.desktop_panel: DesktopReceiptPanel | None = None

        self.setWindowTitle("ReceiptFlow")
        self.setWindowIcon(app_icon())
        self.resize(1240, 820)
        self.setStyleSheet(APP_QSS)

        self.stack = QStackedWidget()
        self.setCentralWidget(self._build_shell())
        self._build_pages()
        self.sidebar.set_current_page(0)
        self._setup_tray()

        # Let the first window paint before doing backup work. The recurring timer
        # only checks whether the next hourly snapshot is due.
        QTimer.singleShot(1500, self.run_automatic_backup)
        self.backup_timer = QTimer(self)
        self.backup_timer.setInterval(15 * 60 * 1000)
        self.backup_timer.timeout.connect(self.run_automatic_backup)
        self.backup_timer.start()

        self._quitting = False
        self.refresh_results()

    # ------------------------------------------------------------------
    # Application shell / navigation
    # ------------------------------------------------------------------

    def _build_shell(self) -> QWidget:
        shell = QWidget()
        shell.setObjectName("AppShell")
        root = QHBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar(self.settings.db_path, shell)
        self.sidebar.page_requested.connect(self._show_page)
        self.sidebar.quick_receipt_requested.connect(self.open_quick_receipt)
        self.sidebar.desktop_requested.connect(self.show_desktop_tab)
        self.stack.currentChanged.connect(self.sidebar.set_current_page)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)
        return shell

    def _show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def _build_pages(self) -> None:
        self.home_page = HomePage(self)
        self.browse_page = BrowsePage(
            self.db,
            self.settings.fields,
            self.settings.default_sort,
            self,
        )
        self.settings_page = SettingsPage(
            self.settings,
            self.store,
            self.db,
            self,
            current_sort_provider=lambda: self.browse_page.current_sort,
        )

        self.home_page.quick_receipt_requested.connect(self.open_quick_receipt)
        self.home_page.browse_requested.connect(lambda: self._show_page(1))
        self.home_page.desktop_requested.connect(self.show_desktop_tab)
        self.home_page.settings_requested.connect(lambda: self._show_page(2))

        self.browse_page.edit_requested.connect(self.edit_receipt)
        self.browse_page.delete_requested.connect(self.delete_receipt)
        self.browse_page.receipt_restored.connect(self.refresh_desktop_tab)
        self.browse_page.active_count_changed.connect(
            self.home_page.set_receipt_count
        )

        self.settings_page.settings_saved.connect(self._settings_saved)

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.browse_page)
        self.stack.addWidget(self.settings_page)

    def _settings_saved(self) -> None:
        """Apply settings that affect components outside the Settings page."""
        self._setup_tray()
        self.browse_page.update_settings(
            self.settings.fields,
            self.settings.default_sort,
        )

        if self.desktop_panel is not None:
            self.desktop_panel.set_panel_size(
                self.settings.desktop_tab_width,
                self.settings.desktop_tab_height,
            )
            self.desktop_panel.update_context(
                self.db,
                self.settings.fields,
                self.settings.catalog,
                self.settings.payment_surcharges,
            )

    # ------------------------------------------------------------------
    # Receipt create / edit / delete
    # ------------------------------------------------------------------

    def open_quick_receipt(self) -> None:
        suggested_receipt_no = self.db.next_receipt_number()
        dialog = ReceiptFormDialog(
            self.settings.fields,
            self,
            initial_values={"receipt_no": suggested_receipt_no},
            catalog=self.settings.catalog,
            surcharge_rates=self.settings.payment_surcharges,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        values = dialog.values()

        # Refresh an untouched auto-suggestion in case another receipt was saved
        # while this dialog was open. Manual receipt-number changes are preserved.
        if str(values.get("receipt_no", "")) == suggested_receipt_no:
            values["receipt_no"] = self.db.next_receipt_number()

        record = self._record_from_values(values, "manual")
        self.db.upsert_receipt(record)
        self._refresh_after_receipt_change()
        QMessageBox.information(
            self,
            "Receipt saved",
            "The receipt was added to the database.",
        )

    def _row_values_for_edit(self, row: Any) -> dict[str, Any]:
        custom = json.loads(row["custom_fields"] or "{}")
        values: dict[str, Any] = {}
        for field_def in self.settings.fields:
            if field_def.key in CORE_FIELD_KEYS:
                values[field_def.key] = row[field_def.key]
            else:
                values[field_def.key] = custom.get(field_def.key, "")

        for key in (
            "surcharge_base_amount",
            "surcharge_percentage",
            "surcharge_amount",
        ):
            if key in custom:
                values[key] = custom[key]
        return values

    def _record_from_values(
        self,
        values: dict[str, Any],
        source: str,
    ) -> ReceiptRecord:
        custom = {
            key: value
            for key, value in values.items()
            if key not in CORE_FIELD_KEYS
        }
        return ReceiptRecord(
            receipt_no=str(values.get("receipt_no", "") or ""),
            transaction_date=str(values.get("transaction_date", "") or ""),
            name=str(values.get("name", "") or ""),
            amount=float(values.get("amount", 0) or 0),
            payment_type=str(values.get("payment_type", "") or ""),
            member_no=str(values.get("member_no", "") or ""),
            notes=str(values.get("notes", "") or ""),
            custom_fields=custom,
            source=source,
        )

    def edit_receipt(self, receipt_id: int) -> None:
        row = self.db.get_receipt(receipt_id)
        if row is None:
            QMessageBox.warning(
                self,
                "Receipt not found",
                "This receipt could not be found. It may have already been deleted.",
            )
            self._refresh_after_receipt_change()
            return

        dialog = ReceiptFormDialog(
            self.settings.fields,
            self,
            title="Edit Receipt",
            heading="Edit receipt",
            subtitle=(
                "Update the receipt details and save the corrected data back to the database."
            ),
            initial_values=self._row_values_for_edit(row),
            quick_only=False,
            catalog=self.settings.catalog,
            surcharge_rates=self.settings.payment_surcharges,
        )
        if dialog.exec() != QDialog.Accepted:
            return

        record = self._record_from_values(
            dialog.values(),
            str(row["source"] or "manual"),
        )
        self.db.update_receipt(receipt_id, record)
        self._refresh_after_receipt_change()
        QMessageBox.information(
            self,
            "Receipt updated",
            "The receipt was updated successfully.",
        )

    def delete_receipt(self, receipt_id: int) -> None:
        row = self.db.get_receipt(receipt_id)
        if row is None:
            QMessageBox.warning(
                self,
                "Receipt not found",
                "This receipt could not be found. It may have already been deleted.",
            )
            self._refresh_after_receipt_change()
            return

        amount = (
            f"${float(row['amount']):,.2f}"
            if row["amount"] not in {None, ""}
            else ""
        )
        description = row["name"] or row["receipt_no"] or "this receipt"
        confirm = QMessageBox.question(
            self,
            "Move receipt to Trash",
            f"Move {description} {amount} to Trash? You can restore it later.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.db.delete_receipt(receipt_id)
        self._refresh_after_receipt_change()
        QMessageBox.information(
            self,
            "Moved to Trash",
            "The receipt was moved to Trash and can be restored.",
        )

    def _refresh_after_receipt_change(self) -> None:
        self.browse_page.invalidate_active_count()
        self.browse_page.refresh_results()
        self.refresh_desktop_tab()

    def refresh_results(self) -> None:
        """Compatibility coordinator used after application-level mutations."""
        self.browse_page.refresh_results()

    # ------------------------------------------------------------------
    # Automatic backup
    # ------------------------------------------------------------------

    def run_automatic_backup(self) -> None:
        """Create an hourly recovery point without interrupting normal use."""
        try:
            self.backup_manager.create_backup_if_due()
        except Exception as exc:
            # Backups should never crash the receipt-entry workflow.
            print(f"ReceiptFlow automatic backup failed: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Desktop receipt panel
    # ------------------------------------------------------------------

    def show_desktop_tab(self) -> None:
        if self.desktop_panel is None:
            self.desktop_panel = DesktopReceiptPanel(
                self.db,
                self.settings.fields,
                self._desktop_receipt_saved,
                self.show_normal,
                self.save_desktop_tab_position,
                self.delete_receipt,
                self.settings.desktop_tab_width,
                self.settings.desktop_tab_height,
                catalog=self.settings.catalog,
                surcharge_rates=self.settings.payment_surcharges,
            )
            if (
                self.settings.desktop_tab_x is not None
                and self.settings.desktop_tab_y is not None
            ):
                self.desktop_panel.move(
                    self.settings.desktop_tab_x,
                    self.settings.desktop_tab_y,
                )
            else:
                self.desktop_panel.move(18, 44)
        else:
            self.desktop_panel.set_panel_size(
                self.settings.desktop_tab_width,
                self.settings.desktop_tab_height,
            )
            self.desktop_panel.update_context(
                self.db,
                self.settings.fields,
                self.settings.catalog,
                self.settings.payment_surcharges,
            )
        self.desktop_panel.show()
        self.desktop_panel.raise_()
        self.desktop_panel.activateWindow()

    def save_desktop_tab_position(self, position: QPoint) -> None:
        self.settings.desktop_tab_x = position.x()
        self.settings.desktop_tab_y = position.y()
        self.store.save(self.settings)

    def _desktop_receipt_saved(self) -> None:
        self.browse_page.invalidate_active_count()
        self.browse_page.refresh_results()
        self.refresh_desktop_tab()

    def refresh_desktop_tab(self) -> None:
        if self.desktop_panel is not None:
            self.desktop_panel.update_context(
                self.db,
                self.settings.fields,
                self.settings.catalog,
                self.settings.payment_surcharges,
            )
            self.desktop_panel.refresh()

    # ------------------------------------------------------------------
    # Tray / lifecycle
    # ------------------------------------------------------------------

    def _app_icon(self):
        return app_icon()

    def _setup_tray(self) -> None:
        if self.tray:
            self.tray.hide()
            self.tray.setContextMenu(None)
            self.tray.deleteLater()
            self.tray = None
        if self.tray_menu is not None:
            self.tray_menu.deleteLater()
            self.tray_menu = None
        if (
            not self.settings.enable_tray
            or not QSystemTrayIcon.isSystemTrayAvailable()
        ):
            app = QApplication.instance()
            if app is not None:
                app.setQuitOnLastWindowClosed(True)
            return

        self.tray = QSystemTrayIcon(self._app_icon(), self)
        menu = QMenu(self)
        self.tray_menu = menu

        show_action = QAction("Show ReceiptFlow", self)
        show_action.triggered.connect(self.show_normal)
        new_action = QAction("New receipt", self)
        new_action.triggered.connect(self.open_quick_receipt)
        browse_action = QAction("Browse transactions", self)
        browse_action.triggered.connect(
            lambda: (self.show_normal(), self.stack.setCurrentIndex(1))
        )
        desktop_action = QAction("Show desktop tab", self)
        desktop_action.triggered.connect(self.show_desktop_tab)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)

        menu.addAction(show_action)
        menu.addAction(new_action)
        menu.addAction(browse_action)
        menu.addAction(desktop_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.open_quick_receipt()
            if reason == QSystemTrayIcon.Trigger
            else None
        )
        self.tray.show()

        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(False)

    def show_normal(self) -> None:
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def quit_application(self) -> None:
        """Perform deterministic tray/timer cleanup, then quit the event loop."""
        self.prepare_shutdown()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def prepare_shutdown(self) -> None:
        if self._quitting:
            return
        self._quitting = True

        if hasattr(self, "backup_timer"):
            self.backup_timer.stop()
        if hasattr(self, "browse_page"):
            self.browse_page.shutdown()

        if self.desktop_panel is not None:
            self.desktop_panel.hide()
            self.desktop_panel.deleteLater()
            self.desktop_panel = None

        if self.tray is not None:
            self.tray.hide()
            self.tray.setContextMenu(None)
            self.tray.deleteLater()
            self.tray = None
        if self.tray_menu is not None:
            self.tray_menu.deleteLater()
            self.tray_menu = None

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._quitting:
            event.accept()
        elif self.tray and self.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()
