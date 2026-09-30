from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..assets import ArtworkLabel, HOME_ILLUSTRATION_PATH
from ..icons import apply_label_icon


class HomePage(QWidget):
    """ReceiptFlow home dashboard with vertical responsive behaviour.

    The horizontal card layout is preserved, while the page can tighten its
    vertical rhythm for shorter windows and fall back to one clean outer
    scrollbar instead of allowing cards to crowd or clip each other.
    """

    quick_receipt_requested = Signal()
    browse_requested = Signal()
    desktop_requested = Signal()
    settings_requested = Signal()

    COMPACT_HEIGHT = 780
    DENSE_HEIGHT = 650

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("HomePage")
        self._vertical_mode: str | None = None
        self._feature_cards: list[QFrame] = []
        self._feature_layouts: list[QVBoxLayout] = []

        # The Home screen now has a single outer scroll area. This guarantees
        # that a shorter non-full-screen window never forces neighbouring cards
        # into each other. Horizontal scrolling is intentionally disabled.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("HomeScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        outer.addWidget(self.scroll_area)

        self.content = QWidget()
        self.content.setObjectName("HomeContent")
        self.content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.scroll_area.setWidget(self.content)

        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(38, 34, 38, 28)
        self.content_layout.setSpacing(20)

        eyebrow = QLabel("WELCOME TO")
        eyebrow.setObjectName("HomeEyebrow")
        title = QLabel("Receipt database")
        title.setObjectName("HomeDisplayTitle")
        subtitle = QLabel("Capture, search and manage club receipts from one place.")
        subtitle.setObjectName("HomeLead")
        subtitle.setWordWrap(True)
        self.content_layout.addWidget(eyebrow)
        self.content_layout.addWidget(title)
        self.content_layout.addWidget(subtitle)

        self.hero_card = QFrame()
        self.hero_card.setObjectName("HomeHeroCard")
        self.hero_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.hero_layout = QHBoxLayout(self.hero_card)
        self.hero_layout.setContentsMargins(28, 28, 28, 28)
        self.hero_layout.setSpacing(24)

        self.hero_left = QVBoxLayout()
        self.hero_left.setSpacing(14)
        badge = QLabel("QUICK RECEIPT")
        badge.setObjectName("HomeBadge")
        hero_heading = QLabel("Add a receipt")
        hero_heading.setObjectName("HomeHeroTitle")
        hero_body = QLabel(
            "Record a transaction immediately with guided product and pricing selection."
        )
        hero_body.setObjectName("HomeHeroBody")
        hero_body.setWordWrap(True)
        hero_button = QPushButton("Add receipt")
        hero_button.setObjectName("PrimaryButton")
        hero_button.clicked.connect(
            lambda _checked=False: self.quick_receipt_requested.emit()
        )
        hero_button.setMinimumWidth(190)

        self.hero_left.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.hero_left.addWidget(hero_heading)
        self.hero_left.addWidget(hero_body)
        self.hero_left.addSpacing(8)
        self.hero_left.addWidget(hero_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.hero_left.addStretch()

        self.hero_illustration = QFrame()
        self.hero_illustration.setObjectName("HomeIllustrationPanel")
        self.hero_illustration.setMinimumWidth(310)
        self.hero_illustration_layout = QVBoxLayout(self.hero_illustration)
        self.hero_illustration_layout.setContentsMargins(18, 16, 18, 16)
        self.hero_illustration_layout.setSpacing(0)

        self.illustration_art = ArtworkLabel(
            HOME_ILLUSTRATION_PATH, self.hero_illustration
        )
        self.illustration_art.setObjectName("HomeIllustrationArt")
        self.illustration_art.setMinimumSize(280, 165)
        self.hero_illustration_layout.addWidget(self.illustration_art, 1)

        self.hero_layout.addLayout(self.hero_left, 3)
        self.hero_layout.addWidget(self.hero_illustration, 2)
        self.content_layout.addWidget(self.hero_card)

        self.feature_row = QHBoxLayout()
        self.feature_row.setSpacing(18)
        self.feature_row.addWidget(
            self._action_card(
                "Search",
                "Browse transactions",
                "Search across receipt number, member, event number, amount, date and notes.",
                "Browse",
                self.browse_requested.emit,
                accent="cyan",
                icon_name="browse",
            )
        )
        self.feature_row.addWidget(
            self._action_card(
                "Desktop",
                "Desktop tab",
                "Keep a small draggable receipt-entry panel open while you work.",
                "Open panel",
                self.desktop_requested.emit,
                accent="amethyst",
                icon_name="desktop",
            )
        )
        self.feature_row.addWidget(
            self._action_card(
                "Manage",
                "Settings",
                "Manage app behaviour, desktop panel options and receipt fields.",
                "Open settings",
                self.settings_requested.emit,
                accent="coral",
                icon_name="settings",
            )
        )
        self.content_layout.addLayout(self.feature_row)

        self.footer = QFrame()
        self.footer.setObjectName("HomeFooter")
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(0, 14, 0, 0)
        self.footer_layout.setSpacing(14)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("HomeFooterStat")
        footer_note = QLabel("All data is stored securely on your device.")
        footer_note.setObjectName("HomeFooterNote")
        footer_note.setWordWrap(True)
        self.footer_layout.addWidget(self.summary_label)
        self.footer_layout.addWidget(footer_note)
        self.footer_layout.addStretch()
        self.content_layout.addWidget(self.footer)
        self.content_layout.addStretch()

        self._apply_vertical_mode(force=True)

    def _action_card(
        self,
        eyebrow: str,
        heading: str,
        body: str,
        button_text: str,
        slot,
        accent: str = "cyan",
        icon_name: str | None = None,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("HomeFeatureCard")
        card.setProperty("accent", accent)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)
        icon_label = QLabel("")
        icon_label.setObjectName("HomeFeatureIcon")
        icon_label.setProperty("accent", accent)
        icon_label.setFixedSize(32, 32)
        if icon_name:
            apply_label_icon(icon_label, icon_name, role=accent, size=16)
        eyebrow_label = QLabel(eyebrow.upper())
        eyebrow_label.setObjectName("HomeFeatureEyebrow")
        top_row.addWidget(icon_label)
        top_row.addWidget(eyebrow_label)
        top_row.addStretch()

        heading_label = QLabel(heading)
        heading_label.setObjectName("HomeFeatureTitle")
        body_label = QLabel(body)
        body_label.setObjectName("HomeFeatureBody")
        body_label.setWordWrap(True)
        button = QPushButton(button_text)
        button.setObjectName("SecondaryButton")
        button.clicked.connect(lambda _checked=False, callback=slot: callback())

        card_layout.addLayout(top_row)
        card_layout.addWidget(heading_label)
        card_layout.addWidget(body_label)
        card_layout.addStretch()
        card_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)

        self._feature_cards.append(card)
        self._feature_layouts.append(card_layout)
        return card

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_vertical_mode()

    def _apply_vertical_mode(self, *, force: bool = False) -> None:
        """Tighten vertical rhythm before scrolling becomes necessary."""
        viewport_height = (
            self.scroll_area.viewport().height()
            if hasattr(self, "scroll_area")
            else self.height()
        )

        if viewport_height < self.DENSE_HEIGHT:
            mode = "dense"
        elif viewport_height < self.COMPACT_HEIGHT:
            mode = "compact"
        else:
            mode = "regular"

        if not force and mode == self._vertical_mode:
            return
        self._vertical_mode = mode
        self.setProperty("verticalMode", mode)

        if mode == "dense":
            page_margins = (32, 20, 32, 18)
            page_spacing = 12
            hero_margins = (22, 18, 22, 18)
            hero_spacing = 18
            hero_left_spacing = 8
            hero_min_height = 205
            illustration_min = (220, 118)
            feature_min_height = 172
            feature_margins = (18, 16, 18, 16)
            feature_spacing = 8
            footer_top = 9
            feature_row_spacing = 14
        elif mode == "compact":
            page_margins = (36, 24, 36, 20)
            page_spacing = 14
            hero_margins = (24, 20, 24, 20)
            hero_spacing = 20
            hero_left_spacing = 10
            hero_min_height = 225
            illustration_min = (245, 135)
            feature_min_height = 188
            feature_margins = (20, 18, 20, 18)
            feature_spacing = 10
            footer_top = 10
            feature_row_spacing = 16
        else:
            page_margins = (38, 34, 38, 28)
            page_spacing = 20
            hero_margins = (28, 28, 28, 28)
            hero_spacing = 24
            hero_left_spacing = 14
            hero_min_height = 250
            illustration_min = (280, 165)
            feature_min_height = 205
            feature_margins = (24, 22, 24, 22)
            feature_spacing = 12
            footer_top = 14
            feature_row_spacing = 18

        self.content_layout.setContentsMargins(*page_margins)
        self.content_layout.setSpacing(page_spacing)
        self.hero_layout.setContentsMargins(*hero_margins)
        self.hero_layout.setSpacing(hero_spacing)
        self.hero_left.setSpacing(hero_left_spacing)
        self.hero_card.setMinimumHeight(hero_min_height)
        self.illustration_art.setMinimumSize(*illustration_min)
        self.feature_row.setSpacing(feature_row_spacing)
        self.footer_layout.setContentsMargins(0, footer_top, 0, 0)

        for card, card_layout in zip(self._feature_cards, self._feature_layouts):
            card.setMinimumHeight(feature_min_height)
            card_layout.setContentsMargins(*feature_margins)
            card_layout.setSpacing(feature_spacing)

        # Re-evaluate QSS selectors if a later style pass chooses to use the
        # verticalMode property as a responsive styling hook.
        self.style().unpolish(self)
        self.style().polish(self)
        self.updateGeometry()

    def set_receipt_count(self, count: int) -> None:
        self.summary_label.setText(f"Current database: {int(count):,} receipt(s).")
