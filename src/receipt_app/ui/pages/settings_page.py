from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...config import (
    AppSettings,
    CATALOG_EXPANDABLE_CATEGORIES,
    DEFAULT_TRANSACTION_CATALOG,
    FieldDefinition,
    PAYMENT_TYPE_OPTIONS,
    SettingsStore,
    TRANSACTION_CATEGORY_OPTIONS,
    clone_catalog,
    normalise_surcharge_rates,
)
from ...database import ReceiptDatabase
from ..widgets.inputs import CenteredCheckBox
from ..widgets.receipt_entry_form import surcharge_totals
from ..icons import apply_button_icon, apply_label_icon


class SettingsPage(QWidget):
    """ReceiptFlow settings screen and its page-local editing behaviour."""

    settings_saved = Signal()

    def __init__(
        self,
        settings: AppSettings,
        store: SettingsStore,
        db: ReceiptDatabase,
        parent: QWidget | None = None,
        *,
        current_sort_provider: Callable[[], str] | None = None,
    ):
        super().__init__(parent)
        self.settings = settings
        self.store = store
        self.db = db
        self.current_sort_provider = current_sort_provider
        self.catalog_draft = clone_catalog(self.settings.catalog)
        self._catalog_current_category = ""

        self.setObjectName("SettingsPage")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("SettingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(38, 34, 38, 34)
        layout.setSpacing(18)

        # Page heading ------------------------------------------------------
        eyebrow = QLabel("SETTINGS")
        eyebrow.setObjectName("SettingsEyebrow")
        title = QLabel("Settings")
        title.setObjectName("SettingsDisplayTitle")
        subtitle = QLabel(
            "Manage how ReceiptFlow behaves, stores data and handles receipts."
        )
        subtitle.setObjectName("SettingsLead")
        subtitle.setWordWrap(True)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)

        # Data & security ---------------------------------------------------
        data_card = QFrame()
        data_card.setObjectName("SettingsCard")
        data_layout = QVBoxLayout(data_card)
        data_layout.setContentsMargins(22, 18, 22, 20)
        data_layout.setSpacing(12)

        data_heading = QHBoxLayout()
        data_heading.setSpacing(10)
        data_icon = QLabel("")
        data_icon.setObjectName("SettingsAccentIcon")
        data_icon.setProperty("accent", "amethyst")
        apply_label_icon(data_icon, "security", role="amethyst", size=14)
        data_title_wrap = QVBoxLayout()
        data_title_wrap.setSpacing(3)
        data_title = QLabel("Data & security")
        data_title.setObjectName("SettingsCardTitle")
        data_help = QLabel(
            "ReceiptFlow manages the live database location so it cannot be accidentally moved into a sync folder or removable drive."
        )
        data_help.setObjectName("SettingsHelper")
        data_help.setWordWrap(True)
        data_title_wrap.addWidget(data_title)
        data_title_wrap.addWidget(data_help)
        data_heading.addWidget(data_icon, 0, Qt.AlignmentFlag.AlignTop)
        data_heading.addLayout(data_title_wrap, 1)
        data_layout.addLayout(data_heading)

        data_info = QHBoxLayout()
        data_info.setSpacing(22)

        db_group = QVBoxLayout()
        db_group.setSpacing(7)
        db_label = QLabel("Database location")
        db_label.setObjectName("SettingsMiniLabel")
        self.db_path_display = QLineEdit(str(self.settings.db_path))
        self.db_path_display.setReadOnly(True)
        self.db_path_display.setObjectName("ReadOnlySetting")
        self.db_path_display.setToolTip(str(self.settings.db_path))
        db_group.addWidget(db_label)
        db_group.addWidget(self.db_path_display)
        data_info.addLayout(db_group, 3)

        divider = QFrame()
        divider.setObjectName("SettingsVerticalDivider")
        divider.setFrameShape(QFrame.Shape.VLine)
        data_info.addWidget(divider)

        security_group = QVBoxLayout()
        security_group.setSpacing(7)
        security_label = QLabel("Encryption")
        security_label.setObjectName("SettingsMiniLabel")
        self.database_security_label = QLabel(
            f"SQLCipher {self.db.cipher_version()} · encryption key stored in the OS credential store"
        )
        self.database_security_label.setObjectName("SecurityStatus")
        self.database_security_label.setWordWrap(True)
        security_group.addWidget(security_label)
        security_group.addWidget(self.database_security_label)
        data_info.addLayout(security_group, 2)

        data_layout.addLayout(data_info)
        layout.addWidget(data_card)

        # App behaviour + desktop panel ------------------------------------
        cards_row = QHBoxLayout()
        cards_row.setSpacing(18)

        behaviour_card = QFrame()
        behaviour_card.setObjectName("SettingsCard")
        behaviour_layout = QVBoxLayout(behaviour_card)
        behaviour_layout.setContentsMargins(22, 18, 22, 20)
        behaviour_layout.setSpacing(10)

        behaviour_head = QHBoxLayout()
        behaviour_head.setSpacing(10)
        behaviour_icon = QLabel("")
        behaviour_icon.setObjectName("SettingsAccentIcon")
        behaviour_icon.setProperty("accent", "cyan")
        apply_label_icon(behaviour_icon, "behaviour", role="cyan", size=14)
        behaviour_title_wrap = QVBoxLayout()
        behaviour_title_wrap.setSpacing(3)
        behaviour_title = QLabel("App behaviour")
        behaviour_title.setObjectName("SettingsCardTitle")
        behaviour_help = QLabel(
            "Choose how ReceiptFlow behaves when it starts and while it is running."
        )
        behaviour_help.setObjectName("SettingsHelper")
        behaviour_help.setWordWrap(True)
        behaviour_title_wrap.addWidget(behaviour_title)
        behaviour_title_wrap.addWidget(behaviour_help)
        behaviour_head.addWidget(behaviour_icon, 0, Qt.AlignmentFlag.AlignTop)
        behaviour_head.addLayout(behaviour_title_wrap, 1)
        behaviour_layout.addLayout(behaviour_head)
        behaviour_layout.addSpacing(3)

        self.tray_checkbox = QCheckBox("Show menu bar / tray quick access")
        self.tray_checkbox.setChecked(self.settings.enable_tray)
        self.start_minimised_checkbox = QCheckBox("Start minimised")
        self.start_minimised_checkbox.setChecked(self.settings.start_minimised)
        behaviour_layout.addWidget(self.tray_checkbox)
        behaviour_layout.addWidget(self.start_minimised_checkbox)
        behaviour_layout.addStretch()
        cards_row.addWidget(behaviour_card, 1)

        desktop_card = QFrame()
        desktop_card.setObjectName("SettingsCard")
        desktop_layout = QVBoxLayout(desktop_card)
        desktop_layout.setContentsMargins(22, 18, 22, 20)
        desktop_layout.setSpacing(10)

        desktop_head = QHBoxLayout()
        desktop_head.setSpacing(10)
        desktop_icon = QLabel("")
        desktop_icon.setObjectName("SettingsAccentIcon")
        desktop_icon.setProperty("accent", "amethyst")
        apply_label_icon(desktop_icon, "desktop", role="amethyst", size=14)
        desktop_title_wrap = QVBoxLayout()
        desktop_title_wrap.setSpacing(3)
        desktop_title = QLabel("Desktop receipt panel")
        desktop_title.setObjectName("SettingsCardTitle")
        desktop_help = QLabel(
            "Control whether the quick-entry panel opens automatically and how large it appears."
        )
        desktop_help.setObjectName("SettingsHelper")
        desktop_help.setWordWrap(True)
        desktop_title_wrap.addWidget(desktop_title)
        desktop_title_wrap.addWidget(desktop_help)
        desktop_head.addWidget(desktop_icon, 0, Qt.AlignmentFlag.AlignTop)
        desktop_head.addLayout(desktop_title_wrap, 1)
        desktop_layout.addLayout(desktop_head)
        desktop_layout.addSpacing(3)

        self.desktop_tab_launch_checkbox = QCheckBox("Show desktop tab on launch")
        self.desktop_tab_launch_checkbox.setChecked(
            self.settings.show_desktop_tab_on_launch
        )
        desktop_layout.addWidget(self.desktop_tab_launch_checkbox)

        size_row = QHBoxLayout()
        size_row.setSpacing(10)
        width_label = QLabel("Width")
        width_label.setObjectName("SettingsMiniLabel")
        self.desktop_width_spin = QSpinBox()
        self.desktop_width_spin.setObjectName("SettingsCompactSpin")
        self.desktop_width_spin.setRange(360, 900)
        self.desktop_width_spin.setSuffix(" px")
        self.desktop_width_spin.setValue(self.settings.desktop_tab_width)
        height_label = QLabel("Height")
        height_label.setObjectName("SettingsMiniLabel")
        self.desktop_height_spin = QSpinBox()
        self.desktop_height_spin.setObjectName("SettingsCompactSpin")
        self.desktop_height_spin.setRange(520, 1000)
        self.desktop_height_spin.setSuffix(" px")
        self.desktop_height_spin.setValue(self.settings.desktop_tab_height)
        size_row.addWidget(width_label)
        size_row.addWidget(self.desktop_width_spin)
        size_row.addSpacing(10)
        size_row.addWidget(height_label)
        size_row.addWidget(self.desktop_height_spin)
        size_row.addStretch()
        desktop_layout.addLayout(size_row)
        desktop_layout.addStretch()
        cards_row.addWidget(desktop_card, 1)

        layout.addLayout(cards_row)

        # Payment surcharges ------------------------------------------------
        surcharge_card = QFrame()
        surcharge_card.setObjectName("SettingsCard")
        surcharge_layout = QVBoxLayout(surcharge_card)
        surcharge_layout.setContentsMargins(22, 18, 22, 20)
        surcharge_layout.setSpacing(12)

        surcharge_head = QHBoxLayout()
        surcharge_head.setSpacing(10)
        surcharge_icon = QLabel("")
        surcharge_icon.setObjectName("SettingsAccentIcon")
        surcharge_icon.setProperty("accent", "coral")
        apply_label_icon(surcharge_icon, "payment", role="coral", size=14)
        surcharge_title_wrap = QVBoxLayout()
        surcharge_title_wrap.setSpacing(3)
        surcharge_title = QLabel("Payment surcharges")
        surcharge_title.setObjectName("SettingsCardTitle")
        surcharge_help = QLabel(
            "Set a separate surcharge percentage for each payment method. Use 0.00% when a payment type should have no surcharge."
        )
        surcharge_help.setObjectName("SettingsHelper")
        surcharge_help.setWordWrap(True)
        surcharge_title_wrap.addWidget(surcharge_title)
        surcharge_title_wrap.addWidget(surcharge_help)
        surcharge_head.addWidget(surcharge_icon, 0, Qt.AlignmentFlag.AlignTop)
        surcharge_head.addLayout(surcharge_title_wrap, 1)
        surcharge_layout.addLayout(surcharge_head)

        rates_grid = QGridLayout()
        rates_grid.setHorizontalSpacing(14)
        rates_grid.setVerticalSpacing(8)

        self.surcharge_rate_spins: dict[str, QDoubleSpinBox] = {}
        for index, payment_type in enumerate(PAYMENT_TYPE_OPTIONS):
            rate_wrap = QFrame()
            rate_wrap.setObjectName("SettingsMiniCard")
            rate_layout = QHBoxLayout(rate_wrap)
            rate_layout.setContentsMargins(12, 8, 10, 8)
            rate_layout.setSpacing(10)

            payment_label = QLabel(payment_type)
            payment_label.setObjectName("PaymentSurchargeLabel")
            rate_spin = QDoubleSpinBox()
            rate_spin.setObjectName("SettingsRateSpin")
            rate_spin.setRange(0.0, 100.0)
            rate_spin.setDecimals(2)
            rate_spin.setSingleStep(0.1)
            rate_spin.setSuffix(" %")
            rate_spin.setMinimumWidth(105)
            rate_spin.setValue(
                float(self.settings.payment_surcharges.get(payment_type, 0.0))
            )
            rate_spin.valueChanged.connect(self._update_surcharge_settings_preview)
            self.surcharge_rate_spins[payment_type] = rate_spin

            rate_layout.addWidget(payment_label)
            rate_layout.addStretch()
            rate_layout.addWidget(rate_spin)

            rates_grid.addWidget(rate_wrap, 0, index)

        for column in range(len(PAYMENT_TYPE_OPTIONS)):
            rates_grid.setColumnStretch(column, 1)
        surcharge_layout.addLayout(rates_grid)

        self.surcharge_preview_label = QLabel("")
        self.surcharge_preview_label.setObjectName("SurchargePreview")
        self.surcharge_preview_label.setWordWrap(True)
        surcharge_layout.addWidget(self.surcharge_preview_label)
        self._update_surcharge_settings_preview()
        layout.addWidget(surcharge_card)

        # Products & pricing + receipt fields -------------------------------
        management_row = QHBoxLayout()
        management_row.setSpacing(18)

        catalog_card = QFrame()
        catalog_card.setObjectName("SettingsCard")
        catalog_layout = QVBoxLayout(catalog_card)
        catalog_layout.setContentsMargins(22, 18, 22, 20)
        catalog_layout.setSpacing(11)

        catalog_header = QHBoxLayout()
        catalog_header.setSpacing(12)
        catalog_heading = QHBoxLayout()
        catalog_heading.setSpacing(10)
        catalog_icon = QLabel("")
        catalog_icon.setObjectName("SettingsAccentIcon")
        catalog_icon.setProperty("accent", "amethyst")
        apply_label_icon(catalog_icon, "product", role="amethyst", size=14)
        catalog_title_wrap = QVBoxLayout()
        catalog_title_wrap.setSpacing(3)
        catalog_title = QLabel("Products & pricing")
        catalog_title.setObjectName("SettingsCardTitle")
        catalog_help = QLabel(
            "Manage products and current default prices used when creating new receipts."
        )
        catalog_help.setObjectName("SettingsHelper")
        catalog_help.setWordWrap(True)
        catalog_title_wrap.addWidget(catalog_title)
        catalog_title_wrap.addWidget(catalog_help)
        catalog_heading.addWidget(catalog_icon, 0, Qt.AlignmentFlag.AlignTop)
        catalog_heading.addLayout(catalog_title_wrap, 1)
        catalog_header.addLayout(catalog_heading, 1)

        category_wrap = QVBoxLayout()
        category_wrap.setSpacing(4)
        category_label = QLabel("Category")
        category_label.setObjectName("SettingsMiniLabel")
        self.catalog_category_combo = QComboBox()
        self.catalog_category_combo.setObjectName("SettingsCategoryCombo")
        self.catalog_category_combo.addItems(TRANSACTION_CATEGORY_OPTIONS)
        self.catalog_category_combo.setMinimumWidth(170)
        category_wrap.addWidget(category_label)
        category_wrap.addWidget(self.catalog_category_combo)
        catalog_header.addLayout(category_wrap)
        catalog_layout.addLayout(catalog_header)

        self.catalog_table = QTableWidget()
        self.catalog_table.setObjectName("ProductCatalogTable")
        self.catalog_table.setColumnCount(2)
        self.catalog_table.setHorizontalHeaderLabels(["Product / option", "Price"])
        self.catalog_table.horizontalHeader().setObjectName("SettingsCatalogHeader")
        self.catalog_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.catalog_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.catalog_table.verticalHeader().setVisible(False)
        self.catalog_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.catalog_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.catalog_table.setMinimumHeight(205)
        self.catalog_table.setMaximumHeight(280)
        catalog_layout.addWidget(self.catalog_table)

        self.catalog_note = QLabel("")
        self.catalog_note.setObjectName("SettingsHelper")
        self.catalog_note.setWordWrap(True)
        catalog_layout.addWidget(self.catalog_note)

        catalog_buttons = QHBoxLayout()
        catalog_buttons.setSpacing(8)
        self.add_catalog_product_btn = QPushButton("+  Add product")
        self.add_catalog_product_btn.setObjectName("SettingsAddButton")
        self.add_catalog_product_btn.clicked.connect(self.add_catalog_product)
        apply_button_icon(self.add_catalog_product_btn, "add", role="cyan", size=14)
        self.remove_catalog_product_btn = QPushButton("Remove selected")
        self.remove_catalog_product_btn.setObjectName("SettingsDangerButton")
        self.remove_catalog_product_btn.clicked.connect(self.remove_catalog_product)
        apply_button_icon(self.remove_catalog_product_btn, "trash", role="coral", size=14)
        catalog_buttons.addWidget(self.add_catalog_product_btn)
        catalog_buttons.addWidget(self.remove_catalog_product_btn)
        catalog_buttons.addStretch()
        catalog_layout.addLayout(catalog_buttons)

        self.catalog_category_combo.currentTextChanged.connect(
            self._catalog_category_changed
        )
        self._catalog_category_changed(self.catalog_category_combo.currentText())
        management_row.addWidget(catalog_card, 5)

        fields_card = QFrame()
        fields_card.setObjectName("SettingsCard")
        fields_layout = QVBoxLayout(fields_card)
        fields_layout.setContentsMargins(22, 18, 22, 20)
        fields_layout.setSpacing(11)

        fields_heading = QHBoxLayout()
        fields_heading.setSpacing(10)
        fields_icon = QLabel("")
        fields_icon.setObjectName("SettingsAccentIcon")
        fields_icon.setProperty("accent", "cyan")
        apply_label_icon(fields_icon, "fields", role="cyan", size=14)
        fields_title_wrap = QVBoxLayout()
        fields_title_wrap.setSpacing(3)
        fields_title = QLabel("Receipt fields")
        fields_title.setObjectName("SettingsCardTitle")
        fields_help = QLabel(
            "Choose which optional fields appear in quick entry and Browse, or add your own custom fields."
        )
        fields_help.setObjectName("SettingsHelper")
        fields_help.setWordWrap(True)
        fields_title_wrap.addWidget(fields_title)
        fields_title_wrap.addWidget(fields_help)
        fields_heading.addWidget(fields_icon, 0, Qt.AlignmentFlag.AlignTop)
        fields_heading.addLayout(fields_title_wrap, 1)
        fields_layout.addLayout(fields_heading)

        self.fields_table = QTableWidget()
        self.fields_table.setObjectName("SettingsFieldsTable")
        self.fields_table.setColumnCount(5)
        self.fields_table.setHorizontalHeaderLabels(
            ["Field", "Type", "Required", "Quick entry", "Browse"]
        )
        self.fields_table.horizontalHeader().setObjectName("SettingsFieldsHeader")
        self.fields_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.fields_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        for col in (2, 3, 4):
            self.fields_table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents
            )
        self.fields_table.verticalHeader().setVisible(False)
        self.fields_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fields_table.setAlternatingRowColors(False)
        self.fields_table.setMinimumHeight(330)
        self.fields_table.setMaximumHeight(430)
        fields_layout.addWidget(self.fields_table)

        field_buttons = QHBoxLayout()
        field_buttons.setSpacing(8)
        add_field_btn = QPushButton("+  Add custom field")
        add_field_btn.setObjectName("SettingsAddButton")
        add_field_btn.clicked.connect(self.add_field_row)
        apply_button_icon(add_field_btn, "add", role="cyan", size=14)
        remove_field_btn = QPushButton("Remove selected custom field")
        remove_field_btn.setObjectName("SettingsDangerButton")
        remove_field_btn.clicked.connect(self.remove_field_row)
        apply_button_icon(remove_field_btn, "trash", role="coral", size=14)
        field_buttons.addWidget(add_field_btn)
        field_buttons.addWidget(remove_field_btn)
        field_buttons.addStretch()
        fields_layout.addLayout(field_buttons)
        management_row.addWidget(fields_card, 7)

        layout.addLayout(management_row)

        # Save footer -------------------------------------------------------
        footer = QFrame()
        footer.setObjectName("SettingsFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 16, 0, 0)
        footer_layout.addStretch()
        save_btn = QPushButton("Save settings")
        save_btn.setObjectName("SettingsSaveButton")
        save_btn.setMinimumWidth(190)
        save_btn.clicked.connect(self.save_settings_from_ui)
        footer_layout.addWidget(save_btn)
        layout.addWidget(footer)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.populate_fields_table()

    def _update_surcharge_settings_preview(self, *_args: object) -> None:
        rates = normalise_surcharge_rates(
            {
                payment_type: spin.value()
                for payment_type, spin in self.surcharge_rate_spins.items()
            }
        )

        examples: list[str] = []
        for payment_type in PAYMENT_TYPE_OPTIONS:
            percentage = rates.get(payment_type, 0.0)
            total, _surcharge = surcharge_totals(20.0, percentage)
            examples.append(f"{payment_type}: {percentage:.2f}% → ${total:,.2f}")

        self.surcharge_preview_label.setText(
            "Example on a $20.00 base amount: " + "   |   ".join(examples)
        )

    def _save_catalog_table_to_draft(self) -> None:
        """Capture the prices currently visible in the catalogue table."""
        category = str(self._catalog_current_category or "").strip()
        if not category:
            return

        products: dict[str, float] = {}
        for row in range(self.catalog_table.rowCount()):
            item = self.catalog_table.item(row, 0)
            if item is None:
                continue
            product = item.text().strip()
            if not product:
                continue
            price_widget = self.catalog_table.cellWidget(row, 1)
            price = (
                float(price_widget.value())
                if isinstance(price_widget, QDoubleSpinBox)
                else 0.0
            )
            products[product] = max(0.0, price)

        self.catalog_draft[category] = products

    def _catalog_category_changed(self, category: str) -> None:
        if self._catalog_current_category:
            self._save_catalog_table_to_draft()

        category = str(category or "").strip()
        self._catalog_current_category = category
        self._populate_catalog_table(category)

    def _populate_catalog_table(self, category: str) -> None:
        category = str(category or "").strip()
        products = self.catalog_draft.get(category, {})
        self.catalog_table.setRowCount(len(products))

        default_products = DEFAULT_TRANSACTION_CATALOG.get(category, {})
        for row, (product, price) in enumerate(products.items()):
            name_item = QTableWidgetItem(product)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if product in default_products:
                name_item.setToolTip(
                    "Built-in ReceiptFlow option. Its price can be changed, but the option itself is protected."
                )
            else:
                name_item.setToolTip(
                    "Custom product. Remove and re-add it if you need to rename it."
                )
            self.catalog_table.setItem(row, 0, name_item)

            price_spin = QDoubleSpinBox()
            price_spin.setDecimals(2)
            price_spin.setRange(0.0, 999999.99)
            price_spin.setPrefix("$")
            price_spin.setSingleStep(1.0)
            price_spin.setValue(float(price or 0))
            price_spin.setMinimumWidth(130)
            self.catalog_table.setCellWidget(row, 1, price_spin)
            self.catalog_table.setRowHeight(row, 46)

        expandable = category in CATALOG_EXPANDABLE_CATEGORIES
        self.add_catalog_product_btn.setEnabled(expandable)
        self.remove_catalog_product_btn.setEnabled(expandable and bool(products))

        if category == "Function":
            self.catalog_note.setText(
                "Function receipts use an Event number and a manually entered amount, so they do not use preset products."
            )
        elif expandable:
            self.catalog_note.setText(
                "You can add products to this category. Built-in options are protected, while custom products can be removed."
            )
        else:
            self.catalog_note.setText(
                "This is a fixed ReceiptFlow category. You can change its current price, but its built-in product cannot be removed."
            )

    def add_catalog_product(self) -> None:
        category = self.catalog_category_combo.currentText().strip()
        if category not in CATALOG_EXPANDABLE_CATEGORIES:
            QMessageBox.information(
                self,
                "Fixed category",
                "This category has a fixed ReceiptFlow workflow and does not accept additional products.",
            )
            return

        self._save_catalog_table_to_draft()
        existing = self.catalog_draft.get(category, {})

        name, ok = QInputDialog.getText(
            self,
            "Add product",
            f"Product / option name for {category}:",
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Product name required", "Enter a product name.")
            return
        if any(existing_name.lower() == name.lower() for existing_name in existing):
            QMessageBox.warning(
                self,
                "Product already exists",
                f"{name} already exists under {category}.",
            )
            return

        price, ok = QInputDialog.getDouble(
            self,
            "Product price",
            f"Current price for {name}:",
            0.0,
            0.0,
            999999.99,
            2,
        )
        if not ok:
            return

        self.catalog_draft.setdefault(category, {})[name] = float(price)
        self._populate_catalog_table(category)

        for row in range(self.catalog_table.rowCount()):
            item = self.catalog_table.item(row, 0)
            if item is not None and item.text() == name:
                self.catalog_table.selectRow(row)
                self.catalog_table.scrollToItem(item)
                break

    def remove_catalog_product(self) -> None:
        category = self.catalog_category_combo.currentText().strip()
        row = self.catalog_table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Select a product",
                "Select the custom product you want to remove first.",
            )
            return

        item = self.catalog_table.item(row, 0)
        if item is None:
            return
        product = item.text().strip()
        if not product:
            return

        if product in DEFAULT_TRANSACTION_CATALOG.get(category, {}):
            QMessageBox.information(
                self,
                "Built-in product",
                "Built-in ReceiptFlow products cannot be removed. You can change the price instead.",
            )
            return

        self._save_catalog_table_to_draft()
        confirm = QMessageBox.question(
            self,
            "Remove product",
            f"Remove {product} from {category}? Existing receipts will not be changed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.catalog_draft.get(category, {}).pop(product, None)
        self._populate_catalog_table(category)

    def _field_key_for_row(self, row: int) -> str:
        item = self.fields_table.item(row, 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _set_field_row(
        self,
        row: int,
        field_def: FieldDefinition,
        *,
        is_new: bool = False,
    ) -> None:
        built_in_keys = {
            "receipt_no",
            "transaction_date",
            "receipt_category",
            "description",
            "quantity",
            "event_number",
            "name",
            "amount",
            "payment_type",
            "member_no",
            "notes",
        }
        required_locked = {
            "receipt_no",
            "transaction_date",
            "receipt_category",
            "description",
            "amount",
            "payment_type",
        }
        quick_locked = {
            "receipt_no",
            "transaction_date",
            "receipt_category",
            "description",
            "quantity",
            "event_number",
            "amount",
            "payment_type",
        }
        is_built_in = field_def.key in built_in_keys

        label_item = QTableWidgetItem(field_def.label)
        label_item.setData(Qt.ItemDataRole.UserRole, field_def.key)
        if is_built_in:
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            label_item.setToolTip("Built-in ReceiptFlow field")
        elif is_new:
            label_item.setToolTip(
                "Rename this field to something meaningful before saving"
            )
        self.fields_table.setItem(row, 0, label_item)

        if is_built_in:
            type_item = QTableWidgetItem(field_def.field_type.title())
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fields_table.setItem(row, 1, type_item)
        else:
            type_combo = QComboBox()
            type_combo.addItems(
                ["text", "number", "currency", "date", "textarea", "dropdown"]
            )
            type_combo.setCurrentText(field_def.field_type)
            self.fields_table.setCellWidget(row, 1, type_combo)

        required = CenteredCheckBox(field_def.required)
        if field_def.key in required_locked or field_def.key in {
            "event_number",
            "quantity",
        }:
            required.checkbox.setEnabled(False)
            if field_def.key == "event_number":
                required.checkbox.setToolTip(
                    "Required automatically for Function receipts only"
                )
            elif field_def.key == "quantity":
                required.checkbox.setToolTip(
                    "Required automatically for Ticketed Event receipts only"
                )
        self.fields_table.setCellWidget(row, 2, required)

        quick = CenteredCheckBox(field_def.quick_entry)
        if field_def.key in quick_locked:
            quick.checkbox.setChecked(True)
            quick.checkbox.setEnabled(False)
            quick.checkbox.setToolTip(
                "Required for the guided receipt-entry workflow"
            )
        self.fields_table.setCellWidget(row, 3, quick)

        browse = CenteredCheckBox(field_def.browse_column)
        self.fields_table.setCellWidget(row, 4, browse)
        self.fields_table.setRowHeight(row, 46)

    def populate_fields_table(self) -> None:
        self.fields_table.setRowCount(len(self.settings.fields))
        for row, field_def in enumerate(self.settings.fields):
            self._set_field_row(row, field_def)

    def add_field_row(self) -> None:
        existing = {
            self._field_key_for_row(row)
            for row in range(self.fields_table.rowCount())
        }
        base = "custom_field"
        key = base
        counter = 2
        while key in existing:
            key = f"{base}_{counter}"
            counter += 1

        row = self.fields_table.rowCount()
        self.fields_table.insertRow(row)
        self._set_field_row(
            row,
            FieldDefinition(key, "New custom field", "text", False, True, True, []),
            is_new=True,
        )
        self.fields_table.selectRow(row)
        self.fields_table.scrollToItem(self.fields_table.item(row, 0))
        self.fields_table.editItem(self.fields_table.item(row, 0))

    def remove_field_row(self) -> None:
        row = self.fields_table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Select a field",
                "Select the custom field you want to remove first.",
            )
            return

        built_in_keys = {
            "receipt_no",
            "transaction_date",
            "receipt_category",
            "description",
            "quantity",
            "event_number",
            "name",
            "amount",
            "payment_type",
            "member_no",
            "notes",
        }
        key = self._field_key_for_row(row)
        if key in built_in_keys:
            QMessageBox.information(
                self,
                "Built-in field",
                "Built-in receipt fields cannot be removed. You can change whether optional fields appear in Quick entry or Browse instead.",
            )
            return
        self.fields_table.removeRow(row)

    def save_settings_from_ui(self) -> None:
        fields: list[FieldDefinition] = []
        seen: set[str] = set()
        built_in_keys = {
            "receipt_no",
            "transaction_date",
            "receipt_category",
            "description",
            "quantity",
            "event_number",
            "name",
            "amount",
            "payment_type",
            "member_no",
            "notes",
        }
        required_locked = {
            "receipt_no",
            "transaction_date",
            "receipt_category",
            "description",
            "amount",
            "payment_type",
        }
        quick_locked = {
            "receipt_no",
            "transaction_date",
            "receipt_category",
            "description",
            "quantity",
            "event_number",
            "amount",
            "payment_type",
        }

        for row in range(self.fields_table.rowCount()):
            key = self._field_key_for_row(row)
            label_item = self.fields_table.item(row, 0)
            label = (label_item.text() if label_item else "").strip()
            if not key or not label:
                QMessageBox.warning(
                    self, "Invalid field", "Each receipt field needs a name."
                )
                return
            if key in seen:
                QMessageBox.warning(
                    self,
                    "Duplicate field",
                    f"ReceiptFlow found a duplicate internal field: {key}",
                )
                return
            seen.add(key)

            if key in built_in_keys:
                current = next(
                    (field for field in self.settings.fields if field.key == key),
                    None,
                )
                if current is None:
                    continue
                field_type = current.field_type
                options = list(current.options)
            else:
                type_combo = self.fields_table.cellWidget(row, 1)
                field_type = (
                    type_combo.currentText()
                    if isinstance(type_combo, QComboBox)
                    else "text"
                )
                options = []

            required_widget = self.fields_table.cellWidget(row, 2)
            quick_widget = self.fields_table.cellWidget(row, 3)
            browse_widget = self.fields_table.cellWidget(row, 4)
            required = (
                required_widget.isChecked()
                if hasattr(required_widget, "isChecked")
                else False
            )
            quick = (
                quick_widget.isChecked()
                if hasattr(quick_widget, "isChecked")
                else True
            )
            browse = (
                browse_widget.isChecked()
                if hasattr(browse_widget, "isChecked")
                else True
            )

            if key in required_locked:
                required = True
            elif key in {"event_number", "quantity"}:
                required = False
            if key in quick_locked:
                quick = True

            if key == "receipt_category":
                label = "Category"
                field_type = "dropdown"
                options = list(TRANSACTION_CATEGORY_OPTIONS)
            elif key == "description":
                label = "Product / term"
                field_type = "dropdown"
                options = []
            elif key == "quantity":
                label = "Quantity"
                field_type = "number"
                options = []
            elif key == "event_number":
                label = "Event number"
                field_type = "text"
                options = []

            fields.append(
                FieldDefinition(
                    key,
                    label,
                    field_type,
                    required,
                    quick,
                    browse,
                    options,
                )
            )

        self._save_catalog_table_to_draft()
        self.settings.catalog = clone_catalog(self.catalog_draft)
        self.settings.payment_surcharges = normalise_surcharge_rates(
            {
                payment_type: spin.value()
                for payment_type, spin in self.surcharge_rate_spins.items()
            }
        )
        self.settings.enable_tray = self.tray_checkbox.isChecked()
        self.settings.start_minimised = self.start_minimised_checkbox.isChecked()
        self.settings.show_desktop_tab_on_launch = (
            self.desktop_tab_launch_checkbox.isChecked()
        )
        self.settings.desktop_tab_width = self.desktop_width_spin.value()
        self.settings.desktop_tab_height = self.desktop_height_spin.value()
        if self.current_sort_provider is not None:
            self.settings.default_sort = self.current_sort_provider()
        self.settings.fields = fields
        self.store.save(self.settings)

        self.settings_saved.emit()
        QMessageBox.information(
            self,
            "Settings saved",
            "Your ReceiptFlow settings have been saved.",
        )
