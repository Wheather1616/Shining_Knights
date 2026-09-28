from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


from ..assets import ArtworkLabel, HOME_ILLUSTRATION_PATH
from ..icons import apply_label_icon


class HomePage(QWidget):
    """ReceiptFlow home dashboard.

    The page owns its presentation and emits navigation/action requests instead of
    reaching back into the main window directly.
    """

    quick_receipt_requested = Signal()
    browse_requested = Signal()
    desktop_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("HomePage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(38, 34, 38, 28)
        layout.setSpacing(20)

        eyebrow = QLabel("WELCOME TO")
        eyebrow.setObjectName("HomeEyebrow")
        title = QLabel("Receipt database")
        title.setObjectName("HomeDisplayTitle")
        subtitle = QLabel("Capture, search and manage club receipts from one place.")
        subtitle.setObjectName("HomeLead")
        subtitle.setWordWrap(True)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        hero_card = QFrame()
        hero_card.setObjectName("HomeHeroCard")
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(28, 28, 28, 28)
        hero_layout.setSpacing(24)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(14)
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
        hero_button.clicked.connect(lambda _checked=False: self.quick_receipt_requested.emit())
        hero_button.setMinimumWidth(190)

        hero_left.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        hero_left.addWidget(hero_heading)
        hero_left.addWidget(hero_body)
        hero_left.addSpacing(8)
        hero_left.addWidget(hero_button, 0, Qt.AlignmentFlag.AlignLeft)
        hero_left.addStretch()

        hero_illustration = QFrame()
        hero_illustration.setObjectName("HomeIllustrationPanel")
        hero_illustration.setMinimumWidth(310)
        hero_illustration_layout = QVBoxLayout(hero_illustration)
        hero_illustration_layout.setContentsMargins(18, 16, 18, 16)
        hero_illustration_layout.setSpacing(0)

        illustration_art = ArtworkLabel(HOME_ILLUSTRATION_PATH, hero_illustration)
        illustration_art.setObjectName("HomeIllustrationArt")
        illustration_art.setMinimumSize(280, 165)
        hero_illustration_layout.addWidget(illustration_art, 1)

        hero_layout.addLayout(hero_left, 3)
        hero_layout.addWidget(hero_illustration, 2)
        layout.addWidget(hero_card)

        feature_row = QHBoxLayout()
        feature_row.setSpacing(18)
        feature_row.addWidget(
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
        feature_row.addWidget(
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
        feature_row.addWidget(
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
        layout.addLayout(feature_row)

        footer = QFrame()
        footer.setObjectName("HomeFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 14, 0, 0)
        footer_layout.setSpacing(14)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("HomeFooterStat")
        footer_note = QLabel("All data is stored securely on your device.")
        footer_note.setObjectName("HomeFooterNote")
        footer_note.setWordWrap(True)
        footer_layout.addWidget(self.summary_label)
        footer_layout.addWidget(footer_note)
        footer_layout.addStretch()
        layout.addWidget(footer)
        layout.addStretch()

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
        card.setMinimumHeight(220)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

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

        layout.addLayout(top_row)
        layout.addWidget(heading_label)
        layout.addWidget(body_label)
        layout.addStretch()
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def set_receipt_count(self, count: int) -> None:
        self.summary_label.setText(f"Current database: {int(count):,} receipt(s).")
