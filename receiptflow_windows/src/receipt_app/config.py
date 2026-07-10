from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

FieldType = Literal["text", "number", "currency", "date", "textarea", "dropdown"]
PAYMENT_TYPE_OPTIONS = ["Eftpos", "Cash", "MOTO", "Direct Debit"]

DESCRIPTION_OPTIONS = ["Renewal", "New Member", "Replacement Card", "Function"]

APP_NAME = "ReceiptFlow"


def app_support_dir() -> Path:
    """Return a macOS-friendly application support folder, with sane fallbacks."""
    home = Path.home()
    if os.name == "posix" and (home / "Library").exists():
        return home / "Library" / "Application Support" / APP_NAME
    return home / f".{APP_NAME.lower()}"


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
    FieldDefinition("description", "Description", "dropdown", True, True, True, DESCRIPTION_OPTIONS),
    FieldDefinition("name", "Name / Customer", "text", False, True, True),
    FieldDefinition("amount", "Amount", "currency", True, True, True),
    FieldDefinition("payment_type", "Payment Type", "dropdown", True, True, True, PAYMENT_TYPE_OPTIONS),
    FieldDefinition("member_no", "Member No", "text", False, True, True),
    FieldDefinition("notes", "Notes", "textarea", False, True, False),
]


@dataclass
class AppSettings:
    db_path: Path
    import_folder: Path
    fields: list[FieldDefinition] = field(default_factory=lambda: list(DEFAULT_FIELDS))
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
        support = app_support_dir()
        return AppSettings(
            db_path=support / "receipts.db",
            import_folder=Path.home() / "Downloads",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_path": str(self.db_path),
            "import_folder": str(self.import_folder),
            "fields": [field_def.to_dict() for field_def in self.fields],
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

            for default_field in DEFAULT_FIELDS:
                merged_fields.append(saved_by_key.pop(default_field.key, default_field))

            merged_fields.extend(saved_by_key.values())
            fields = merged_fields
        else:
            fields = list(DEFAULT_FIELDS)
        return AppSettings(
            db_path=Path(data.get("db_path") or default.db_path),
            import_folder=Path(data.get("import_folder") or default.import_folder),
            fields=fields or list(DEFAULT_FIELDS),
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
            settings = AppSettings.default()
            self.save(settings)
            return settings
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return AppSettings.from_dict(data)
        except Exception:
            backup = self.settings_path.with_suffix(".broken.json")
            self.settings_path.replace(backup)
            settings = AppSettings.default()
            self.save(settings)
            return settings

    def save(self, settings: AppSettings) -> None:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
