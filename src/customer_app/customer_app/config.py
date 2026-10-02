"""Customer/job field definitions and atomically persisted non-sensitive settings."""
from __future__ import annotations

import copy
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .paths import app_support_dir, default_db_path

FIELD_TYPES = ('text', 'textarea', 'number', 'currency', 'date', 'dropdown', 'multiselect', 'boolean')
JOB_STATUSES = ('Scheduled', 'In progress', 'Completed', 'Cancelled')
PAYMENT_STATUSES = ('Unpaid', 'Invoiced', 'Part-paid', 'Paid')
FREQUENCIES = {
    'One-off / as needed': (None, ''), 'Monthly': (1, 'months'),
    'Every 6 weeks': (6, 'weeks'), 'Every 8 weeks': (8, 'weeks'),
    'Every 10 weeks': (10, 'weeks'), 'Every 12 weeks': (12, 'weeks'),
    'Quarterly': (3, 'months'), 'Six-monthly': (6, 'months'),
    'Annual': (12, 'months'),
}

@dataclass
class FieldDefinition:
    key: str
    label: str
    field_type: str = 'text'
    required: bool = False
    browse_column: bool = False
    options: list[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FieldDefinition':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

CUSTOMER_FIELDS = [
    FieldDefinition('name', 'Client name', required=True, browse_column=True),
    FieldDefinition('business_name', 'Business name'),
    FieldDefinition('phone', 'Phone number', browse_column=True),
    FieldDefinition('email', 'Email address'),
    FieldDefinition('address_line_1', 'Street address', browse_column=True),
    FieldDefinition('address_line_2', 'Address line 2'),
    FieldDefinition('suburb', 'Suburb', browse_column=True),
    FieldDefinition('state', 'State / territory', 'dropdown', options=['NSW','VIC','QLD','ACT','SA','WA','TAS','NT']),
    FieldDefinition('postcode', 'Postcode'),
    FieldDefinition('frequency_value', 'Repeat interval', 'number'),
    FieldDefinition('frequency_unit', 'Repeat unit', 'dropdown', options=['days','weeks','months','years']),
    FieldDefinition('first_service_date', 'First / next service date', 'date'),
    FieldDefinition('default_job_type', 'Nature of job', 'dropdown', browse_column=True),
    FieldDefinition('default_equipment', 'Equipment required', 'multiselect'),
    FieldDefinition('default_fee', 'Standard charge / fee (AUD)', 'currency', browse_column=True),
    FieldDefinition('default_payment_type', 'Usual payment method', 'dropdown'),
    FieldDefinition('notes', 'Customer / access notes', 'textarea'),
    FieldDefinition('active', 'Active customer', 'boolean'),
]
JOB_FIELDS = [
    FieldDefinition('scheduled_date', 'Scheduled date', 'date', browse_column=True),
    FieldDefinition('completed_date', 'Completed date', 'date', browse_column=True),
    FieldDefinition('status', 'Job status', 'dropdown', True, True, list(JOB_STATUSES)),
    FieldDefinition('job_type', 'Nature of job', 'dropdown', browse_column=True),
    FieldDefinition('equipment', 'Equipment required', 'multiselect'),
    FieldDefinition('fee', 'Charge / fee (AUD)', 'currency', browse_column=True),
    FieldDefinition('payment_type', 'Payment method', 'dropdown', browse_column=True),
    FieldDefinition('payment_status', 'Payment status', 'dropdown', True, True, list(PAYMENT_STATUSES)),
    FieldDefinition('notes', 'Job notes', 'textarea'),
]
CORE_FIELDS = {'customers': {f.key for f in CUSTOMER_FIELDS}, 'jobs': {f.key for f in JOB_FIELDS}}
RESERVED_KEYS = {'id','customer_id','created_at','updated_at','deleted_at','custom_fields','fee_cents','default_fee_cents','jobs_completed','last_job','next_due'}

@dataclass
class AppSettings:
    db_path: Path = field(default_factory=default_db_path)
    customer_fields: list[FieldDefinition] = field(default_factory=lambda: copy.deepcopy(CUSTOMER_FIELDS))
    job_fields: list[FieldDefinition] = field(default_factory=lambda: copy.deepcopy(JOB_FIELDS))
    equipment_options: list[str] = field(default_factory=lambda: ['Extension pole','3m ladder','6m ladder','Water-fed pole','Pressure washer','Harness','Other'])
    job_type_options: list[str] = field(default_factory=lambda: ['External windows','Internal windows','Internal + external','Screens','Skylights','Solar panels','Pressure cleaning','Commercial clean','Other'])
    payment_type_options: list[str] = field(default_factory=lambda: ['Cash','Card','Bank transfer','Other'])

    def fields_for(self, entity: str) -> list[FieldDefinition]:
        if entity not in CORE_FIELDS:
            raise ValueError('Unknown record type.')
        fields = copy.deepcopy(self.customer_fields if entity == 'customers' else self.job_fields)
        for f in fields:
            if f.key in ('default_equipment','equipment'): f.options = list(self.equipment_options)
            if f.key in ('default_job_type','job_type'): f.options = list(self.job_type_options)
            if f.key in ('default_payment_type','payment_type'): f.options = list(self.payment_type_options)
        return fields

    def validate(self) -> None:
        for name in ('equipment_options','job_type_options','payment_type_options'):
            options = getattr(self, name)
            if not isinstance(options, list) or any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in options):
                raise ValueError(f'{name}: enter non-empty options, one per line.')
            if len({v.casefold() for v in options}) != len(options):
                raise ValueError(f'{name}: options must be unique.')
        for entity, defaults in [('customers',CUSTOMER_FIELDS), ('jobs',JOB_FIELDS)]:
            fields = self.customer_fields if entity == 'customers' else self.job_fields
            seen = set()
            for f in fields:
                if not re.fullmatch(r'[a-z][a-z0-9_]*', f.key) or f.key in seen or f.key in RESERVED_KEYS:
                    raise ValueError(f'Invalid or duplicate field key: {f.key}')
                seen.add(f.key)
                if not f.label.strip() or f.field_type not in FIELD_TYPES:
                    raise ValueError(f'Invalid field definition: {f.key}')
                if not isinstance(f.options, list) or any(not isinstance(v, str) or not v.strip() for v in f.options):
                    raise ValueError(f'Invalid choices for {f.label}.')
                if len(set(f.options)) != len(f.options): raise ValueError(f'Duplicate choices for {f.label}.')
                if f.required and not f.enabled: raise ValueError(f'Required field {f.label} must be enabled.')
                if f.key not in CORE_FIELDS[entity] and f.enabled and f.field_type in ('dropdown','multiselect') and not f.options:
                    raise ValueError(f'{f.label} needs at least one choice.')
            for base in defaults:
                saved = next((f for f in fields if f.key == base.key), None)
                if saved is None or saved.field_type != base.field_type or not saved.enabled or (base.required and not saved.required):
                    raise ValueError(f'Core field {base.label} must retain its type and required setting.')
                if base.key in ('status','payment_status','frequency_unit') and saved.options != base.options:
                    raise ValueError(f'{base.label} choices are controlled by the application.')

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['db_path'] = str(self.db_path)
        d['config_version'] = 1
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'AppSettings':
        if data.get('config_version', 1) != 1: raise ValueError('Unsupported settings version.')
        settings = cls()
        settings.db_path = Path(data.get('db_path') or settings.db_path)
        for attr in ('customer_fields','job_fields'):
            if attr in data:
                saved = [FieldDefinition.from_dict(f) for f in data[attr]]
                # Introduced core fields are added without dropping custom definitions.
                keys = {f.key for f in saved}
                saved.extend(copy.deepcopy(f) for f in getattr(settings, attr) if f.key not in keys)
                setattr(settings, attr, saved)
        for attr in ('equipment_options','job_type_options','payment_type_options'):
            if attr in data: setattr(settings, attr, data[attr])
        settings.validate()
        return settings

class SettingsStore:
    def __init__(self, settings_path: Path | None = None):
        # Separate from the inherited receipt settings, preventing accidental reuse.
        self.settings_path = Path(settings_path or app_support_dir() / 'crm-settings.json')

    def load(self) -> AppSettings:
        if not self.settings_path.exists(): return AppSettings()
        try:
            return AppSettings.from_dict(json.loads(self.settings_path.read_text(encoding='utf-8')))
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f'Cannot load settings from {self.settings_path}: {exc}. The file has been preserved.') from exc

    def save(self, settings: AppSettings) -> None:
        settings.validate()
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.settings_path.with_name(self.settings_path.name + '.tmp')
        with temporary.open('w', encoding='utf-8') as h:
            json.dump(settings.to_dict(), h, indent=2, ensure_ascii=False)
            h.flush()
            os.fsync(h.fileno())
        os.replace(temporary, self.settings_path)
