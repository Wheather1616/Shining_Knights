from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


from .assets import ArtworkLabel, LOGO_PATH
from .icons import apply_button_icon

class Sidebar(QFrame):
    """ReceiptFlow's primary navigation and database-status sidebar.

    The component owns all sidebar presentation and selection state. Application
    actions are exposed as signals so the sidebar does not need to know about the
    main window or the pages it controls.
    """

    page_requested = Signal(int)
    quick_receipt_requested = Signal()
    desktop_requested = Signal()

    HOME_PAGE = 0
    BROWSE_PAGE = 1
    SETTINGS_PAGE = 2

    def __init__(
        self,
        db_path: str | Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._page_buttons: dict[int, QPushButton] = {}

        self.setObjectName("BrandSidebar")
        self.setFixedWidth(276)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 24, 18, 20)
        layout.setSpacing(12)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        brand_logo = ArtworkLabel(LOGO_PATH, self)
        brand_logo.setObjectName("SidebarBrandLogo")
        brand_logo.setFixedSize(42, 42)
        brand_row.addWidget(brand_logo, 0, Qt.AlignmentFlag.AlignTop)

        brand_lockup = QVBoxLayout()
        brand_lockup.setSpacing(1)
        app_title = QLabel("ReceiptFlow")
        app_title.setObjectName("SidebarBrandTitle")
        app_tagline = QLabel("Receipt manager")
        app_tagline.setObjectName("SidebarTagline")
        app_tagline.setWordWrap(True)
        brand_lockup.addWidget(app_title)
        brand_lockup.addWidget(app_tagline)
        brand_row.addLayout(brand_lockup, 1)

        layout.addLayout(brand_row)
        layout.addSpacing(10)

        self.home_btn = self._page_button("Home", self.HOME_PAGE)
        self.browse_btn = self._page_button(
            "Browse transactions",
            self.BROWSE_PAGE,
        )
        self.quick_btn = self._action_button(
            "Quick receipt",
            self.quick_receipt_requested.emit,
        )
        self.desktop_btn = self._action_button(
            "Desktop tab",
            self.desktop_requested.emit,
        )
        self.settings_btn = self._page_button("Settings", self.SETTINGS_PAGE)

        apply_button_icon(self.home_btn, "home", role="inverse", size=16)
        apply_button_icon(self.browse_btn, "browse", role="inverse", size=16)
        apply_button_icon(self.quick_btn, "quick_receipt", role="inverse", size=16)
        apply_button_icon(self.desktop_btn, "desktop", role="inverse", size=16)
        apply_button_icon(self.settings_btn, "settings", role="inverse", size=16)

        for button in (
            self.home_btn,
            self.browse_btn,
            self.quick_btn,
            self.desktop_btn,
            self.settings_btn,
        ):
            layout.addWidget(button)

        layout.addStretch()

        status_card = QFrame()
        status_card.setObjectName("SidebarStatusCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(18, 16, 18, 16)
        status_layout.setSpacing(8)

        db_status = QLabel("Database connected")
        db_status.setObjectName("SidebarStatusTitle")
        db_storage = QLabel("Local encrypted storage")
        db_storage.setObjectName("SidebarStatusMeta")

        view_location_btn = QPushButton("View location")
        view_location_btn.setObjectName("SidebarLinkButton")
        view_location_btn.clicked.connect(self._open_database_location)
        apply_button_icon(view_location_btn, "folder", role="inverse", size=14)

        status_layout.addWidget(db_status)
        status_layout.addWidget(db_storage)
        status_layout.addSpacing(2)
        status_layout.addWidget(
            view_location_btn,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(status_card)

        self.set_current_page(self.HOME_PAGE)

    def _page_button(self, text: str, page_index: int) -> QPushButton:
        button = self._make_button(text)
        button.setCheckable(True)
        button.setProperty("pageButton", True)
        button.clicked.connect(
            lambda _checked=False, index=page_index: self.page_requested.emit(index)
        )
        self._page_buttons[page_index] = button
        return button

    def _action_button(self, text: str, action) -> QPushButton:
        button = self._make_button(text)
        button.clicked.connect(lambda _checked=False, callback=action: callback())
        return button

    @staticmethod
    def _make_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("SidebarNavButton")
        button.setMinimumHeight(48)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def set_current_page(self, page_index: int) -> None:
        """Update the highlighted navigation item for the active stacked page."""
        for index, button in self._page_buttons.items():
            button.setChecked(index == page_index)
            button.style().unpolish(button)
            button.style().polish(button)

    def set_database_path(self, db_path: str | Path) -> None:
        """Update the displayed database location without rebuilding the sidebar."""
        self._db_path = Path(db_path)

    def _open_database_location(self) -> None:
        target = self._db_path.parent if self._db_path.parent.exists() else self._db_path
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
