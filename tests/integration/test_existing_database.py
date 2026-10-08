from dataclasses import fields
from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3

import pytest
from sqlcipher3 import dbapi2 as sqlcipher

from customer_app.backup import DatabaseBackupManager
from customer_app.config import AppSettings, FieldDefinition, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.db_crypto import DatabaseEncryptionError, open_encrypted_connection
from customer_app.models import CustomerRecord, JobRecord, ValidationError, add_interval, money_to_cents

KEY = '12' * 32

@pytest.fixture
def db(tmp_path):
    return CustomerDatabase(tmp_path/'customers.db',key_hex=KEY)

def customer(db, **kwargs):
    return db.create_customer(CustomerRecord(name='Jane Smith',phone='0412 345 678',address_line_1='22 Beach Street',suburb='Coogee',state='NSW',postcode='2034',
        frequency_value=8,frequency_unit='weeks',default_job_type='External windows',default_equipment=['6m ladder'],default_fee='180.00',default_payment_type='Bank transfer',**kwargs))

def record(cls,row):
    return cls(**{f.name:row[f.name] for f in fields(cls)})

def test_relationship_is_enforced_on_every_connection(db):
    with db.connect() as conn:
        assert conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1
        with pytest.raises(sqlcipher.IntegrityError):
            conn.execute("INSERT INTO jobs(customer_id,created_at,updated_at) VALUES(999,'a','a')")
    c=customer(db)
    db.create_job(db.new_job_for_customer(c))
    with db.connect() as conn:
        with pytest.raises(sqlcipher.IntegrityError): conn.execute('DELETE FROM customers WHERE id=?',(c,))


def test_snapshot_and_derived_counts(db):
    c=customer(db)
    job=db.new_job_for_customer(c,'2026-09-18')
    job.status='Completed'; job.completed_date='2026-09-18'
    j=db.create_job(job)
    updated=record(CustomerRecord,db.get_customer(c))
    updated.default_fee='210.00'; updated.default_equipment=['Water-fed pole']; updated.default_job_type='Screens'
    db.update_customer(c,updated)
    saved=db.get_job(j)
    assert saved['fee_cents'] == 18000
    assert saved['equipment'] == ['6m ladder']
    assert saved['job_type'] == ['External windows']
    assert db.new_job_for_customer(c).fee == '210.00'
    s=db.customer_summary(c)
    assert s == {'jobs_completed':1,'last_job':'2026-09-18','next_due':'2026-11-13','next_scheduled':None}
    db.trash_job(j)
    assert db.customer_summary(c)['jobs_completed'] == 0
    assert db.list_jobs(c) == []
    db.restore_job(j)
    assert db.customer_summary(c)['jobs_completed'] == 1

@pytest.mark.parametrize('value',['-1','NaN','Infinity','1.001','garbage'])
def test_invalid_money_rejected(db,value):
    with pytest.raises(ValidationError): db.create_customer(CustomerRecord(name='A',default_fee=value))


def test_money_exact(db):
    assert money_to_cents('0.29') == 29
    assert money_to_cents('$1,234.56') == 123456
    c=db.create_customer(CustomerRecord(name='Zero fee',default_fee='0'))
    assert db.get_customer(c)['default_fee'] == '0.00'

@pytest.mark.parametrize('kwargs',[{'name':''},{'email':'x@@y'},{'postcode':'203'},{'phone':'ab'},{'frequency_value':8},
    {'frequency_unit':'months'},{'frequency_value':1.5,'frequency_unit':'months'},{'frequency_value':0,'frequency_unit':'weeks'},
    {'frequency_value':True,'frequency_unit':'weeks'},{'first_service_date':'2026-02-30'},{'first_service_date':'20260918'}])
def test_customer_validation(db,kwargs):
    with pytest.raises(ValidationError): db.create_customer(CustomerRecord(**{'name':'A',**kwargs}))


def test_job_status_and_dates(db):
    c=customer(db)
    for kwargs in [{'status':'Completed'},{'status':'Scheduled','completed_date':'2026-09-18'},
        {'status':'Completed','completed_date':'9999-01-01'},{'scheduled_date':'2026-02-30'}, {'payment_status':'Nonsense'}]:
        with pytest.raises(ValidationError): db.create_job(JobRecord(customer_id=c,**kwargs))
    with pytest.raises(ValidationError): db.create_job(JobRecord(customer_id=999))
    j=db.create_job(db.new_job_for_customer(c))
    db.complete_job(j,'2026-09-18')
    assert db.get_job(j)['status'] == 'Completed'
    other=db.create_customer(CustomerRecord(name='Other'))
    edited=record(JobRecord,db.get_job(j)); edited.customer_id=other
    with pytest.raises(ValidationError): db.update_job(j,edited)


def test_archiving_preserves_history_and_blocks_new_jobs(db):
    c=customer(db)
    j=db.create_job(db.new_job_for_customer(c))
    db.set_customer_active(c,False)
    assert not db.list_customers()
    assert db.list_customers(include_inactive=True)[0]['id'] == c
    assert db.get_job(j)['customer_id'] == c
    with pytest.raises(ValidationError): db.new_job_for_customer(c)
    with pytest.raises(ValidationError): db.create_job(JobRecord(c))
    db.set_customer_active(c,True)
    assert db.list_customers()[0]['id'] == c


def test_search_and_customer_grouping(db):
    c=customer(db)
    other=db.create_customer(CustomerRecord(name='Jane Smith',suburb='Randwick'))
    db.create_job(db.new_job_for_customer(c)); db.create_job(db.new_job_for_customer(other))
    assert db.list_customers('0412345678')[0]['id'] == c
    assert db.list_customers('Beach Street')[0]['id'] == c
    assert db.list_customers('Jane Coogee')[0]['id'] == c
    assert db.list_customers('%') == []
    assert len(db.list_jobs(group_by='customer')) == 2
    assert len(db.list_jobs(c)) == 1
    assert db.list_jobs(search='Randwick')[0]['customer_id'] == other
    with pytest.raises(ValidationError): db.list_jobs(group_by='bad')

@pytest.mark.parametrize('anchor,value,unit,expected',[
    ('2026-01-31',1,'months','2026-02-28'),('2024-02-29',1,'years','2025-02-28'),
    ('2026-09-18',8,'weeks','2026-11-13'),('2026-10-02',6,'months','2027-04-02'),
    ('2026-10-02',1,'days','2026-10-03')])
def test_calendar_recurrence(anchor,value,unit,expected):
    assert add_interval(anchor,value,unit) == expected


def test_first_visit_anchor_and_scheduled_separate(db):
    c=customer(db,first_service_date='2026-10-10')
    assert db.customer_summary(c)['next_due'] == '2026-10-10'
    db.create_job(db.new_job_for_customer(c,'2026-10-12'))
    summary=db.customer_summary(c)
    assert summary['next_due'] == '2026-10-10'
    assert summary['next_scheduled'] == '2026-10-12'


def test_configuration_and_custom_fields_roundtrip(db,tmp_path):
    db.settings.customer_fields.extend([
        FieldDefinition('gate_code','Gate code',required=True,browse_column=True),
        FieldDefinition('site_flags','Site flags','multiselect',options=['Dog','Gate']),
    ])
    with pytest.raises(ValidationError): db.create_customer(CustomerRecord(name='A'))
    c=customer(db,custom_fields={'gate_code':'0042','site_flags':['Dog']})
    db.settings.customer_fields[-2].enabled=False
    db.settings.customer_fields[-2].required=False
    changed=record(CustomerRecord,db.get_customer(c)); changed.name='Jane Updated'
    db.update_customer(c,changed)
    assert db.get_customer(c)['custom_fields']['gate_code'] == '0042'
    store=SettingsStore(tmp_path/'settings.json'); store.save(db.settings)
    loaded=store.load()
    assert loaded.customer_fields[-2].key == 'gate_code'
    assert not loaded.customer_fields[-2].enabled
    # Loading defaults produces independent lists, with no leaking between settings.
    a=AppSettings(); b=AppSettings(); a.customer_fields[0].label='Changed'
    assert b.customer_fields[0].label == 'Client name'


def test_retired_choices_preserve_existing_records(db):
    c=customer(db); j=db.create_job(db.new_job_for_customer(c))
    db.settings.equipment_options.remove('6m ladder')
    db.settings.job_type_options.remove('External windows')
    changed=record(CustomerRecord,db.get_customer(c)); changed.notes='Updated'
    db.update_customer(c,changed)
    changed_job=record(JobRecord,db.get_job(j)); changed_job.notes='Historical'
    db.update_job(j,changed_job)
    assert db.get_job(j)['equipment'] == ['6m ladder']
    with pytest.raises(ValidationError): db.create_customer(CustomerRecord(name='B',default_equipment=['6m ladder']))


def test_bad_config_preserved(tmp_path):
    path=tmp_path/'settings.json'; path.write_text('{bad')
    with pytest.raises(ValueError): SettingsStore(path).load()
    assert path.read_text() == '{bad'
    settings=AppSettings(); settings.customer_fields[0].required=False
    with pytest.raises(ValueError): settings.validate()


def test_database_reopen_and_encryption(db):
    c=customer(db)
    assert db.db_path.read_bytes()[:16] != b'SQLite format 3\0'
    reopened=CustomerDatabase(db.db_path,key_hex=KEY)
    assert reopened.get_customer(c)['name'] == 'Jane Smith'
    with pytest.raises(DatabaseEncryptionError): CustomerDatabase(db.db_path,key_hex='34'*32)
    assert db.get_customer(c)['name'] == 'Jane Smith'


def test_encrypted_backup(db,tmp_path):
    c=customer(db); db.create_job(db.new_job_for_customer(c))
    manager=DatabaseBackupManager(db.db_path,tmp_path/'backups',KEY)
    path=manager.create_backup()
    assert path.name.startswith('customers_')
    assert path.read_bytes()[:16] != b'SQLite format 3\0'
    backup=CustomerDatabase(path,key_hex=KEY)
    assert backup.get_customer(c)['name'] == 'Jane Smith'
    assert len(backup.list_jobs(c)) == 1


def test_plaintext_upgrade_and_receipt_data_preserved(tmp_path):
    path=tmp_path/'old.db'
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('CREATE TABLE receipts(id INTEGER PRIMARY KEY,name TEXT)')
        conn.execute("INSERT INTO receipts VALUES(1,'Historical receipt')")
    db=CustomerDatabase(path,key_hex=KEY)
    with db.connect() as conn: assert conn.execute('SELECT name FROM receipts').fetchone()[0] == 'Historical receipt'
    assert db.list_customers() == []
    assert path.read_bytes()[:16] != b'SQLite format 3\0'


def test_foreign_customer_schema_refused(tmp_path):
    path=tmp_path/'foreign.db'
    conn=open_encrypted_connection(path,KEY)
    conn.execute('CREATE TABLE customers(id INTEGER PRIMARY KEY, company TEXT)'); conn.commit(); conn.close()
    with pytest.raises(ValidationError): CustomerDatabase(path,key_hex=KEY)
    conn=open_encrypted_connection(path,KEY)
    assert [r[1] for r in conn.execute('PRAGMA table_info(customers)')] == ['id','company']
    conn.close()
