"""ReceiptFlow application bootstrap.

This module owns process startup only: create QApplication, enforce the
single-instance rule, construct the main window, wire shutdown hooks and start
the Qt event loop. UI implementation lives under ``receipt_app.ui``.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from .db_crypto import DatabaseEncryptionError
from .security import SecureKeyStoreError
from .single_instance import SingleInstanceManager
from .styles import APP_QSS
from .ui.main_window import ReceiptMainWindow
from .ui.theme import load_application_fonts


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ReceiptFlow")
    app.setApplicationDisplayName("ReceiptFlow")
    load_application_fonts()
    app.setStyleSheet(APP_QSS)

    instance = SingleInstanceManager(app)
    try:
        is_primary, notified = instance.acquire()
    except RuntimeError as exc:
        QMessageBox.critical(None, "ReceiptFlow startup error", str(exc))
        return 1

    if not is_primary:
        if not notified:
            QMessageBox.information(
                None,
                "ReceiptFlow is already running",
                "Another ReceiptFlow process already owns the application lock, "
                "but it could not be contacted. Check the system tray or Task Manager "
                "instead of opening another copy.",
            )
        return 0

    try:
        window = ReceiptMainWindow()
    except (SecureKeyStoreError, DatabaseEncryptionError) as exc:
        instance.release()
        QMessageBox.critical(
            None,
            "ReceiptFlow security error",
            str(exc)
            + "\n\nReceiptFlow has stopped rather than creating or overwriting a database.",
        )
        return 1

    instance.activation_requested.connect(window.show_normal)
    app.aboutToQuit.connect(window.prepare_shutdown)
    app.aboutToQuit.connect(instance.release)

    if not window.settings.start_minimised:
        window.show()
    if window.settings.show_desktop_tab_on_launch:
        window.show_desktop_tab()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
