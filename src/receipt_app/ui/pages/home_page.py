from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, QTimer, Signal
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
        self._total_receipts = 0

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

        # Operational summary ---------------------------------------------
        self.summary_card = QFrame()
        self.summary_card.setObjectName("HomeSummaryCard")
        self.summary_layout = QVBoxLayout(self.summary_card)
        self.summary_layout.setContentsMargins(20, 18, 20, 18)
        self.summary_layout.setSpacing(14)

        summary_header = QHBoxLayout()
        summary_header.setContentsMargins(0, 0, 0, 0)
        summary_header.setSpacing(12)

        summary_title = QLabel("TODAY'S ACTIVITY")
        summary_title.setObjectName("HomeSummaryEyebrow")
        self.summary_date_label = QLabel("")
        self.summary_date_label.setObjectName("HomeSummaryDate")
        self.summary_total_database_label = QLabel("")
        self.summary_total_database_label.setObjectName("HomeSummaryDatabaseTotal")

        summary_header.addWidget(summary_title)
        summary_header.addWidget(self.summary_date_label)
        summary_header.addStretch()
        summary_header.addWidget(self.summary_total_database_label)
        self.summary_layout.addLayout(summary_header)

        self.summary_metrics_row = QHBoxLayout()
        self.summary_metrics_row.setContentsMargins(0, 0, 0, 0)
        self.summary_metrics_row.setSpacing(12)

        self.today_metric, self.today_value_label, self.today_meta_label = (
            self._summary_metric(
                "RECEIPTS",
                "0 receipts · $0.00",
                "No receipts recorded today",
                accent="coral",
            )
        )
        self.payment_metric, self.payment_value_label, self.payment_meta_label = (
            self._summary_metric(
                "PAYMENTS",
                "No payments yet",
                "Today's payment mix",
                accent="cyan",
            )
        )
        self.backup_metric, self.backup_value_label, self.backup_meta_label = (
            self._summary_metric(
                "LAST BACKUP",
                "Checking…",
                "Automatic encrypted backup",
                accent="amethyst",
            )
        )

        self.summary_metrics_row.addWidget(self.today_metric, 1)
        self.summary_metrics_row.addWidget(self.payment_metric, 2)
        self.summary_metrics_row.addWidget(self.backup_metric, 1)
        self.summary_layout.addLayout(self.summary_metrics_row)

        self.content_layout.addWidget(self.summary_card)
        self.content_layout.addStretch()

        QTimer.singleShot(0, self.refresh_operational_summary)
        self.backup_age_timer = QTimer(self)
        self.backup_age_timer.setInterval(60 * 1000)
        self.backup_age_timer.timeout.connect(self._refresh_backup_status)
        self.backup_age_timer.start()

        self._apply_vertical_mode(force=True)

    def _summary_metric(
        self,
        heading: str,
        value: str,
        meta: str,
        *,
        accent: str,
    ) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setObjectName("HomeSummaryMetric")
        card.setProperty("accent", accent)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(4)

        heading_label = QLabel(heading)
        heading_label.setObjectName("HomeSummaryMetricLabel")
        heading_label.setProperty("accent", accent)

        value_label = QLabel(value)
        value_label.setObjectName("HomeSummaryMetricValue")
        value_label.setWordWrap(True)

        meta_label = QLabel(meta)
        meta_label.setObjectName("HomeSummaryMetricMeta")
        meta_label.setWordWrap(True)

        layout.addWidget(heading_label)
        layout.addWidget(value_label)
        layout.addWidget(meta_label)
        layout.addStretch()
        return card, value_label, meta_label

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
            summary_margins = (14, 12, 14, 12)
            summary_spacing = 8
            metric_margins = (12, 10, 12, 10)
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
            summary_margins = (16, 14, 16, 14)
            summary_spacing = 10
            metric_margins = (14, 11, 14, 11)
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
            summary_margins = (20, 18, 20, 18)
            summary_spacing = 14
            metric_margins = (16, 13, 16, 13)
            feature_row_spacing = 18

        self.content_layout.setContentsMargins(*page_margins)
        self.content_layout.setSpacing(page_spacing)
        self.hero_layout.setContentsMargins(*hero_margins)
        self.hero_layout.setSpacing(hero_spacing)
        self.hero_left.setSpacing(hero_left_spacing)
        self.hero_card.setMinimumHeight(hero_min_height)
        self.illustration_art.setMinimumSize(*illustration_min)
        self.feature_row.setSpacing(feature_row_spacing)
        self.summary_layout.setContentsMargins(*summary_margins)
        self.summary_layout.setSpacing(summary_spacing)

        for metric in (self.today_metric, self.payment_metric, self.backup_metric):
            metric_layout = metric.layout()
            if metric_layout is not None:
                metric_layout.setContentsMargins(*metric_margins)

        for card, card_layout in zip(self._feature_cards, self._feature_layouts):
            card.setMinimumHeight(feature_min_height)
            card_layout.setContentsMargins(*feature_margins)
            card_layout.setSpacing(feature_spacing)

        # Re-evaluate QSS selectors if a later style pass chooses to use the
        # verticalMode property as a responsive styling hook.
        self.style().unpolish(self)
        self.style().polish(self)
        self.updateGeometry()

    def _data_sources(self):
        """Return app-owned database and backup services when available."""
        owner = self.window()
        return getattr(owner, "db", None), getattr(owner, "backup_manager", None)

    @staticmethod
    def _money(value: float) -> str:
        return f"${float(value):,.2f}"

    @staticmethod
    def _backup_age_text(timestamp: datetime) -> str:
        seconds = max(0, int((datetime.now() - timestamp).total_seconds()))
        if seconds < 60:
            return "Just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min ago" if minutes == 1 else f"{minutes} mins ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hr ago" if hours == 1 else f"{hours} hrs ago"
        days = hours // 24
        return "Yesterday" if days == 1 else f"{days} days ago"

    def _refresh_backup_status(self) -> None:
        _db, backup_manager = self._data_sources()
        if backup_manager is None:
            self.backup_value_label.setText("Unavailable")
            return
        try:
            latest = backup_manager.latest_backup()
        except Exception:
            self.backup_value_label.setText("Unavailable")
            return
        if latest is None:
            self.backup_value_label.setText("No backup yet")
            return
        try:
            timestamp = datetime.fromtimestamp(latest.stat().st_mtime)
        except OSError:
            self.backup_value_label.setText("Unavailable")
            return
        self.backup_value_label.setText(self._backup_age_text(timestamp))

    def refresh_operational_summary(self) -> None:
        """Refresh today's receipt, payment and backup summary."""
        today = date.today()
        self.summary_date_label.setText(today.strftime("%A · %d %B %Y"))
        self.summary_total_database_label.setText(
            f"{self._total_receipts:,} receipt"
            f"{'s' if self._total_receipts != 1 else ''} in database"
        )

        db, _backup_manager = self._data_sources()
        if db is None:
            self.today_value_label.setText("Unavailable")
            self.payment_value_label.setText("Unavailable")
            self._refresh_backup_status()
            return

        try:
            rows = list(db.receipts_for_date(today.isoformat(), limit=10_000))
            if not rows:
                legacy_date = today.strftime("%d/%m/%Y")
                rows = list(db.receipts_for_date(legacy_date, limit=10_000))
        except Exception:
            self.today_value_label.setText("Unavailable")
            self.payment_value_label.setText("Unavailable")
            self._refresh_backup_status()
            return

        receipt_count = len(rows)
        total_amount = 0.0
        payment_totals: dict[str, float] = {}
        for row in rows:
            try:
                amount = float(row["amount"] or 0)
            except (TypeError, ValueError):
                amount = 0.0
            total_amount += amount
            payment_type = str(row["payment_type"] or "").strip() or "Other"
            payment_totals[payment_type] = payment_totals.get(payment_type, 0.0) + amount

        self.today_value_label.setText(
            f"{receipt_count:,} receipt{'s' if receipt_count != 1 else ''} · {self._money(total_amount)}"
        )
        self.today_meta_label.setText(
            "Recorded today" if receipt_count else "No receipts recorded today"
        )

        preferred_order = ("Eftpos", "Cash", "MOTO", "Direct Debit")
        payment_parts: list[str] = []
        consumed: set[str] = set()
        for payment_type in preferred_order:
            amount = payment_totals.get(payment_type, 0.0)
            if amount:
                payment_parts.append(f"{payment_type} {self._money(amount)}")
                consumed.add(payment_type)

        other_total = sum(
            amount for payment_type, amount in payment_totals.items()
            if payment_type not in consumed
        )
        if other_total:
            payment_parts.append(f"Other {self._money(other_total)}")

        self.payment_value_label.setText(
            " · ".join(payment_parts) if payment_parts else "No payments yet"
        )
        self.payment_meta_label.setText("Today's payment mix")
        self._refresh_backup_status()

    def set_receipt_count(self, count: int) -> None:
        self._total_receipts = max(0, int(count))
        self.refresh_operational_summary()
