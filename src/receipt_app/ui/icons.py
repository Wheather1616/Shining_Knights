"""ReceiptFlow semantic icon provider.

The UI refers to icons by purpose (``home``, ``browse``, ``quick_receipt`` ...)
rather than by asset filename.  The provider resolves the corresponding SVG from
``assets/icons/flaticons`` and renders a colour-appropriate copy for the current
UI role.

Keeping this mapping in one place means changing an icon later does not require
editing Sidebar, Home, Browse, Settings, or other UI components.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton

try:
    from PySide6.QtSvg import QSvgRenderer
except ImportError:  # pragma: no cover - defensive fallback for unusual Qt builds
    QSvgRenderer = None  # type: ignore[assignment]


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Support the intended folder name plus the earlier typo, so moving between local
# branches does not silently remove icons.
ICON_DIR_CANDIDATES = (
    ASSETS_DIR / "icons" / "flaticons",
    ASSETS_DIR / "icons" / "flavicons",
)

# UI code should only use these semantic names.
ICON_FILES: dict[str, str] = {
    "home": "home.svg",
    "browse": "search.svg",
    "search": "search.svg",
    "quick_receipt": "add.svg",
    "add": "add.svg",
    "desktop": "computer.svg",
    "settings": "settings-sliders.svg",
}

# Brand-aware colour roles.  Add new roles here rather than hard-coding colours
# inside individual widgets.
ICON_COLOURS: dict[str, str] = {
    "inverse": "#fff7f4",
    "bordeaux": "#52050a",
    "text": "#302a30",
    "muted": "#6b6267",
    "cyan": "#258ea6",
    "amethyst": "#a846a0",
    "coral": "#f87666",
}


def _icon_path(name: str) -> Path | None:
    filename = ICON_FILES.get(name, name if name.lower().endswith(".svg") else f"{name}.svg")
    for directory in ICON_DIR_CANDIDATES:
        direct = directory / filename
        if direct.exists():
            return direct
        if directory.exists():
            # Flaticon downloads may preserve nested pack directories.
            for match in directory.rglob(filename):
                if match.is_file():
                    return match
    return None


def _colour_svg(svg: str, colour: str) -> str:
    """Apply a single brand colour to a solid/outline Flaticon SVG.

    The selected ReceiptFlow icon family is monochrome.  Styling SVG elements at
    render time lets the same source asset work as white sidebar navigation,
    Bordeaux buttons, and coloured Home-card accents.
    """
    style = (
        "<style>"
        f"path,rect,circle,ellipse,polygon,polyline,line {{ fill: {colour} !important; }}"
        f"line,polyline {{ stroke: {colour} !important; }}"
        "</style>"
    )
    match = re.search(r"<svg\b[^>]*>", svg, flags=re.IGNORECASE)
    if not match:
        return svg
    return svg[: match.end()] + style + svg[match.end() :]


@lru_cache(maxsize=256)
def _render_icon(name: str, role: str, size: int) -> QIcon:
    path = _icon_path(name)
    if path is None:
        return QIcon()

    # If QtSvg is unavailable, still show the original SVG rather than failing
    # application startup.  Normal PySide6 installations include QtSvg.
    if QSvgRenderer is None:
        return QIcon(str(path))

    colour = ICON_COLOURS.get(role, ICON_COLOURS["text"])
    try:
        svg = path.read_text(encoding="utf-8")
        svg = _colour_svg(svg, colour)
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        if not renderer.isValid():
            return QIcon(str(path))

        pixel_size = max(1, int(size))
        pixmap = QPixmap(pixel_size, pixel_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    except (OSError, UnicodeError):
        return QIcon(str(path))


def icon(name: str, *, role: str = "text", size: int = 16) -> QIcon:
    """Return a semantic ReceiptFlow icon."""
    return _render_icon(name, role, int(size))


def icon_pixmap(name: str, *, role: str = "text", size: int = 16) -> QPixmap:
    """Return a semantic icon as a pixmap for labels/card accents."""
    return icon(name, role=role, size=size).pixmap(QSize(size, size))


def apply_button_icon(
    button: QPushButton,
    name: str,
    *,
    role: str = "text",
    size: int = 16,
) -> None:
    """Apply a semantic icon to a QPushButton without changing its styling."""
    button.setIcon(icon(name, role=role, size=size))
    button.setIconSize(QSize(size, size))


def apply_label_icon(
    label: QLabel,
    name: str,
    *,
    role: str = "text",
    size: int = 16,
) -> None:
    """Apply a semantic icon to a QLabel used as an icon container."""
    label.setPixmap(icon_pixmap(name, role=role, size=size))
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
