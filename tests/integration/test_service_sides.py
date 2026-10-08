"""Encrypted work scope storage, old-schema upgrades and job snapshots."""
from contextlib import closing
from dataclasses import fields
from pathlib import Path
import json
import pytest

from customer_app.models import CustomerRecord, JobRecord, ServiceRecord, ValidationError
from customer_app.database import CustomerDatabase, SCHEMA_VERSION
from customer_app.db_crypto import open_encrypted_connection
from customer_app.backup import DatabaseBackupManager
from customer_app.recovery import inspect_backup, restore_backup, file_fingerprint
from tests.conftest import KEY
from tests.integration.test_customer_workflow_storage import legacy_database
from tests.integration.test_customer_services import version_two
from tests.integration.test_multiple_job_types import version_three, record


def version_four(path):
    schema=(Path(__file__).parents[1]/'fixtures/schema_v4.sql').read_text()
    with closing(open_encrypted_connection(path,KEY,validate=False)) as conn:
        conn.executescript(schema)
        with conn:
            conn.execute("INSERT INTO customers(id,name,default_job_type,created_at,updated_at) VALUES(7,'Mary',?,'old','old')",(json.dumps(['Screens']),))
            conn.execute("INSERT INTO customer_services(id,customer_id,name,job_type,is_default,created_at,updated_at) VALUES(21,7,'Windows',?,1,'old','old')",(json.dumps(['Screens']),))
            conn.execute("INSERT INTO jobs(id,customer_id,service_id,service_name,job_type,fee_cents,hours,created_at,updated_at) VALUES(11,7,21,'Original',?,50000,'3.00','old','old')",(json.dumps(['Screens']),))
    return path


@pytest.mark.parametrize('version',[1,2,3,4])
def test_old_databases_gain_unset_sides_without_guessing_or_changing_jobs(tmp_path,version):
    path={1:legacy_database,2:version_two,3:version_three,4:version_four}[version](tmp_path/'old.db')
    db=CustomerDatabase(path,key_hex=KEY)
    assert db.get_customer(7)['default_job_type_sides']=={}
    assert db.get_job(11)['job_type_sides']=={}
    assert db.list_services(7)[0]['job_type_sides']=={}
    if version==4:
        assert (db.get_job(11)['service_name'],db.get_job(11)['fee'],db.get_job(11)['hours'],db.get_job(11)['updated_at'])==('Original','500.00','3.00','old')
    with db.connect() as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0]==SCHEMA_VERSION
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert CustomerDatabase(path,key_hex=KEY).get_job(11)['job_type_sides']=={}
    assert not path.read_bytes().startswith(b'SQLite format 3')


@pytest.mark.parametrize('version',[1,2,3,4])
def test_last_upgrade_failure_rolls_back_whole_chain(tmp_path,version):
    path={1:legacy_database,2:version_two,3:version_three,4:version_four}[version](tmp_path/'old.db')
    class Interrupted(CustomerDatabase):
        @staticmethod
        def _migrate_v4(conn):
            CustomerDatabase._migrate_v4(conn)
            raise OSError('Interrupted last migration')
    with pytest.raises(OSError):Interrupted(path,key_hex=KEY)
    with closing(open_encrypted_connection(path,KEY)) as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0]==version
        for table,column in [('customers','default_job_type_sides'),('jobs','job_type_sides'),('customer_services','job_type_sides')]:
            assert column not in {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
    assert CustomerDatabase(path,key_hex=KEY).get_job(11)


def test_sides_roundtrip_sync_usual_defaults_and_snapshot_visits(context,customer_id):
    db=context.db;types=['Internal windows','Screens'];sides={'Internal windows':'inside','Screens':'both'}
    sid=db.create_service(ServiceRecord(customer_id,'Windows',types,fee='500',hours='3',job_type_sides=sides))
    db.set_usual_service(sid)
    assert db.get_customer(customer_id)['default_job_type_sides']==sides
    jid=db.create_job(db.new_job_for_customer(customer_id))
    db.update_service(sid,record(ServiceRecord,db.get_service(sid),job_type_sides={'Internal windows':'outside','Screens':'inside'},fee='600',hours='4'))
    assert db.get_job(jid)['job_type_sides']==sides
    assert (db.get_job(jid)['fee'],db.get_job(jid)['hours'])==('500.00','3.00')
    assert db.new_job_for_customer(customer_id).job_type_sides=={'Internal windows':'outside','Screens':'inside'}
    db.update_customer(customer_id,record(CustomerRecord,db.get_customer(customer_id),default_job_type_sides={'Screens':'outside'}))
    assert db.get_service(sid)['job_type_sides']=={'Screens':'outside'}
    db.update_job(jid,record(JobRecord,db.get_job(jid),job_type_sides={'Internal windows':'both'}))
    assert db.get_service(sid)['job_type_sides']=={'Screens':'outside'}
    assert CustomerDatabase(db.db_path,context.settings,key_hex=KEY).get_job(jid)['job_type_sides']=={'Internal windows':'both'}


@pytest.mark.parametrize('sides',[None,[],True,{'Screens':'invalid'},{'Screens':['inside']},{'Unticked':'both'},{1:'inside'}])
def test_invalid_side_mapping_rejected_before_writing(context,customer_id,sides):
    db=context.db
    with pytest.raises(ValidationError):db.create_service(ServiceRecord(customer_id,'Invalid',['Screens'],job_type_sides=sides))
    with pytest.raises(ValidationError):db.create_customer(CustomerRecord(name='Invalid',default_job_type=['Screens'],default_job_type_sides=sides))
    with pytest.raises(ValidationError):db.create_job(JobRecord(customer_id,job_type=['Screens'],job_type_sides=sides))
    assert db.list_jobs(customer_id)==[] and len(db.list_services(customer_id))==1


def test_retired_choice_keeps_historic_side_but_is_filtered_from_new_visits(context,customer_id):
    db=context.db
    sid=db.create_service(ServiceRecord(customer_id,'Windows',['Internal windows','Screens'],job_type_sides={'Internal windows':'inside','Screens':'outside'}))
    jid=db.create_job(db.new_job_for_customer(customer_id,service_id=sid))
    context.settings.job_type_options.remove('Screens')
    db.update_job(jid,record(JobRecord,db.get_job(jid),notes='Preserve old scope'))
    assert db.get_job(jid)['job_type_sides']['Screens']=='outside'
    assert db.new_job_for_customer(customer_id,service_id=sid).job_type_sides=={'Internal windows':'inside'}


@pytest.mark.parametrize('version',[4,5])
def test_restore_upgrades_old_backup_and_preserves_current_sides(context,customer_id,tmp_path,version):
    path=tmp_path/'source.db'
    if version==4:
        version_four(path);jid=11;expected={}
    else:
        db=CustomerDatabase(path,key_hex=KEY)
        cid=db.create_customer(CustomerRecord(name='Saved'))
        sid=db.create_service(ServiceRecord(cid,'Windows',['Screens'],job_type_sides={'Screens':'both'}))
        jid=db.create_job(db.new_job_for_customer(cid,service_id=sid));expected={'Screens':'both'}
    fingerprint=file_fingerprint(path);info=inspect_backup(path,KEY,context.db.db_path)
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    restore_backup(manager,path,context.store,context.settings,expected_info=info)
    assert file_fingerprint(path)==fingerprint
    assert context.db.get_job(jid)['job_type_sides']==expected


def test_restore_rejects_invalid_persisted_scope_and_preserves_live_database(context,customer_id,tmp_path):
    path=tmp_path/'source.db';db=CustomerDatabase(path,key_hex=KEY)
    cid=db.create_customer(CustomerRecord(name='Saved'))
    with db.connect() as conn:conn.execute("UPDATE customer_services SET job_type_sides=?",(json.dumps({'Not selected':'inside'}),))
    original=file_fingerprint(context.db.db_path)
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    with pytest.raises(ValidationError):restore_backup(manager,path,context.store,context.settings)
    assert file_fingerprint(context.db.db_path)==original
    assert context.db.get_customer(customer_id)['name']=='Mary Window'
