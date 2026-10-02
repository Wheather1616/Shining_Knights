"""ShiningKnights customer/job application bootstrap."""
from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from .single_instance import SingleInstanceManager
from .styles import APP_QSS
from .ui.main_window import CustomerMainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('ShiningKnights')
    app.setApplicationDisplayName('ShiningKnights')
    app.setStyleSheet(APP_QSS)
    instance = SingleInstanceManager(app)
    try:
        primary,notified = instance.acquire()
        if not primary:
            if not notified: QMessageBox.information(None,'ShiningKnights is running','Check the taskbar or Task Manager for the existing application.')
            return 0
        window = CustomerMainWindow()
    except Exception as exc:
        instance.release()
        QMessageBox.critical(None,'ShiningKnights startup error',str(exc)+'\n\nThe application has stopped. Existing data will not be reset automatically.')
        return 1
    instance.activation_requested.connect(window.show_normal)
    app.aboutToQuit.connect(window.prepare_shutdown)
    app.aboutToQuit.connect(instance.release)
    window.show()
    return app.exec()

if __name__ == '__main__': raise SystemExit(run())
