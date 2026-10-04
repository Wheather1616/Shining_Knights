"""Encrypted relational customer/job repository. No receipt schema or plaintext fallback."""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .config import AppSettings, CORE_FIELDS
from .db_crypto import is_plaintext_sqlite, migrate_plaintext_database, open_encrypted_connection, verify_encrypted_database
from .models import CustomerRecord, JobRecord, ValidationError, add_interval, money_text, money_to_cents
from .security import SecureKeyStore

SCHEMA_VERSION = 1
SCHEMA = '''
CREATE TABLE customers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL CHECK(length(trim(name)) > 0),
 business_name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
 address_line_1 TEXT NOT NULL DEFAULT '', address_line_2 TEXT NOT NULL DEFAULT '',
 suburb TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT '', postcode TEXT NOT NULL DEFAULT '',
 frequency_value INTEGER, frequency_unit TEXT NOT NULL DEFAULT '', first_service_date TEXT NOT NULL DEFAULT '',
 default_job_type TEXT NOT NULL DEFAULT '', default_equipment TEXT NOT NULL DEFAULT '[]',
 default_fee_cents INTEGER CHECK(default_fee_cents IS NULL OR (typeof(default_fee_cents)='integer' AND default_fee_cents >= 0)),
 default_payment_type TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 custom_fields TEXT NOT NULL DEFAULT '{}', search_text TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CHECK((frequency_value IS NULL AND frequency_unit='') OR
 (typeof(frequency_value)='integer' AND frequency_value > 0 AND frequency_unit IN ('days','weeks','months','years')))
);
CREATE TABLE jobs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
 scheduled_date TEXT NOT NULL DEFAULT '', completed_date TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'Scheduled' CHECK(status IN ('Scheduled','In progress','Completed','Cancelled')),
 job_type TEXT NOT NULL DEFAULT '', equipment TEXT NOT NULL DEFAULT '[]',
 fee_cents INTEGER CHECK(fee_cents IS NULL OR (typeof(fee_cents)='integer' AND fee_cents >= 0)),
 payment_type TEXT NOT NULL DEFAULT '',
 payment_status TEXT NOT NULL DEFAULT 'Unpaid' CHECK(payment_status IN ('Unpaid','Invoiced','Part-paid','Paid')),
 notes TEXT NOT NULL DEFAULT '', custom_fields TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT,
 CHECK((status='Completed' AND completed_date<>'') OR (status<>'Completed' AND completed_date=''))
);
CREATE INDEX idx_customers_name ON customers(name COLLATE NOCASE);
CREATE INDEX idx_customers_active ON customers(active);
CREATE INDEX idx_jobs_customer ON jobs(customer_id);
CREATE INDEX idx_jobs_schedule ON jobs(scheduled_date, status, deleted_at);
CREATE INDEX idx_jobs_completed ON jobs(completed_date, status, deleted_at);
CREATE TABLE crm_schema (version INTEGER NOT NULL);
INSERT INTO crm_schema VALUES(1);
'''

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')

def _search(values: dict[str, Any]) -> str:
    result = ' '.join(str(v) for v in values.values() if v is not None).casefold()
    if 'phone' in values: result += ' ' + re.sub(r'\D', '', values['phone'])
    return result

class CustomerDatabase:
    def __init__(self, db_path: Path, settings: AppSettings | None = None, *, key_hex: str | None = None):
        self.db_path = Path(db_path)
        self.settings = settings or AppSettings(db_path=self.db_path)
        self.settings.validate()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Explicit key injection is for tests/controlled recovery; production uses OS storage.
        self.key_hex = key_hex if key_hex is not None else SecureKeyStore().get_or_create_database_key()
        if self.db_path.exists() and self.db_path.stat().st_size:
            if is_plaintext_sqlite(self.db_path): migrate_plaintext_database(self.db_path, self.key_hex)
            else: verify_encrypted_database(self.db_path, self.key_hex)
        self.initialise()
        if __import__('os').name == 'posix': self.db_path.chmod(0o600)

    @contextmanager
    def connect(self):
        conn = open_encrypted_connection(self.db_path, self.key_hex)
        try:
            with conn: yield conn
        finally:
            conn.close()

    def initialise(self) -> None:
        with self.connect() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'crm_schema' in tables:
                versions = conn.execute('SELECT version FROM crm_schema').fetchall()
                if len(versions) != 1 or versions[0][0] != SCHEMA_VERSION:
                    raise ValidationError('Unsupported customer database version. No schema changes were made.')
            elif 'customers' in tables or 'jobs' in tables:
                raise ValidationError('This database already has an unrecognised customer/job schema. Use a new file; the original has been preserved.')
            else:
                # Legacy receipts, if present, remain untouched. They are not customer records.
                conn.executescript('BEGIN IMMEDIATE;\n' + SCHEMA + '\nCOMMIT;')

    def _validate_fields(self, entity: str, values: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
        previous = previous or {}
        values = dict(values)
        custom = dict(values.get('custom_fields') or {})
        if not isinstance(values.get('custom_fields', {}), dict): raise ValidationError('Custom fields must be a dictionary.')
        known = {f.key for f in self.settings.fields_for(entity)}
        if any(k not in known and k not in previous.get('custom_fields', {}) for k in custom):
            raise ValidationError('A custom field is not configured for this record type.')
        for f in self.settings.fields_for(entity):
            target = values if f.key in CORE_FIELDS[entity] else custom
            value = target.get(f.key)
            old = previous.get(f.key) if f.key in CORE_FIELDS[entity] else previous.get('custom_fields', {}).get(f.key)
            if not f.enabled: continue
            empty = value is None or value == '' or value == []
            if f.required and empty: raise ValidationError(f'{f.label} is required.')
            if empty: continue
            if f.field_type in ('text','textarea','dropdown','date'):
                if not isinstance(value, str): raise ValidationError(f'{f.label} must be text.')
                value = value.strip()
                if f.required and not value: raise ValidationError(f'{f.label} is required.')
            if f.field_type == 'date':
                try:
                    parsed = date.fromisoformat(value)
                    if value != parsed.isoformat(): raise ValueError()
                except ValueError as exc: raise ValidationError(f'{f.label} must be a valid date (YYYY-MM-DD).') from exc
            elif f.field_type == 'currency': value = money_text(money_to_cents(value))
            elif f.field_type == 'number':
                try:
                    from decimal import Decimal
                    number = Decimal(str(value))
                    if not number.is_finite(): raise ValueError()
                    value = int(number) if number == number.to_integral_value() else str(number)
                except Exception as exc: raise ValidationError(f'{f.label} must be a valid number.') from exc
            elif f.field_type == 'boolean':
                if not isinstance(value, (bool, int)) or value not in (0,1): raise ValidationError(f'{f.label} must be true or false.')
                value = bool(value)
            elif f.field_type == 'dropdown':
                if value not in f.options and value != old: raise ValidationError(f'Choose a configured option for {f.label}.')
            elif f.field_type == 'multiselect':
                if not isinstance(value, list) or any(not isinstance(v,str) for v in value): raise ValidationError(f'{f.label} must be a list of choices.')
                if any(v not in f.options and v not in (old or []) for v in value): raise ValidationError(f'Choose configured options for {f.label}.')
                value = list(dict.fromkeys(value))
            target[f.key] = value
        values['custom_fields'] = custom
        return values

    def _customer_values(self, record: CustomerRecord, previous=None) -> dict[str, Any]:
        v = self._validate_fields('customers', asdict(record), previous)
        if v['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v['email']):
            raise ValidationError('Enter a valid email address, or leave it blank.')
        if v['phone'] and not 6 <= len(re.sub(r'\D', '', v['phone'])) <= 15:
            raise ValidationError('Enter a phone number containing 6 to 15 digits.')
        if v['postcode'] and not re.fullmatch(r'\d{4}', v['postcode']):
            raise ValidationError('Australian postcodes must contain four digits.')
        if v['frequency_value'] in ('',None): v['frequency_value'] = None
        if v['frequency_value'] is None:
            if v['frequency_unit']: raise ValidationError('Enter a repeat interval, or clear the repeat unit.')
        elif not isinstance(v['frequency_value'], int) or isinstance(v['frequency_value'], bool) or not 1 <= v['frequency_value'] <= 3650 or not v['frequency_unit']:
            raise ValidationError('Repeat interval must be a whole number from 1 to 3650, with a repeat unit.')
        v['default_fee_cents'] = money_to_cents(v.pop('default_fee'))
        v['search_text'] = _search(v)
        v['default_equipment'] = json.dumps(v['default_equipment'], ensure_ascii=False)
        v['custom_fields'] = json.dumps(v['custom_fields'], ensure_ascii=False, allow_nan=False)
        return v

    def _job_values(self, record: JobRecord, previous=None) -> dict[str, Any]:
        v = self._validate_fields('jobs', asdict(record), previous)
        if not isinstance(v['customer_id'],int) or isinstance(v['customer_id'],bool): raise ValidationError('Choose a valid customer.')
        if v['status'] == 'Completed' and not v['completed_date']:
            raise ValidationError('Completed jobs need a completed date.')
        if v['status'] != 'Completed' and v['completed_date']:
            raise ValidationError('Only completed jobs can have a completed date.')
        if v['completed_date'] and v['completed_date'] > date.today().isoformat():
            raise ValidationError('A completed date cannot be in the future.')
        v['fee_cents'] = money_to_cents(v.pop('fee'))
        v['equipment'] = json.dumps(v['equipment'], ensure_ascii=False)
        v['custom_fields'] = json.dumps(v['custom_fields'], ensure_ascii=False, allow_nan=False)
        return v

    @staticmethod
    def _insert(conn, table: str, values: dict[str, Any]) -> int:
        now = _now()
        values = {**values, 'created_at':now, 'updated_at':now}
        keys = ','.join(values)
        cursor = conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({','.join('?' for _ in values)})",tuple(values.values()))
        return int(cursor.lastrowid)

    @staticmethod
    def _update(conn, table: str, record_id: int, values: dict[str, Any]) -> None:
        values = {**values, 'updated_at':_now()}
        conn.execute(f"UPDATE {table} SET {','.join(k+'=?' for k in values)} WHERE id=?", (*values.values(),record_id))

    @staticmethod
    def _decode(row, entity: str) -> dict[str, Any] | None:
        if row is None: return None
        v = dict(row)
        v['custom_fields'] = json.loads(v['custom_fields'])
        if entity == 'customers':
            v['default_equipment'] = json.loads(v['default_equipment'])
            v['default_fee'] = money_text(v['default_fee_cents']) or None
            v['active'] = bool(v['active'])
        else:
            v['equipment'] = json.loads(v['equipment'])
            v['fee'] = money_text(v['fee_cents']) or None
        return v

    def create_customer(self, record: CustomerRecord) -> int:
        v = self._customer_values(record)
        with self.connect() as conn: return self._insert(conn,'customers',v)

    def get_customer(self, customer_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            return self._decode(conn.execute('SELECT * FROM customers WHERE id=?',(customer_id,)).fetchone(),'customers')

    def update_customer(self, customer_id: int, record: CustomerRecord) -> None:
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            old = self._decode(conn.execute('SELECT * FROM customers WHERE id=?',(customer_id,)).fetchone(),'customers')
            if old is None: raise ValidationError('Customer not found.')
            self._update(conn,'customers',customer_id,self._customer_values(record,old))

    def set_customer_active(self, customer_id: int, active: bool) -> None:
        with self.connect() as conn:
            if conn.execute('UPDATE customers SET active=?,updated_at=? WHERE id=?',(bool(active),_now(),customer_id)).rowcount != 1:
                raise ValidationError('Customer not found.')

    def list_customers(self, search: str = '', *, include_inactive: bool = False) -> list[dict[str, Any]]:
        with self.connect() as conn:
            terms = [t.replace('\\','\\\\').replace('%','\\%').replace('_','\\_') for t in search.strip().casefold().split()]
            condition = ' AND '.join("search_text LIKE ? ESCAPE '\\'" for _ in terms) or '1'
            rows = conn.execute(f"SELECT * FROM customers WHERE (? OR active=1) AND {condition} ORDER BY name COLLATE NOCASE,id", (include_inactive,*('%'+t+'%' for t in terms))).fetchall()
            return [self._decode(r,'customers') for r in rows]

    def new_job_for_customer(self, customer_id: int, scheduled_date: str = '') -> JobRecord:
        c = self.get_customer(customer_id)
        if c is None or not c['active']: raise ValidationError('Choose an active customer for a new job.')
        return JobRecord(customer_id=customer_id, scheduled_date=scheduled_date,
                         job_type=c['default_job_type'],equipment=list(c['default_equipment']),
                         fee=c['default_fee'],payment_type=c['default_payment_type'])

    def create_job(self, record: JobRecord) -> int:
        v = self._job_values(record)
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            customer = conn.execute('SELECT active FROM customers WHERE id=?',(record.customer_id,)).fetchone()
            if customer is None or not customer['active']: raise ValidationError('Choose an active customer for a new job.')
            return self._insert(conn,'jobs',v)

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            return self._decode(conn.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone(),'jobs')

    def update_job(self, job_id: int, record: JobRecord) -> None:
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            old = self._decode(conn.execute('SELECT * FROM jobs WHERE id=? AND deleted_at IS NULL',(job_id,)).fetchone(),'jobs')
            if old is None: raise ValidationError('Job not found, or it is in Trash.')
            if old['customer_id'] != record.customer_id: raise ValidationError('The customer of an existing job cannot be changed.')
            self._update(conn,'jobs',job_id,self._job_values(record,old))

    def complete_job(self, job_id: int, completed_date: str | None = None) -> None:
        j = self.get_job(job_id)
        if j is None: raise ValidationError('Job not found.')
        record = JobRecord(**{k:j[k] for k in JobRecord.__dataclass_fields__})
        record.status = 'Completed'
        record.completed_date = completed_date or date.today().isoformat()
        self.update_job(job_id,record)

    def trash_job(self, job_id: int) -> None:
        with self.connect() as conn:
            if conn.execute('UPDATE jobs SET deleted_at=?,updated_at=? WHERE id=? AND deleted_at IS NULL',(_now(),_now(),job_id)).rowcount != 1:
                raise ValidationError('Job not found, or already in Trash.')

    def restore_job(self, job_id: int) -> None:
        with self.connect() as conn:
            if conn.execute('UPDATE jobs SET deleted_at=NULL,updated_at=? WHERE id=? AND deleted_at IS NOT NULL',(_now(),job_id)).rowcount != 1:
                raise ValidationError('Job is not in Trash.')

    def list_jobs(self, customer_id: int | None = None, *, status: str = '', include_deleted: bool = False, group_by: str = 'date', search: str = '') -> list[dict[str, Any]]:
        sorts = {'date':"COALESCE(NULLIF(j.scheduled_date,''),NULLIF(j.completed_date,''),'9999-12-31'),j.id",'customer':'c.name COLLATE NOCASE,j.scheduled_date,j.id','status':'j.status,j.scheduled_date,j.id'}
        if group_by not in sorts: raise ValidationError('Unknown job grouping.')
        with self.connect() as conn:
            rows = conn.execute(f'''SELECT j.*,c.name AS customer_name,c.suburb,c.address_line_1,c.phone
            FROM jobs j JOIN customers c ON c.id=j.customer_id
            WHERE (? IS NULL OR j.customer_id=?) AND (?='' OR j.status=?) AND (? OR j.deleted_at IS NULL)
            ORDER BY {sorts[group_by]}''',(customer_id,customer_id,status,status,include_deleted)).fetchall()
            result = [self._decode(r,'jobs') for r in rows]
            terms = search.strip().casefold().split()
            return [r for r in result if all(t in _search(r) for t in terms)]

    def customer_summary(self, customer_id: int) -> dict[str, Any]:
        c = self.get_customer(customer_id)
        if c is None: raise ValidationError('Customer not found.')
        with self.connect() as conn:
            r = conn.execute("SELECT COUNT(*) AS n,MAX(completed_date) AS last_job FROM jobs WHERE customer_id=? AND status='Completed' AND deleted_at IS NULL",(customer_id,)).fetchone()
            upcoming = conn.execute("SELECT MIN(scheduled_date) FROM jobs WHERE customer_id=? AND status IN ('Scheduled','In progress') AND scheduled_date<>'' AND deleted_at IS NULL",(customer_id,)).fetchone()[0]
        try:
            due = add_interval(r['last_job'],c['frequency_value'],c['frequency_unit']) if r['last_job'] else (c['first_service_date'] or None)
        except (ValueError,OverflowError): due = None
        return {'jobs_completed':r['n'],'last_job':r['last_job'],'next_due':due,'next_scheduled':upcoming}

    def dashboard(self) -> dict[str, Any]:
        today = date.today().isoformat()
        month = today[:7] + '-01'
        with self.connect() as conn:
            return {
                'active_customers':conn.execute('SELECT COUNT(*) FROM customers WHERE active=1').fetchone()[0],
                'upcoming_jobs':conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('Scheduled','In progress') AND deleted_at IS NULL").fetchone()[0],
                'overdue_jobs':conn.execute("SELECT COUNT(*) FROM jobs WHERE scheduled_date<>'' AND scheduled_date<? AND status IN ('Scheduled','In progress') AND deleted_at IS NULL",(today,)).fetchone()[0],
                'completed_month_cents':conn.execute("SELECT COALESCE(SUM(fee_cents),0) FROM jobs WHERE status='Completed' AND completed_date BETWEEN ? AND ? AND deleted_at IS NULL",(month,today)).fetchone()[0],
            }
