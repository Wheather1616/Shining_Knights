"""Domain records, exact money handling and calendar recurrence."""
from __future__ import annotations
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

class ValidationError(ValueError):
    pass

def money_to_cents(value: Any) -> int | None:
    if value is None or value == '': return None
    try:
        amount = Decimal(str(value).replace('$','').replace(',','').strip())
        if not amount.is_finite() or amount < 0 or amount > Decimal('999999999.99'):
            raise InvalidOperation
        cents = amount * 100
        if cents != cents.to_integral_value():
            raise ValidationError('Money amounts must have at most two decimal places.')
        return int(cents)
    except ValidationError:
        raise
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError('Enter a valid, non-negative amount in AUD.') from exc

def money_text(cents: int | None) -> str:
    return '' if cents is None else f'{Decimal(cents) / 100:.2f}'

def hours_text(value: Any) -> str | None:
    if value is None or value == '':
        return None
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal('9999.99') or amount * 100 != (amount * 100).to_integral_value():
            raise InvalidOperation
        return f'{amount:.2f}'
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError('Hours must be a non-negative number with at most two decimal places (up to 9999.99).') from exc

def job_types(value: Any) -> list[str]:
    """Normalise a legacy single choice or a current list without splitting names."""
    if isinstance(value, str):
        value = [value] if value else []
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValidationError('Nature of job must contain a list of named choices.')
    return list(dict.fromkeys(value))

def add_interval(anchor: str, value: int | None, unit: str) -> str | None:
    if not anchor or value is None or not unit: return None
    d = date.fromisoformat(anchor)
    if unit in ('days','weeks'):
        return (d + timedelta(days=value * (7 if unit == 'weeks' else 1))).isoformat()
    months = value * (12 if unit == 'years' else 1)
    year, month = divmod(d.year * 12 + d.month - 1 + months, 12)
    return date(year, month + 1, min(d.day, monthrange(year, month + 1)[1])).isoformat()

@dataclass
class CustomerRecord:
    name: str = ''
    business_name: str = ''
    phone: str = ''
    email: str = ''
    address_line_1: str = ''
    address_line_2: str = ''
    suburb: str = ''
    state: str = ''
    postcode: str = ''
    frequency_value: int | None = None
    frequency_unit: str = ''
    first_service_date: str = ''
    default_job_type: list[str] = field(default_factory=list)
    default_equipment: list[str] = field(default_factory=list)
    default_fee: str | None = None
    default_payment_type: str = ''
    notes: str = ''
    active: bool = True
    custom_fields: dict[str, Any] = field(default_factory=dict)
    first_name: str = ''
    last_name: str = ''
    default_hours: str | None = None

@dataclass
class JobRecord:
    customer_id: int
    scheduled_date: str = ''
    completed_date: str = ''
    status: str = 'Scheduled'
    job_type: list[str] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)
    fee: str | None = None
    payment_type: str = ''
    payment_status: str = 'Unpaid'
    notes: str = ''
    custom_fields: dict[str, Any] = field(default_factory=dict)
    hours: str | None = None
    service_id: int | None = None
    service_name: str = ''


@dataclass
class ServiceRecord:
    """A reusable customer-specific visit, independent of global job types."""
    customer_id: int
    name: str = ''
    job_type: list[str] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)
    fee: str | None = None
    hours: str | None = None
    notes: str = ''
