from __future__ import annotations

import hashlib
from PySide6.QtCore import QObject, QLockFile, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from .paths import app_support_dir


class SingleInstanceManager(QObject):
    """Enforce one ReceiptFlow process per OS user and activate it on relaunch.

    QLockFile provides the actual cross-process exclusion. QLocalServer is only
    the signalling channel used by a second launch to ask the existing process
    to show itself. Using both avoids relying on QLocalServer alone on Windows,
    where multiple named-pipe listeners may otherwise be possible.
    """

    activation_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        runtime_dir = app_support_dir() / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        self.lock = QLockFile(str(runtime_dir / "receiptflow.lock"))
        # This is a long-lived application lock. Qt will still use PID/process
        # information to identify genuinely stale lock files after a crash.
        self.lock.setStaleLockTime(0)

        user_scope = hashlib.sha256(
            str(app_support_dir().resolve()).encode("utf-8", errors="ignore")
        ).hexdigest()[:16]
        self.server_name = f"ReceiptFlow-{user_scope}"

        self.server = QLocalServer(self)
        try:
            self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        except (AttributeError, TypeError):
            # Older Qt builds may not expose the scoped option in the same form.
            pass
        self.server.newConnection.connect(self._handle_new_connection)

        self._owns_lock = False

    def acquire(self) -> tuple[bool, bool]:
        """Return ``(is_primary, existing_instance_notified)``.

        A secondary launch never proceeds into database/window initialisation.
        """
        if not self.lock.tryLock(0):
            lock_error = self.lock.error()
            if lock_error != QLockFile.LockError.LockFailedError:
                raise RuntimeError(
                    "ReceiptFlow could not create its single-instance lock. "
                    "Check permissions and free disk space for the local app-data folder."
                )

            notified = self.notify_existing_instance()

            # QLockFile automatically removes lock files it can prove are stale.
            # If the file changed between calls, one immediate retry handles it.
            if not notified and self.lock.tryLock(0):
                self._owns_lock = True
                self._start_server()
                return True, False

            return False, notified

        self._owns_lock = True
        self._start_server()
        return True, False

    def _start_server(self) -> None:
        if self.server.listen(self.server_name):
            return

        # We already own the exclusive QLockFile, so no valid ReceiptFlow
        # instance can be using this endpoint. Removing a stale Unix socket is
        # therefore safe here. On Windows removeServer() is effectively a no-op.
        QLocalServer.removeServer(self.server_name)
        if self.server.listen(self.server_name):
            return

        error = self.server.errorString()
        self.release()
        raise RuntimeError(
            "ReceiptFlow could not create its local single-instance endpoint: "
            f"{error}"
        )

    def notify_existing_instance(self) -> bool:
        """Ask the existing ReceiptFlow process to show/raise its main window."""
        for timeout_ms in (150, 300, 550):
            socket = QLocalSocket()
            socket.connectToServer(self.server_name)
            if socket.waitForConnected(timeout_ms):
                socket.write(b"activate\n")
                socket.flush()
                socket.waitForBytesWritten(250)
                socket.disconnectFromServer()
                return True
            socket.abort()
        return False

    def _handle_new_connection(self) -> None:
        received_connection = False
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if socket is None:
                break
            received_connection = True
            socket.disconnectFromServer()
            socket.deleteLater()

        if received_connection:
            self.activation_requested.emit()

    def release(self) -> None:
        """Release the local endpoint and process lock during normal shutdown."""
        if self.server.isListening():
            self.server.close()
        if self._owns_lock:
            self.lock.unlock()
            self._owns_lock = False
