"""Encrypted relational customer/job repository. No receipt schema or plaintext fallback."""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import AppSettings, CORE_FIELDS
from .db_crypto import is_plaintext_sqlite, migrate_plaintext_database, open_encrypted_connection, verify_encrypted_database
from .models import CustomerRecord, JobRecord, ServiceRecord, ValidationError, add_interval, hours_text, job_types, money_text, money_to_cents, work_sides
from .security import SecureKeyStore

SCHEMA_VERSION = 5
SERVICE_SCHEMA = '''
CREATE TABLE customer_services (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
 name TEXT NOT NULL CHECK(length(trim(name)) > 0),
 job_type TEXT NOT NULL DEFAULT '[]', equipment TEXT NOT NULL DEFAULT '[]',
 fee_cents INTEGER CHECK(fee_cents IS NULL OR (typeof(fee_cents)='integer' AND fee_cents >= 0)),
 hours TEXT, notes TEXT NOT NULL DEFAULT '',
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0,1)),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CHECK(is_default=0 OR active=1)
);
CREATE UNIQUE INDEX idx_service_name ON customer_services(customer_id, name COLLATE NOCASE);
CREATE UNIQUE INDEX idx_service_default ON customer_services(customer_id) WHERE is_default=1;
CREATE INDEX idx_services_customer ON customer_services(customer_id,active);
'''
SCHEMA = '''
CREATE TABLE customers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL CHECK(length(trim(name)) > 0),
 first_name TEXT NOT NULL DEFAULT '', last_name TEXT NOT NULL DEFAULT '', default_hours TEXT,
 business_name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
 address_line_1 TEXT NOT NULL DEFAULT '', address_line_2 TEXT NOT NULL DEFAULT '',
 suburb TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT '', postcode TEXT NOT NULL DEFAULT '',
 frequency_value INTEGER, frequency_unit TEXT NOT NULL DEFAULT '', first_service_date TEXT NOT NULL DEFAULT '',
 default_job_type TEXT NOT NULL DEFAULT '[]', default_equipment TEXT NOT NULL DEFAULT '[]',
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
 job_type TEXT NOT NULL DEFAULT '[]', equipment TEXT NOT NULL DEFAULT '[]',
 fee_cents INTEGER CHECK(fee_cents IS NULL OR (typeof(fee_cents)='integer' AND fee_cents >= 0)),
 hours TEXT, service_id INTEGER REFERENCES customer_services(id) ON DELETE RESTRICT,
 service_name TEXT NOT NULL DEFAULT '',
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
''' + SERVICE_SCHEMA + '''
ALTER TABLE customers ADD COLUMN default_job_type_sides TEXT NOT NULL DEFAULT '{}';
ALTER TABLE jobs ADD COLUMN job_type_sides TEXT NOT NULL DEFAULT '{}';
ALTER TABLE customer_services ADD COLUMN job_type_sides TEXT NOT NULL DEFAULT '{}';
CREATE TABLE crm_schema (version INTEGER NOT NULL);
INSERT INTO crm_schema VALUES(5);
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
                if len(versions) != 1 or versions[0][0] not in (1, 2, 3, 4, SCHEMA_VERSION):
                    raise ValidationError('Unsupported customer database version. No schema changes were made.')
                if versions[0][0] == 1:
                    self._migrate_v1(conn)
                if versions[0][0] in (1, 2):
                    self._migrate_v2(conn)
                if versions[0][0] < 4:
                    self._migrate_v3(conn)
                if versions[0][0] < 5:
                    self._migrate_v4(conn)
            elif 'customers' in tables or 'jobs' in tables:
                raise ValidationError('This database already has an unrecognised customer/job schema. Use a new file; the original has been preserved.')
            else:
                # Legacy receipts, if present, remain untouched. They are not customer records.
                conn.executescript('BEGIN IMMEDIATE;\n' + SCHEMA + '\nCOMMIT;')

    @staticmethod
    def _migrate_v1(conn):
        # SQLCipher and the transaction protect existing bytes and customer/job IDs.
        # Keep legacy names intact. People can split them explicitly when editing.
        conn.execute('BEGIN IMMEDIATE')
        conn.execute("ALTER TABLE customers ADD COLUMN first_name TEXT NOT NULL DEFAULT ''")
        conn.execute("ALTER TABLE customers ADD COLUMN last_name TEXT NOT NULL DEFAULT ''")
        conn.execute('ALTER TABLE customers ADD COLUMN default_hours TEXT')
        conn.execute('ALTER TABLE jobs ADD COLUMN hours TEXT')
        conn.execute('UPDATE crm_schema SET version=2')

    @staticmethod
    def _migrate_v2(conn):
        if not conn.in_transaction:
            conn.execute('BEGIN IMMEDIATE')
        # Execute each DDL statement in the existing transaction; executescript
        # would implicitly commit and break rollback of a chained v1 upgrade.
        for statement in SERVICE_SCHEMA.split(';'):
            if statement.strip():
                conn.execute(statement)
        conn.execute('ALTER TABLE jobs ADD COLUMN service_id INTEGER REFERENCES customer_services(id) ON DELETE RESTRICT')
        conn.execute("ALTER TABLE jobs ADD COLUMN service_name TEXT NOT NULL DEFAULT ''")
        conn.execute("""INSERT INTO customer_services
            (customer_id,name,job_type,equipment,fee_cents,hours,is_default,created_at,updated_at)
            SELECT id,'Usual service',default_job_type,default_equipment,default_fee_cents,
                default_hours,1,created_at,updated_at FROM customers""")
        conn.execute('UPDATE crm_schema SET version=3')

    @staticmethod
    def _migrate_v3(conn):
        if not conn.in_transaction:
            conn.execute('BEGIN IMMEDIATE')
        # Old strings represent one whole option, even if their label contains
        # commas or looks like JSON. Preserve job snapshots, prices and links.
        for table, column in [('customers','default_job_type'),('jobs','job_type'),('customer_services','job_type')]:
            for row in conn.execute(f'SELECT id,{column} FROM {table}').fetchall():
                value = row[column]
                conn.execute(f'UPDATE {table} SET {column}=? WHERE id=?',
                             (json.dumps([value] if value else [],ensure_ascii=False),row['id']))
        conn.execute('UPDATE crm_schema SET version=4')

    @staticmethod
    def _migrate_v4(conn):
        if not conn.in_transaction:
            conn.execute('BEGIN IMMEDIATE')
        for table, column in [('customers', 'default_job_type_sides'), ('jobs', 'job_type_sides'), ('customer_services', 'job_type_sides')]:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT NOT NULL DEFAULT '{{}}'")
        conn.execute('UPDATE crm_schema SET version=5')

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
        values = asdict(record)
        if any(not isinstance(values[key], str) for key in ('name', 'first_name', 'last_name')):
            raise ValidationError('Customer names must be text.')
        if previous and values['name'] != previous['name'] and (values['first_name'], values['last_name']) == (previous['first_name'], previous['last_name']):
            values['first_name'] = values['last_name'] = ''  # Support legacy API renames.
        elif values['first_name'].strip() or values['last_name'].strip():
            if not values['first_name'].strip():
                raise ValidationError('Enter a first name.')
            values['name'] = ' '.join(filter(None, (values['first_name'].strip(), values['last_name'].strip())))
        values['default_job_type'] = job_types(values['default_job_type'])
        v = self._validate_fields('customers', values, previous)
        if v['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v['email']):
            raise ValidationError('Enter a valid email address, or leave it blank.')
        if v['phone'] and (not re.fullmatch(r'\+?[0-9 ()-]+', v['phone']) or not 10 <= len(re.sub(r'\D', '', v['phone'])) <= 15):
            raise ValidationError('Enter a phone number containing 10 to 15 digits, or leave it blank.')
        if v['postcode'] and not re.fullmatch(r'\d{4}', v['postcode']):
            raise ValidationError('Australian postcodes must contain four digits.')
        if v['frequency_value'] in ('',None): v['frequency_value'] = None
        if v['frequency_value'] is None:
            if v['frequency_unit']: raise ValidationError('Enter a repeat interval, or clear the repeat unit.')
        elif not isinstance(v['frequency_value'], int) or isinstance(v['frequency_value'], bool) or not 1 <= v['frequency_value'] <= 3650 or not v['frequency_unit']:
            raise ValidationError('Repeat interval must be a whole number from 1 to 3650, with a repeat unit.')
        v['default_fee_cents'] = money_to_cents(v.pop('default_fee'))
        v['default_hours'] = hours_text(v['default_hours'])
        v['default_job_type_sides'] = work_sides(v['default_job_type_sides'], v['default_job_type'])
        v['search_text'] = _search(v)
        v['default_job_type_sides'] = json.dumps(v['default_job_type_sides'], ensure_ascii=False)
        v['default_job_type'] = json.dumps(v['default_job_type'],ensure_ascii=False)
        v['default_equipment'] = json.dumps(v['default_equipment'], ensure_ascii=False)
        v['custom_fields'] = json.dumps(v['custom_fields'], ensure_ascii=False, allow_nan=False)
        return v

    def _job_values(self, record: JobRecord, previous=None) -> dict[str, Any]:
        values = asdict(record)
        values['job_type'] = job_types(values['job_type'])
        v = self._validate_fields('jobs', values, previous)
        if not isinstance(v['customer_id'],int) or isinstance(v['customer_id'],bool): raise ValidationError('Choose a valid customer.')
        if v['status'] == 'Completed' and not v['completed_date']:
            raise ValidationError('Completed jobs need a completed date.')
        if v['status'] != 'Completed' and v['completed_date']:
            raise ValidationError('Only completed jobs can have a completed date.')
        if v['completed_date'] and v['completed_date'] > date.today().isoformat():
            raise ValidationError('A completed date cannot be in the future.')
        v['fee_cents'] = money_to_cents(v.pop('fee'))
        v['hours'] = hours_text(v['hours'])
        v['job_type_sides'] = json.dumps(work_sides(v['job_type_sides'], v['job_type']), ensure_ascii=False)
        v['job_type'] = json.dumps(v['job_type'],ensure_ascii=False)
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
            v['default_job_type'] = job_types(json.loads(v['default_job_type']))
            v['default_job_type_sides'] = work_sides(json.loads(v['default_job_type_sides']), v['default_job_type'])
            v['default_equipment'] = json.loads(v['default_equipment'])
            v['default_fee'] = money_text(v['default_fee_cents']) or None
            v['active'] = bool(v['active'])
        else:
            v['job_type'] = job_types(json.loads(v['job_type']))
            v['job_type_sides'] = work_sides(json.loads(v['job_type_sides']), v['job_type'])
            v['equipment'] = json.loads(v['equipment'])
            v['fee'] = money_text(v['fee_cents']) or None
        return v

    def create_customer(self, record: CustomerRecord) -> int:
        v = self._customer_values(record)
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            cid = self._insert(conn,'customers',v)
            self._insert(conn,'customer_services',self._usual_service_values(cid,v))
            return cid

    def get_customer(self, customer_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            return self._decode(conn.execute('SELECT * FROM customers WHERE id=?',(customer_id,)).fetchone(),'customers')

    def update_customer(self, customer_id: int, record: CustomerRecord) -> None:
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            old = self._decode(conn.execute('SELECT * FROM customers WHERE id=?',(customer_id,)).fetchone(),'customers')
            if old is None: raise ValidationError('Customer not found.')
            values = self._customer_values(record,old)
            self._update(conn,'customers',customer_id,values)
            usual = conn.execute('SELECT id FROM customer_services WHERE customer_id=? AND is_default=1',(customer_id,)).fetchone()
            if usual:
                service = self._usual_service_values(customer_id,values)
                for key in ('customer_id','name','is_default','active','notes'):
                    service.pop(key, None)
                self._update(conn,'customer_services',usual['id'],service)

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

    @staticmethod
    def _usual_service_values(customer_id, customer):
        return {'customer_id':customer_id, 'name':'Usual service',
                'job_type':customer['default_job_type'], 'job_type_sides':customer['default_job_type_sides'],
                'equipment':customer['default_equipment'],
                'fee_cents':customer['default_fee_cents'], 'hours':customer['default_hours'],
                'notes':'', 'active':1, 'is_default':1}

    @staticmethod
    def _decode_service(row):
        if row is None:
            return None
        value = dict(row)
        value['job_type'] = job_types(json.loads(value['job_type']))
        value['job_type_sides'] = work_sides(json.loads(value['job_type_sides']), value['job_type'])
        value['equipment'] = json.loads(value['equipment'])
        value['fee'] = money_text(value['fee_cents']) or None
        value['active'], value['is_default'] = bool(value['active']), bool(value['is_default'])
        return value

    def get_service(self, service_id):
        with self.connect() as conn:
            return self._decode_service(conn.execute('SELECT * FROM customer_services WHERE id=?',(service_id,)).fetchone())

    def list_services(self, customer_id, *, include_archived=False):
        with self.connect() as conn:
            return [self._decode_service(row) for row in conn.execute(
                'SELECT * FROM customer_services WHERE customer_id=? AND (? OR active=1) ORDER BY is_default DESC,name COLLATE NOCASE,id',
                (customer_id,include_archived))]

    def _service_values(self, record, previous=None):
        if not isinstance(record.customer_id,int) or isinstance(record.customer_id,bool):
            raise ValidationError('Choose a valid customer.')
        if not isinstance(record.name,str) or not record.name.strip() or len(record.name.strip()) > 120:
            raise ValidationError('Enter a service name (up to 120 characters).')
        if not isinstance(record.notes,str):
            raise ValidationError('Service notes must be text.')
        # Reuse job choice rules without requiring visit status/dates or custom questions.
        previous = previous or {}
        types = job_types(record.job_type)
        if any(v not in self.settings.job_type_options and v not in previous.get('job_type',[]) for v in types):
            raise ValidationError('Choose configured options for nature of job.')
        equipment = record.equipment
        if not isinstance(equipment,list) or any(not isinstance(v,str) or (v not in self.settings.equipment_options and v not in previous.get('equipment',[])) for v in equipment):
            raise ValidationError('Choose configured equipment.')
        return {'customer_id':record.customer_id,'name':record.name.strip(), 'job_type':json.dumps(types,ensure_ascii=False),
                'job_type_sides':json.dumps(work_sides(record.job_type_sides, types),ensure_ascii=False),
                'equipment':json.dumps(list(dict.fromkeys(record.equipment)),ensure_ascii=False),
                'fee_cents':money_to_cents(record.fee),'hours':hours_text(record.hours),'notes':record.notes.strip()}

    @staticmethod
    def _unique_service(conn, customer_id, name, service_id=None):
        if conn.execute('SELECT id FROM customer_services WHERE customer_id=? AND name=? COLLATE NOCASE AND (? IS NULL OR id<>?)',
                        (customer_id,name,service_id,service_id)).fetchone():
            raise ValidationError('This customer already has a service with that name. Choose another name or edit the existing service.')

    def create_service(self, record):
        values = self._service_values(record)
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT id FROM customers WHERE id=?',(record.customer_id,)).fetchone() is None:
                raise ValidationError('Customer not found.')
            self._unique_service(conn,record.customer_id,values['name'])
            return self._insert(conn,'customer_services',values)

    def update_service(self, service_id, record):
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            old = self._decode_service(conn.execute('SELECT * FROM customer_services WHERE id=?',(service_id,)).fetchone())
            if old is None: raise ValidationError('Service not found.')
            if old['customer_id'] != record.customer_id: raise ValidationError('A service cannot be moved to another customer.')
            values = self._service_values(record,old)
            self._unique_service(conn,record.customer_id,values['name'],service_id)
            self._update(conn,'customer_services',service_id,values)
            if old['is_default']:
                self._sync_usual_service(conn,record.customer_id,values)

    def _sync_usual_service(self, conn, customer_id, service):
        customer = self._decode(conn.execute('SELECT * FROM customers WHERE id=?',(customer_id,)).fetchone(),'customers')
        # Only change service defaults. Historical contact details and newly
        # required custom questions must not block editing a reusable service.
        values = {'default_job_type':service['job_type'], 'default_job_type_sides':service['job_type_sides'],
                  'default_equipment':service['equipment'],
                  'default_fee_cents':service['fee_cents'],'default_hours':service['hours']}
        searchable = {k:customer[k] for k in CustomerRecord.__dataclass_fields__}
        searchable.update(default_job_type=json.loads(service['job_type']),default_job_type_sides=json.loads(service['job_type_sides']),default_equipment=json.loads(service['equipment']),
                          default_fee=money_text(service['fee_cents']) or None,default_hours=service['hours'])
        values['search_text'] = _search(searchable)
        self._update(conn,'customers',customer_id,values)

    def set_usual_service(self, service_id):
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            service = conn.execute('SELECT * FROM customer_services WHERE id=?',(service_id,)).fetchone()
            if service is None or not service['active']: raise ValidationError('Choose an available service.')
            conn.execute('UPDATE customer_services SET is_default=0 WHERE customer_id=?',(service['customer_id'],))
            self._update(conn,'customer_services',service_id,{'is_default':1})
            self._sync_usual_service(conn,service['customer_id'],dict(service))

    def set_service_active(self, service_id, active):
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            service = conn.execute('SELECT * FROM customer_services WHERE id=?',(service_id,)).fetchone()
            if service is None: raise ValidationError('Service not found.')
            if service['is_default'] and not active:
                raise ValidationError('Choose another service as the usual service before archiving this one.')
            self._update(conn,'customer_services',service_id,{'active':bool(active)})

    def new_job_for_customer(self, customer_id: int, scheduled_date: str = '', *, service_id=None) -> JobRecord:
        c = self.get_customer(customer_id)
        if c is None or not c['active']: raise ValidationError('Choose an active customer for a new job.')
        services = self.list_services(customer_id)
        service = next((s for s in services if s['id'] == service_id),None) if service_id is not None else next((s for s in services if s['is_default']),None)
        if service is None: raise ValidationError('Choose an available service belonging to this customer.')
        return JobRecord(customer_id=customer_id, scheduled_date=scheduled_date,
                         job_type=[v for v in service['job_type'] if v in self.settings.job_type_options],
                         job_type_sides={k:v for k,v in service['job_type_sides'].items() if k in self.settings.job_type_options},
                         equipment=[v for v in service['equipment'] if v in self.settings.equipment_options],
                         fee=service['fee'],hours=service['hours'], notes=service['notes'],
                         service_id=service['id'],service_name=service['name'],
                         payment_type=c['default_payment_type'] if c['default_payment_type'] in self.settings.payment_type_options else '')

    @staticmethod
    def _check_job_service(conn, values, previous=None):
        sid = values['service_id']
        if sid is None:
            if values['service_name']: raise ValidationError('Choose a service for this service name.')
            return
        if not isinstance(sid,int) or isinstance(sid,bool): raise ValidationError('Choose a valid service.')
        service = conn.execute('SELECT * FROM customer_services WHERE id=?',(sid,)).fetchone()
        unchanged = previous is not None and previous['service_id'] == sid
        if service is None or service['customer_id'] != values['customer_id'] or (not service['active'] and not unchanged):
            raise ValidationError('Choose an available service belonging to this customer.')
        if not isinstance(values['service_name'],str): raise ValidationError('Service name must be text.')
        if unchanged:
            values['service_name'] = previous['service_name']
        else:
            values['service_name'] = service['name']

    def create_job(self, record: JobRecord) -> int:
        v = self._job_values(record)
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            customer = conn.execute('SELECT active FROM customers WHERE id=?',(record.customer_id,)).fetchone()
            if customer is None or not customer['active']: raise ValidationError('Choose an active customer for a new job.')
            self._check_job_service(conn,v)
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
            values = self._job_values(record,old)
            self._check_job_service(conn,values,old)
            self._update(conn,'jobs',job_id,values)

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

    def home_overview(self, today: date | None = None) -> dict[str, Any]:
        """Read a consistent seven-day overview without opening a connection per customer.

        Open visits remain visible for inactive customers. Only active customers
        can need a new booking; any future open booking suppresses that reminder.
        """
        today = today or date.today()
        start, end = today.isoformat(), (today + timedelta(days=6)).isoformat()
        with self.connect() as conn:
            conn.execute('BEGIN')
            upcoming = [self._decode(row, 'jobs') for row in conn.execute('''
                SELECT j.*,c.name AS customer_name,c.suburb
                FROM jobs j JOIN customers c ON c.id=j.customer_id
                WHERE j.deleted_at IS NULL AND j.status IN ('Scheduled','In progress')
                  AND j.scheduled_date BETWEEN ? AND ?
                ORDER BY j.scheduled_date,c.name COLLATE NOCASE,j.id
            ''', (start, end))]
            overdue = conn.execute('''SELECT COUNT(*) FROM jobs
                WHERE deleted_at IS NULL AND status IN ('Scheduled','In progress')
                AND scheduled_date<>'' AND scheduled_date<?''', (start,)).fetchone()[0]
            candidates = conn.execute('''
                SELECT c.*,MAX(CASE WHEN j.status='Completed' THEN j.completed_date END) AS last_job,
                    MAX(CASE WHEN j.status IN ('Scheduled','In progress')
                        AND j.scheduled_date>=? THEN 1 ELSE 0 END) AS booked
                FROM customers c LEFT JOIN jobs j ON j.customer_id=c.id AND j.deleted_at IS NULL
                WHERE c.active=1 GROUP BY c.id
            ''', (start,)).fetchall()
        needs_booking = []
        for row in candidates:
            if row['booked']:
                continue
            try:
                due = (add_interval(row['last_job'], row['frequency_value'], row['frequency_unit'])
                       if row['last_job'] else (row['first_service_date'] or None))
            except (ValueError, OverflowError):
                due = None
            if due and due <= end:
                needs_booking.append({**self._decode(row, 'customers'), 'next_due': due})
        needs_booking.sort(key=lambda c: (c['next_due'], c['name'].casefold(), c['id']))
        return {'as_of': start, 'today_jobs': sum(j['scheduled_date'] == start for j in upcoming),
                'next7_jobs': len(upcoming), 'upcoming': upcoming,
                'needs_booking': needs_booking, 'overdue_jobs': overdue}
