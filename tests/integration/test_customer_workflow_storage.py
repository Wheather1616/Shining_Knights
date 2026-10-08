"""Split names, hours snapshots and migration/recovery against real encrypted files."""
from contextlib import closing
from dataclasses import fields
from pathlib import Path

import pytest

from customer_app.backup import DatabaseBackupManager
from customer_app.config import AppSettings, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.db_crypto import open_encrypted_connection, verify_encrypted_database
from customer_app.models import CustomerRecord, JobRecord, ValidationError
from customer_app.recovery import inspect_backup, restore_backup, file_fingerprint
from tests.conftest import KEY


def legacy_database(path):
    schema = (Path(__file__).parents[1] / 'fixtures/schema_v1.sql').read_text()
    with closing(open_encrypted_connection(path, KEY, validate=False)) as conn:
        conn.executescript(schema)
        with conn:
            conn.execute("INSERT INTO customers(id,name,phone,frequency_value,frequency_unit,custom_fields,search_text,created_at,updated_at) VALUES(7,?,?,?,?,?,?,?,?)",
                         ('William James Heather', '0457 516 182', 1, 'months', '{"gate_code":"0042"}', 'william james heather 0457516182', 'created', 'updated'))
            conn.execute("INSERT INTO jobs(id,customer_id,status,completed_date,fee_cents,created_at,updated_at) VALUES(11,7,'Completed','2026-10-02',15000,'created','updated')")
            conn.execute('CREATE TABLE receipts(id INTEGER PRIMARY KEY, notes TEXT)')
            conn.execute("INSERT INTO receipts VALUES(1,'Keep inherited records')")
    return path


def test_additive_migration_preserves_names_ids_links_receipts_and_encryption(tmp_path):
    path = legacy_database(tmp_path / 'customers.db')
    db = CustomerDatabase(path, key_hex=KEY)
    customer = db.get_customer(7)
    assert customer['name'] == 'William James Heather'
    assert customer['first_name'] == customer['last_name'] == ''  # No surname guesses.
    assert customer['default_hours'] is None
    assert customer['custom_fields'] == {'gate_code': '0042'}
    assert db.get_job(11)['customer_id'] == 7 and db.get_job(11)['hours'] is None
    assert db.get_job(11)['fee_cents'] == 15000
    assert db.customer_summary(7)['next_due'] == '2026-11-02'
    assert db.list_customers('Heather')[0]['id'] == 7
    with db.connect() as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0] == 4
        assert conn.execute('SELECT notes FROM receipts').fetchone()[0] == 'Keep inherited records'
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    assert not path.read_bytes().startswith(b'SQLite format 3')
    verify_encrypted_database(path, KEY)
    reopened = CustomerDatabase(path, key_hex=KEY)
    assert reopened.get_customer(7) == customer


def test_migration_failure_rolls_back_every_column_and_version(tmp_path):
    path = legacy_database(tmp_path / 'customers.db')
    class InterruptedDatabase(CustomerDatabase):
        @staticmethod
        def _migrate_v1(conn):
            conn.execute('BEGIN IMMEDIATE')
            conn.execute("ALTER TABLE customers ADD COLUMN first_name TEXT NOT NULL DEFAULT ''")
            raise OSError('Injected migration interruption')
    with pytest.raises(OSError):
        InterruptedDatabase(path, key_hex=KEY)
    with closing(open_encrypted_connection(path, KEY)) as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0] == 1
        assert 'first_name' not in {r[1] for r in conn.execute('PRAGMA table_info(customers)')}
        assert conn.execute('SELECT customer_id FROM jobs WHERE id=11').fetchone()[0] == 7
    assert CustomerDatabase(path, key_hex=KEY).get_customer(7)['name'] == 'William James Heather'


def test_old_backup_is_inspected_without_changes_and_upgraded_only_when_staged(context, tmp_path):
    old = legacy_database(tmp_path / 'old-backup.db')
    original = file_fingerprint(old)
    info = inspect_backup(old, KEY, context.db.db_path)
    assert info['customers'] == info['jobs'] == 1
    assert file_fingerprint(old) == original
    later = context.db.create_customer(CustomerRecord(first_name='Later', last_name='Customer'))
    manager = DatabaseBackupManager(context.db.db_path, tmp_path / 'backups', KEY, settings_store=context.store)
    _, safety, _ = restore_backup(manager, old, context.store, context.settings, expected_info=info)
    assert context.db.get_customer(later) is None
    assert context.db.get_customer(7)['name'] == 'William James Heather'
    assert context.db.get_job(11)['customer_id'] == 7
    assert CustomerDatabase(safety, key_hex=KEY).get_customer(later)['name'] == 'Later Customer'
    with context.db.connect() as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0] == 4
    assert file_fingerprint(old) == original


def test_missing_columns_in_legacy_backup_are_rejected_before_restore(context, tmp_path):
    path = legacy_database(tmp_path / 'incomplete.db')
    with closing(open_encrypted_connection(path, KEY)) as conn:
        with conn:
            conn.execute('ALTER TABLE customers DROP COLUMN email')
    before = context.db.db_path.read_bytes()
    with pytest.raises(ValueError, match='required'):
        inspect_backup(path, KEY, context.db.db_path)
    assert context.db.db_path.read_bytes() == before


def record_from(cls, saved, **changes):
    return cls(**{**{f.name: saved[f.name] for f in fields(cls)}, **changes})


def test_names_are_searchable_and_customer_ids_keep_jobs_linked(context):
    db = context.db
    cid = db.create_customer(CustomerRecord(first_name='Mary Jane', last_name='van Dijk'))
    other = db.create_customer(CustomerRecord(first_name='Mary Jane', last_name='van Dijk', suburb='Bondi'))
    jid = db.create_job(JobRecord(cid))
    assert db.get_customer(cid)['name'] == 'Mary Jane van Dijk'
    assert {c['id'] for c in db.list_customers('van Dijk Mary')} == {cid, other}
    db.update_customer(cid, record_from(CustomerRecord, db.get_customer(cid), last_name='Brown'))
    assert db.get_customer(cid)['name'] == 'Mary Jane Brown'
    assert db.get_job(jid)['customer_id'] == cid
    assert db.list_jobs()[0]['customer_name'] == 'Mary Jane Brown'
    assert [c['id'] for c in db.list_customers('Brown')] == [cid]
    db.update_customer(cid, record_from(CustomerRecord, db.get_customer(cid), name='Legacy API rename'))
    assert db.get_customer(cid)['name'] == 'Legacy API rename'
    assert db.get_customer(cid)['first_name'] == ''


def test_hours_are_optional_exact_and_snapshot_into_new_jobs(context):
    db = context.db
    cid = db.create_customer(CustomerRecord(first_name='Prince', default_fee='150', default_hours='1.5'))
    jid = db.create_job(db.new_job_for_customer(cid))
    assert db.get_job(jid)['hours'] == '1.50'
    assert db.get_job(jid)['fee'] == '150.00'
    db.update_customer(cid, record_from(CustomerRecord, db.get_customer(cid), default_hours='2.25', default_fee='180'))
    assert db.get_job(jid)['hours'] == '1.50' and db.get_job(jid)['fee'] == '150.00'
    assert db.new_job_for_customer(cid).hours == '2.25'
    zero = db.create_customer(CustomerRecord(first_name='Zero', default_hours='0'))
    assert db.get_customer(zero)['default_hours'] == '0.00'
    assert db.get_job(db.create_job(JobRecord(zero)))['hours'] is None


@pytest.mark.parametrize('value', ['-1', '1.001', 'NaN', 'Infinity', '10000', True, 'letters'])
def test_invalid_hours_are_rejected_in_customer_and_job_records(context, customer_id, value):
    with pytest.raises(ValidationError):
        context.db.create_customer(CustomerRecord(name='Invalid', default_hours=value))
    with pytest.raises(ValidationError):
        context.db.create_job(JobRecord(customer_id, hours=value))


@pytest.mark.parametrize('phone', ['123456789', '1234567890123456', 'abc1234567890'])
def test_phone_length_and_characters_are_checked_in_the_database(context, phone):
    with pytest.raises(ValidationError, match='phone'):
        context.db.create_customer(CustomerRecord(name='Phone', phone=phone))


def test_v1_settings_gain_new_fields_without_losing_customisation(tmp_path):
    settings = AppSettings(db_path=tmp_path / 'customers.db')
    old = settings.to_dict()
    old['customer_fields'] = [f for f in old['customer_fields'] if f['key'] not in ('first_name', 'last_name', 'default_hours')]
    old['job_fields'] = [f for f in old['job_fields'] if f['key'] != 'hours']
    old['customer_fields'][0]['label'] = 'Our customer'
    loaded = AppSettings.from_dict(old)
    assert loaded.customer_fields[0].label == 'Our customer'
    assert {'first_name', 'last_name', 'default_hours'} <= {f.key for f in loaded.customer_fields}
    assert 'hours' in {f.key for f in loaded.job_fields}
    store = SettingsStore(tmp_path / 'settings.json')
    store.save(loaded)
    assert store.load() == loaded
