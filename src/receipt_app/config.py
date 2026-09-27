from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .paths import (
    app_support_dir,
    default_db_path,
    legacy_settings_paths,
)

FieldType = Literal["text", "number", "currency", "date", "textarea", "dropdown"]
PAYMENT_TYPE_OPTIONS = ["Eftpos", "Cash", "MOTO", "Direct Debit"]
DEFAULT_PAYMENT_SURCHARGE_RATES: dict[str, float] = {
    payment_type: 0.0 for payment_type in PAYMENT_TYPE_OPTIONS
}

# These are defaults only. The live product catalogue is stored in AppSettings
# (settings.json) so authorised users can manage products/prices without changing code.
DEFAULT_TRANSACTION_CATALOG: dict[str, dict[str, float]] = {
    "New Member": {
        "1 year": 10.0,
        "3 years": 20.0,
        "5 years": 30.0,
    },
    "Renewal": {
        "1 year": 10.0,
        "3 years": 20.0,
        "5 years": 30.0,
    },
    "Ticketed Event": {
        "Melbourne Cup": 85.0,
    },
    "Replacement Card": {
        "Replacement Card": 3.0,
    },
    "Function": {},
    "Merch": {
        "Pack": 120.0,
        "T-shirt": 40.0,
        "Towel": 50.0,
        "Cap": 20.0,
        "Stubby holder": 10.0,
        "Beanie": 25.0,
        "Bag": 20.0,
    },
    "Poppy": {
        "Poppy": 1.0,
    },
}

# Categories remain controlled by ReceiptFlow because each category can have
# specialised workflow behaviour. Products/prices inside expandable categories
# are user configurable.
TRANSACTION_CATEGORY_OPTIONS = list(DEFAULT_TRANSACTION_CATALOG.keys())
CATALOG_EXPANDABLE_CATEGORIES = {
    "New Member",
    "Renewal",
    "Ticketed Event",
    "Merch",
}


def normalise_catalog(raw_catalog: Any = None) -> dict[str, dict[str, float]]:
    """Return a safe catalogue containing only established ReceiptFlow categories.

    Default products are retained (their prices may be overridden by settings).
    User-created products are retained only for categories whose workflows support
    expansion. This keeps category behaviour controlled by the application.
    """
    raw = raw_catalog if isinstance(raw_catalog, dict) else {}
    result: dict[str, dict[str, float]] = {}

    for category in TRANSACTION_CATEGORY_OPTIONS:
        defaults = DEFAULT_TRANSACTION_CATALOG[category]
        raw_products = raw.get(category, {})
        if not isinstance(raw_products, dict):
            raw_products = {}

        products: dict[str, float] = {}

        # Keep built-in products so workflow-critical choices cannot disappear.
        for product, default_price in defaults.items():
            value = raw_products.get(product, default_price)
            try:
                price = max(0.0, float(value))
            except (TypeError, ValueError):
                price = float(default_price)
            products[product] = price

        # Keep user-created products only where the established category workflow
        # supports arbitrary additional choices.
        if category in CATALOG_EXPANDABLE_CATEGORIES:
            for product, value in raw_products.items():
                product_name = str(product or "").strip()
                if not product_name or product_name in products:
                    continue
                try:
                    price = max(0.0, float(value))
                except (TypeError, ValueError):
                    continue
                products[product_name] = price

        result[category] = products

    return result


def clone_catalog(catalog: Any = None) -> dict[str, dict[str, float]]:
    """Return an independent, normalised copy of a ReceiptFlow catalogue."""
    if catalog is None:
        catalog = DEFAULT_TRANSACTION_CATALOG
    return normalise_catalog(catalog)


def product_options(
    category: str,
    catalog: dict[str, dict[str, float]] | None = None,
) -> list[str]:
    active_catalog = catalog if catalog is not None else DEFAULT_TRANSACTION_CATALOG
    products = active_catalog.get(str(category or "").strip(), {})
    return list(products.keys()) if isinstance(products, dict) else []


def product_price(
    category: str,
    product: str = "",
    catalog: dict[str, dict[str, float]] | None = None,
) -> float | None:
    active_catalog = catalog if catalog is not None else DEFAULT_TRANSACTION_CATALOG
    products = active_catalog.get(str(category or "").strip(), {})
    if not isinstance(products, dict) or not products:
        return None
    if product in products:
        try:
            return float(products[product])
        except (TypeError, ValueError):
            return None
    if len(products) == 1:
        try:
            return float(next(iter(products.values())))
        except (TypeError, ValueError):
            return None
    return None


def normalise_surcharge_percentage(value: Any, default: float = 0.0) -> float:
    """Return a safe percentage between 0 and 100."""
    try:
        percentage = float(value)
    except (TypeError, ValueError):
        percentage = float(default)
    return max(0.0, min(percentage, 100.0))


def normalise_surcharge_rates(
    raw_rates: Any = None,
    *,
    legacy_enabled: bool | None = None,
    legacy_percentage: Any = 1.0,
) -> dict[str, float]:
    """Return one safe surcharge percentage for every established payment type.

    ReceiptFlow previously had one optional non-cash surcharge. When an older
    settings file is loaded, an enabled legacy rate is migrated to Eftpos, MOTO
    and Direct Debit while Cash starts at 0%. From then on every payment type,
    including Cash, can be configured independently.
    """
    rates = dict(DEFAULT_PAYMENT_SURCHARGE_RATES)

    if isinstance(raw_rates, dict):
        by_name = {
            str(name or "").strip().casefold(): value
            for name, value in raw_rates.items()
            if str(name or "").strip()
        }
        for payment_type in PAYMENT_TYPE_OPTIONS:
            rates[payment_type] = normalise_surcharge_percentage(
                by_name.get(payment_type.casefold(), 0.0),
                0.0,
            )
        return rates

    if bool(legacy_enabled):
        legacy_rate = normalise_surcharge_percentage(legacy_percentage, 1.0)
        for payment_type in PAYMENT_TYPE_OPTIONS:
            if payment_type.casefold() != "cash":
                rates[payment_type] = legacy_rate

    return rates


def surcharge_percentage_for_payment(
    payment_type: str,
    rates: dict[str, float] | None,
) -> float:
    """Return the configured surcharge for a payment method, or 0% if unknown."""
    payment = str(payment_type or "").strip().casefold()
    if not payment:
        return 0.0

    active_rates = normalise_surcharge_rates(rates)
    for name, percentage in active_rates.items():
        if name.casefold() == payment:
            return normalise_surcharge_percentage(percentage, 0.0)
    return 0.0


def description_for_selection(category: str, product: str = "") -> str:
    category = str(category or "").strip()
    product = str(product or "").strip()
    if not category:
        return ""
    if category in {"Replacement Card", "Function", "Poppy"}:
        return category
    if not product:
        return ""
    return f"{category} - {product}"


def infer_category_from_description(description: str) -> str:
    text = str(description or "").strip()
    if not text:
        return ""

    lowered = text.lower()
    aliases = {
        "new member": "New Member",
        "renewal": "Renewal",
        "ticketed event": "Ticketed Event",
        "ticketed events": "Ticketed Event",
        "replacement card": "Replacement Card",
        "function": "Function",
        "merch": "Merch",
        "poppy": "Poppy",
        "poppies": "Poppy",
    }
    for prefix, category in aliases.items():
        if (
            lowered == prefix
            or lowered.startswith(prefix + " -")
            or lowered.startswith(prefix + ":")
            or (prefix == "merch" and lowered.startswith("merch "))
        ):
            return category
    return ""


def product_from_description(
    category: str,
    description: str,
    catalog: dict[str, dict[str, float]] | None = None,
) -> str:
    category = str(category or "").strip()
    text = str(description or "").strip()
    if not category or not text:
        return ""

    active_catalog = catalog if catalog is not None else DEFAULT_TRANSACTION_CATALOG

    if category in {"Replacement Card", "Function", "Poppy"}:
        return next(iter(active_catalog.get(category, {})), "")

    options = product_options(category, active_catalog)
    candidate = text
    prefixes = [f"{category} - ", f"{category}: "]
    matched_prefix = False
    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()):
            candidate = text[len(prefix):].strip()
            matched_prefix = True
            break

    if category == "Merch":
        legacy = {
            "merch pack": "Pack",
            "pack": "Pack",
            "t-shirt": "T-shirt",
            "tshirt": "T-shirt",
            "towel": "Towel",
            "cap": "Cap",
            "stuuby": "Stubby holder",
            "stubby": "Stubby holder",
            "stubby holder": "Stubby holder",
            "beanie": "Beanie",
            "bag": "Bag",
        }
        lowered_candidate = candidate.lower()
        if lowered_candidate in legacy and legacy[lowered_candidate] in options:
            return legacy[lowered_candidate]
        if text.lower() in legacy and legacy[text.lower()] in options:
            return legacy[text.lower()]

    for option in options:
        if candidate.lower() == option.lower():
            return option

    # Historical receipts may reference a custom product that has since been
    # removed from the current catalogue. Return the saved product name so Edit
    # can display it without re-adding it to today's catalogue.
    if matched_prefix and candidate:
        return candidate
    return ""


@dataclass
class FieldDefinition:
    key: str
    label: str
    field_type: FieldType = "text"
    required: bool = False
    quick_entry: bool = True
    browse_column: bool = True
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "field_type": self.field_type,
            "required": self.required,
            "quick_entry": self.quick_entry,
            "browse_column": self.browse_column,
            "options": self.options,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FieldDefinition":
        return FieldDefinition(
            key=str(data.get("key", "")).strip(),
            label=str(data.get("label", "")).strip(),
            field_type=data.get("field_type", "text"),
            required=bool(data.get("required", False)),
            quick_entry=bool(data.get("quick_entry", True)),
            browse_column=bool(data.get("browse_column", True)),
            options=[str(item).strip() for item in data.get("options", []) if str(item).strip()],
        )


CORE_FIELD_KEYS = {
    "receipt_no",
    "transaction_date",
    "name",
    "amount",
    "payment_type",
    "member_no",
    "notes",
}

DEFAULT_FIELDS = [
    FieldDefinition("receipt_no", "Receipt No", "text", True, True, True),
    FieldDefinition("transaction_date", "Date", "date", True, True, True),
    FieldDefinition("receipt_category", "Category", "dropdown", True, True, True, TRANSACTION_CATEGORY_OPTIONS),
    FieldDefinition("description", "Product / term", "dropdown", True, True, True, []),
    FieldDefinition("quantity", "Quantity", "number", False, True, False),
    FieldDefinition("event_number", "Event number", "text", False, True, False),
    FieldDefinition("name", "Name / Customer", "text", False, True, True),
    FieldDefinition("amount", "Amount", "currency", True, True, True),
    FieldDefinition("payment_type", "Payment Type", "dropdown", True, True, True, PAYMENT_TYPE_OPTIONS),
    FieldDefinition("member_no", "Member No", "text", False, True, True),
    FieldDefinition("notes", "Notes", "textarea", False, True, False),
]


@dataclass
class AppSettings:
    db_path: Path
    fields: list[FieldDefinition] = field(default_factory=lambda: list(DEFAULT_FIELDS))
    catalog: dict[str, dict[str, float]] = field(default_factory=clone_catalog)
    payment_surcharges: dict[str, float] = field(default_factory=normalise_surcharge_rates)
    enable_tray: bool = True
    start_minimised: bool = False
    show_desktop_tab_on_launch: bool = False
    desktop_tab_x: int | None = None
    desktop_tab_y: int | None = None
    desktop_tab_width: int = 430
    desktop_tab_height: int = 640
    default_sort: str = "Newest first"

    @staticmethod
    def default() -> "AppSettings":
        return AppSettings(
            db_path=default_db_path(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_path": str(self.db_path),
            "fields": [field_def.to_dict() for field_def in self.fields],
            "catalog": clone_catalog(self.catalog),
            "payment_surcharges": normalise_surcharge_rates(self.payment_surcharges),
            "enable_tray": self.enable_tray,
            "start_minimised": self.start_minimised,
            "show_desktop_tab_on_launch": self.show_desktop_tab_on_launch,
            "desktop_tab_x": self.desktop_tab_x,
            "desktop_tab_y": self.desktop_tab_y,
            "desktop_tab_width": self.desktop_tab_width,
            "desktop_tab_height": self.desktop_tab_height,
            "default_sort": self.default_sort,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AppSettings":
        default = AppSettings.default()
        saved_fields = [FieldDefinition.from_dict(item) for item in data.get("fields", [])]
        saved_fields = [field_def for field_def in saved_fields if field_def.key and field_def.label]

        if saved_fields:
            saved_by_key = {field_def.key: field_def for field_def in saved_fields}
            merged_fields = []

            workflow_keys = {"receipt_category", "description", "quantity", "event_number"}
            for default_field in DEFAULT_FIELDS:
                saved = saved_by_key.pop(default_field.key, None)
                if saved is None:
                    merged_fields.append(default_field)
                    continue

                if default_field.key in workflow_keys:
                    merged_fields.append(
                        FieldDefinition(
                            default_field.key,
                            default_field.label,
                            default_field.field_type,
                            default_field.required,
                            True,
                            saved.browse_column,
                            list(default_field.options),
                        )
                    )
                else:
                    merged_fields.append(saved)

            merged_fields.extend(saved_by_key.values())
            fields = merged_fields
        else:
            fields = list(DEFAULT_FIELDS)

        return AppSettings(
            db_path=Path(data.get("db_path") or default.db_path),
            fields=fields or list(DEFAULT_FIELDS),
            catalog=normalise_catalog(data.get("catalog")),
            payment_surcharges=normalise_surcharge_rates(
                data.get("payment_surcharges"),
                legacy_enabled=bool(data.get("surcharge_enabled", False)),
                legacy_percentage=data.get("surcharge_percentage", 1.0),
            ),
            enable_tray=bool(data.get("enable_tray", True)),
            start_minimised=bool(data.get("start_minimised", False)),
            show_desktop_tab_on_launch=bool(data.get("show_desktop_tab_on_launch", False)),
            desktop_tab_x=data.get("desktop_tab_x") if isinstance(data.get("desktop_tab_x"), int) else None,
            desktop_tab_y=data.get("desktop_tab_y") if isinstance(data.get("desktop_tab_y"), int) else None,
            desktop_tab_width=int(data.get("desktop_tab_width", default.desktop_tab_width) or default.desktop_tab_width),
            desktop_tab_height=int(data.get("desktop_tab_height", default.desktop_tab_height) or default.desktop_tab_height),
            default_sort=str(data.get("default_sort", default.default_sort)),
        )


class SettingsStore:
    def __init__(self, settings_path: Path | None = None):
        self.settings_path = settings_path or (app_support_dir() / "settings.json")
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        if not self.settings_path.exists():
            for legacy_path in legacy_settings_paths():
                if legacy_path.exists():
                    self.settings_path.write_bytes(
                        legacy_path.read_bytes()
                    )
                    break
        if not self.settings_path.exists():
            settings = AppSettings.default()
            self.save(settings)
            return settings
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            settings = AppSettings.from_dict(data)
            # Persist newly introduced settings so upgraded installations have a
            # complete configuration file without requiring a manual Save first.
            if any(
                key not in data
                for key in ("catalog", "payment_surcharges")
            ):
                self.save(settings)
            return settings
        except Exception:
            backup = self.settings_path.with_suffix(".broken.json")
            self.settings_path.replace(backup)
            settings = AppSettings.default()
            self.save(settings)
            return settings

    def save(self, settings: AppSettings) -> None:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Product/pricing configuration now lives in settings.json, so publish
        # settings atomically to avoid leaving a truncated file after a crash or
        # power loss during save.
        temp_path = self.settings_path.with_name(self.settings_path.name + ".tmp")
        temp_path.write_text(
            json.dumps(settings.to_dict(), indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, self.settings_path)
