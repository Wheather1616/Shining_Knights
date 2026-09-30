"""ReceiptFlow branded artwork and application icon helpers.

Large Canva-style illustrations are rendered to PNG at build/source time for
predictable Qt display. The original SVGs remain in ``assets`` as editable
source artwork.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QWidget


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

LOGO_PATH = ASSETS_DIR / "Logo.png"
HOME_ILLUSTRATION_PATH = ASSETS_DIR / "Illustration.png"
RECEIPT_ILLUSTRATION_PATH = ASSETS_DIR / "Add-Receipt.png"


def asset_path(filename: str) -> Path:
    """Return the path to a bundled ReceiptFlow asset."""
    return ASSETS_DIR / filename


def app_icon() -> QIcon:
    """Return the ReceiptFlow application icon with a safe SVG fallback."""
    if LOGO_PATH.exists():
        return QIcon(str(LOGO_PATH))
    svg_path = ASSETS_DIR / "Logo.svg"
    return QIcon(str(svg_path)) if svg_path.exists() else QIcon()


class ArtworkLabel(QLabel):
    """A QLabel that keeps branded artwork crisp and aspect-ratio correct."""

    def __init__(
        self,
        image_path: str | Path,
        parent: QWidget | None = None,
        *,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
    ) -> None:
        super().__init__(parent)
        self._source = QPixmap(str(image_path))
        self.setAlignment(alignment)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setMinimumSize(1, 1)
        self._refresh_pixmap()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._source.isNull():
            self.clear()
            return
        target = self.contentsRect().size()
        if target.width() <= 0 or target.height() <= 0:
            return
        self.setPixmap(
            self._source.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
