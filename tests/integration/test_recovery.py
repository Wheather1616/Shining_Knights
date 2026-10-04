"""Exercise real encrypted files, rollback and recovery, including injected failures."""
from datetime import datetime, timedelta
from contextlib import closing
import os
import sqlite3
import pytest
from sqlcipher3 import dbapi2 as sqlcipher
from customer_app import backup, db_crypto
from customer_app.backup import DatabaseBackupManager
from customer_app.database import CustomerDatabase
from customer_app.db_crypto import DatabaseEncryptionError, migrate_plaintext_database, open_encrypted_connection, verify_encrypted_database
from customer_app.models import CustomerRecord, ValidationError

KEY='12'*32

def test_sqlcipher_is_enabled_and_all_integrity_checks_pass(context,customer_id):
    with context.db.connect() as conn:
        assert conn.execute('PRAGMA cipher_version').fetchone()[0]
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('PRAGMA cipher_integrity_check').fetchall()==[]
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
    with closing(sqlite3.connect(context.db.db_path)) as plain:
        with pytest.raises(sqlite3.DatabaseError): plain.execute('SELECT * FROM customers').fetchall()
    assert b'Mary Window' not in context.db.db_path.read_bytes()

def test_connection_rolls_back_partial_writes_on_error(context,customer_id):
    before=context.db.get_customer(customer_id)
    with pytest.raises(sqlcipher.IntegrityError):
        with context.db.connect() as conn:
            conn.execute('UPDATE customers SET name=? WHERE id=?',('Should roll back',customer_id))
            conn.execute("INSERT INTO jobs(customer_id,created_at,updated_at) VALUES(999,'a','a')")
    assert context.db.get_customer(customer_id)==before
    assert context.db.list_jobs()==[]

def test_invalid_customer_update_leaves_original_record_intact(context,customer_id):
    before=context.db.get_customer(customer_id)
    with pytest.raises(ValidationError): context.db.update_customer(customer_id,CustomerRecord(name='Invalid',default_fee='1.001'))
    assert context.db.get_customer(customer_id)==before

def test_backup_is_an_independent_encrypted_snapshot(context,customer_id,tmp_path):
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY)
    path=manager.create_backup()
    context.db.set_customer_active(customer_id,False)
    restored=CustomerDatabase(path,context.settings,key_hex=KEY)
    assert restored.get_customer(customer_id)['active'] is True
    assert context.db.get_customer(customer_id)['active'] is False
    with pytest.raises(DatabaseEncryptionError): verify_encrypted_database(path,'34'*32)
    verify_encrypted_database(path,KEY)

def test_failed_backup_verification_never_publishes_a_recovery_point(context,tmp_path,monkeypatch):
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY)
    def fail(*a): raise DatabaseEncryptionError('Injected verification failure')
    monkeypatch.setattr(backup,'verify_encrypted_database',fail)
    with pytest.raises(DatabaseEncryptionError): manager.create_backup()
    assert list(manager.backup_dir.iterdir())==[]
    assert context.db.dashboard()['active_customers']==0

def test_backup_creation_failure_closes_connections_and_removes_temporary_file(context,tmp_path,monkeypatch):
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY)
    real_open=backup.open_encrypted_connection
    opened=[]
    def controlled_open(path,key_hex,**kwargs):
        if str(path).endswith('.tmp'): raise OSError('Destination unavailable')
        conn=real_open(path,key_hex,**kwargs); opened.append(conn); return conn
    monkeypatch.setattr(backup,'open_encrypted_connection',controlled_open)
    with pytest.raises(OSError): manager.create_backup()
    for conn in opened:
        with pytest.raises(sqlcipher.ProgrammingError): conn.execute('SELECT 1')
    assert not list(manager.backup_dir.iterdir())

def test_missing_database_does_not_create_a_fake_backup(tmp_path):
    manager=DatabaseBackupManager(tmp_path/'missing.db',tmp_path/'backups',KEY)
    assert manager.latest_backup() is None
    with pytest.raises(FileNotFoundError): manager.create_backup()
    assert list(manager.backup_dir.iterdir())==[]

def test_backup_names_do_not_collide_in_the_same_second(context,tmp_path,monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls): return cls(2026,10,2,12)
    monkeypatch.setattr(backup,'datetime',Clock)
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY)
    first=manager.create_backup(); second=manager.create_backup()
    assert first!=second
    assert second.name.endswith('_01.db')
    verify_encrypted_database(first,KEY); verify_encrypted_database(second,KEY)

def test_backup_due_and_retention_use_snapshot_age(context,tmp_path,monkeypatch):
    now=datetime(2026,10,2,12)
    class Clock(datetime):
        @classmethod
        def now(cls): return now
    monkeypatch.setattr(backup,'datetime',Clock)
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY)
    ages=[timedelta(minutes=10),timedelta(hours=2),timedelta(days=2,hours=1),timedelta(days=2,hours=2),
          timedelta(days=40),timedelta(days=41),timedelta(days=400)]
    files=[]
    for index,age in enumerate(ages):
        path=manager.backup_dir/f'customers_fixture_{index}.db'; path.write_bytes(b'fixture')
        timestamp=(now-age).timestamp(); os.utime(path,(timestamp,timestamp)); files.append(path)
    assert manager.latest_backup()==files[0]
    assert not manager.backup_is_due()
    assert manager.create_backup_if_due() is None
    removed=manager.prune_backups()
    assert set(removed)=={files[3],files[5],files[6]}
    assert {p for p in manager.backup_dir.iterdir()}=={files[0],files[1],files[2],files[4]}
    os.utime(files[0],((now-timedelta(hours=3)).timestamp(),)*2)
    os.utime(files[1],((now-timedelta(hours=4)).timestamp(),)*2)
    assert manager.backup_is_due()

def test_plaintext_migration_failure_restores_original_file(tmp_path,monkeypatch):
    path=tmp_path/"Customer's database.db"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('CREATE TABLE customers(id INTEGER PRIMARY KEY,name TEXT)')
        conn.execute("INSERT INTO customers VALUES(1,'Historical customer')")
    before=path.read_bytes()
    real_replace=db_crypto.os.replace
    def fail_publish(source,destination):
        if str(source).endswith('.encrypted.tmp'): raise OSError('Injected publish failure')
        return real_replace(source,destination)
    monkeypatch.setattr(db_crypto.os,'replace',fail_publish)
    with pytest.raises(OSError,match='publish'): migrate_plaintext_database(path,KEY)
    assert path.read_bytes()==before
    assert not path.with_name(path.name+'.encrypted.tmp').exists()
    assert not path.with_name(path.name+'.plaintext-migration.tmp').exists()

def test_plaintext_backups_are_encrypted_and_keep_original_age(tmp_path):
    directory=tmp_path/'backups'; directory.mkdir()
    path=directory/'customers_legacy.db'
    with closing(sqlite3.connect(path)) as conn, conn: conn.execute('CREATE TABLE original(value TEXT)')
    age=datetime(2025,1,1).timestamp(); os.utime(path,(age,age))
    manager=DatabaseBackupManager(tmp_path/'source.db',directory,KEY)
    assert path.stat().st_mtime==age
    assert not db_crypto.is_plaintext_sqlite(path)
    verify_encrypted_database(path,KEY)

@pytest.mark.parametrize('key',['','abc','g'*64,'12'*31])
def test_invalid_raw_key_does_not_leave_a_connection_open(tmp_path,key,monkeypatch):
    real_connect=db_crypto.sqlcipher.connect
    connections=[]
    def track(*a,**kw):
        conn=real_connect(*a,**kw); connections.append(conn); return conn
    monkeypatch.setattr(db_crypto.sqlcipher,'connect',track)
    with pytest.raises(DatabaseEncryptionError): open_encrypted_connection(tmp_path/'invalid.db',key)
    assert not (tmp_path/'invalid.db').exists()
    for conn in connections:
        with pytest.raises(sqlcipher.ProgrammingError): conn.execute('SELECT 1')

def test_unknown_schema_version_does_not_mutate_records(context,customer_id):
    with context.db.connect() as conn: conn.execute('UPDATE crm_schema SET version=99')
    with pytest.raises(ValidationError,match='version'): CustomerDatabase(context.db.db_path,context.settings,key_hex=KEY)
    assert context.db.get_customer(customer_id)['name']=='Mary Window'

def test_job_actions_reject_unknown_and_trashed_records(context,customer_id):
    db=context.db
    for action in (db.complete_job,db.trash_job,db.restore_job,db.customer_summary):
        with pytest.raises(ValidationError): action(999)
    job=db.create_job(db.new_job_for_customer(customer_id)); db.trash_job(job)
    with pytest.raises(ValidationError): db.complete_job(job)
    with pytest.raises(ValidationError): db.trash_job(job)
    db.restore_job(job)
    with pytest.raises(ValidationError): db.restore_job(job)

def test_dashboard_boundary_dates_and_trash_exclusion(context,customer_id,today):
    from customer_app.models import JobRecord
    db=context.db
    db.create_job(JobRecord(customer_id,scheduled_date='2026-10-01'))
    db.create_job(JobRecord(customer_id,scheduled_date='2026-10-02'))
    db.create_job(JobRecord(customer_id,scheduled_date='2026-10-03',status='Cancelled'))
    db.create_job(JobRecord(customer_id,status='Completed',completed_date='2026-09-30',fee='10.00'))
    job=db.create_job(JobRecord(customer_id,status='Completed',completed_date='2026-10-01',fee='0.29'))
    assert db.dashboard()=={'active_customers':1,'upcoming_jobs':2,'overdue_jobs':1,'completed_month_cents':29}
    db.trash_job(job)
    assert db.dashboard()['completed_month_cents']==0
