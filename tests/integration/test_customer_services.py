"""Encrypted service relationships, snapshots, migration and recovery contracts."""
from contextlib import closing
from dataclasses import fields
from pathlib import Path

import pytest

from customer_app.backup import DatabaseBackupManager
from customer_app.database import CustomerDatabase, SCHEMA_VERSION
from customer_app.db_crypto import open_encrypted_connection
from customer_app.models import CustomerRecord, JobRecord, ServiceRecord, ValidationError
from customer_app.recovery import inspect_backup, restore_backup, file_fingerprint
from tests.conftest import KEY
from tests.integration.test_customer_workflow_storage import legacy_database


def record(cls, saved, **changes):
    return cls(**{**{f.name:saved[f.name] for f in fields(cls)}, **changes})


def version_two(path):
    schema = (Path(__file__).parents[1]/'fixtures/schema_v2.sql').read_text()
    with closing(open_encrypted_connection(path,KEY,validate=False)) as conn:
        conn.executescript(schema)
        with conn:
            conn.execute("""INSERT INTO customers(id,name,first_name,last_name,default_hours,default_fee_cents,
                default_job_type,default_equipment,created_at,updated_at) VALUES
                (7,'Mary Brown','Mary','Brown','3.00',50000,'Internal windows','["3m ladder"]','old','old')""")
            conn.execute("INSERT INTO jobs(id,customer_id,fee_cents,hours,created_at,updated_at) VALUES(11,7,45000,'2.50','old','old')")
    return path


def test_v2_upgrade_copies_usual_service_without_rewriting_old_jobs(tmp_path):
    path = version_two(tmp_path/'v2.db'); db=CustomerDatabase(path,key_hex=KEY)
    service, = db.list_services(7)
    assert (service['name'],service['fee'],service['hours'],service['equipment'],service['is_default']) == ('Usual service','500.00','3.00',['3m ladder'],True)
    assert (db.get_job(11)['service_id'],db.get_job(11)['service_name'],db.get_job(11)['fee'],db.get_job(11)['hours']) == (None,'','450.00','2.50')
    new=db.new_job_for_customer(7)
    assert new.service_id==service['id'] and new.fee=='500.00'
    reopened=CustomerDatabase(path,key_hex=KEY)
    assert reopened.list_services(7)==[service]
    with db.connect() as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0]==SCHEMA_VERSION
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert not path.read_bytes().startswith(b'SQLite format 3')


@pytest.mark.parametrize('version',[1,2])
def test_interrupted_upgrade_rolls_back_entire_chain(tmp_path,version):
    path=(legacy_database if version==1 else version_two)(tmp_path/'legacy.db')
    class Interrupted(CustomerDatabase):
        @staticmethod
        def _migrate_v2(conn):
            CustomerDatabase._migrate_v2(conn)
            raise OSError('Interrupted after all migration writes')
    with pytest.raises(OSError):Interrupted(path,key_hex=KEY)
    with closing(open_encrypted_connection(path,KEY)) as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0]==version
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name='customer_services'").fetchone()
        assert 'service_id' not in {r[1] for r in conn.execute('PRAGMA table_info(jobs)')}
        if version==1:assert 'first_name' not in {r[1] for r in conn.execute('PRAGMA table_info(customers)')}
    assert len(CustomerDatabase(path,key_hex=KEY).list_services(7))==1


def test_two_services_independent_prices_and_historical_snapshots(context,customer_id):
    db=context.db
    indoor=db.create_service(ServiceRecord(customer_id,'Indoor windows','Internal windows',['3m ladder'],'500','3',notes='Inside only'))
    whole=db.create_service(ServiceRecord(customer_id,'Whole house','Internal + external',['Water-fed pole'],'600','4'))
    first=db.create_job(db.new_job_for_customer(customer_id,service_id=indoor))
    second=db.create_job(db.new_job_for_customer(customer_id,service_id=whole))
    assert [(j['service_name'],j['fee'],j['hours']) for j in db.list_jobs(customer_id)]==[('Indoor windows','500.00','3.00'),('Whole house','600.00','4.00')]
    db.update_service(indoor,record(ServiceRecord,db.get_service(indoor),name='Indoor windows only',fee='550',hours='3.5'))
    db.set_service_active(indoor,False)
    old=db.get_job(first)
    assert (old['service_name'],old['fee'],old['hours'],old['notes'])==('Indoor windows','500.00','3.00','Inside only')
    db.update_job(first,record(JobRecord,old,payment_status='Paid'))
    assert db.get_job(first)['service_name']=='Indoor windows'
    assert db.get_job(second)['fee']=='600.00'
    with pytest.raises(ValidationError,match='available'):db.new_job_for_customer(customer_id,service_id=indoor)
    db.set_service_active(indoor,True)
    assert db.new_job_for_customer(customer_id,service_id=indoor).fee=='550.00'
    # Changing the profile does not remove the association from historical queries.
    assert db.list_jobs(search='Indoor windows')[0]['id']==first


def test_service_must_belong_to_job_customer(context,customer_id):
    db=context.db; other=db.create_customer(CustomerRecord(name='Other'))
    wrong=db.list_services(other)[0]['id']
    with pytest.raises(ValidationError,match='belonging'):db.new_job_for_customer(customer_id,service_id=wrong)
    with pytest.raises(ValidationError,match='belonging'):db.create_job(JobRecord(customer_id,service_id=wrong))
    jid=db.create_job(db.new_job_for_customer(customer_id))
    with pytest.raises(ValidationError,match='belonging'):db.update_job(jid,record(JobRecord,db.get_job(jid),service_id=wrong))
    sid=db.list_services(customer_id)[0]['id']
    with pytest.raises(ValidationError,match='moved'):db.update_service(sid,ServiceRecord(other,'Wrong'))
    assert db.get_service(sid)['customer_id']==customer_id
    assert len(db.list_jobs(customer_id))==1


def test_usual_service_and_customer_defaults_stay_in_sync(context,customer_id):
    db=context.db; old=db.list_services(customer_id)[0]['id']
    whole=db.create_service(ServiceRecord(customer_id,'Whole house','Internal + external',['Water-fed pole'],'600','4'))
    db.set_usual_service(whole)
    assert db.new_job_for_customer(customer_id).service_id==whole
    assert db.get_customer(customer_id)['default_fee']=='600.00'
    db.update_customer(customer_id,record(CustomerRecord,db.get_customer(customer_id),default_fee='650',default_hours='4.5'))
    assert db.get_service(whole)['fee']=='650.00' and db.get_service(old)['fee']=='180.00'
    db.update_service(whole,record(ServiceRecord,db.get_service(whole),fee='700'))
    assert db.get_customer(customer_id)['default_fee']=='700.00'
    with pytest.raises(ValidationError,match='usual'):db.set_service_active(whole,False)
    db.set_service_active(old,False)
    with pytest.raises(ValidationError,match='available'):db.set_usual_service(old)
    assert len([s for s in db.list_services(customer_id) if s['is_default']])==1


@pytest.mark.parametrize('changes',[
    {'name':''},{'name':' '*4},{'name':'x'*121},{'name':12},{'job_type':'Invalid'},
    {'equipment':['Invalid']},{'equipment':'3m ladder'},{'fee':'-1'},{'fee':'1.001'},
    {'hours':'-1'},{'hours':'3.001'},{'hours':'NaN'},{'hours':True},{'notes':12},
    {'customer_id':False}])
def test_invalid_service_cannot_be_saved(context,customer_id,changes):
    before=context.db.list_services(customer_id,include_archived=True)
    with pytest.raises(ValidationError):context.db.create_service(ServiceRecord(**{'customer_id':customer_id,'name':'Test',**changes}))
    assert context.db.list_services(customer_id,include_archived=True)==before


def test_unique_names_scoped_to_customer_and_archives(context,customer_id):
    db=context.db; other=db.create_customer(CustomerRecord(name='Other'))
    sid=db.create_service(ServiceRecord(customer_id,'Indoor windows'))
    db.set_service_active(sid,False)
    with pytest.raises(ValidationError,match='already'):db.create_service(ServiceRecord(customer_id,'INDOOR WINDOWS'))
    db.create_service(ServiceRecord(other,'Indoor windows'))
    usual=db.list_services(customer_id)[0]
    with pytest.raises(ValidationError,match='already'):db.update_service(usual['id'],ServiceRecord(customer_id,'Indoor windows'))
    assert db.get_service(usual['id'])['name']=='Usual service'
    with pytest.raises(ValidationError,match='not found'):db.create_service(ServiceRecord(99999,'No customer'))


@pytest.mark.parametrize('version',[2,3])
def test_service_backup_restore_supports_old_and_current_data(context,customer_id,tmp_path,version):
    db=context.db; source=tmp_path/'source.db'
    if version==2:version_two(source)
    else:
        candidate=CustomerDatabase(source,key_hex=KEY)
        cid=candidate.create_customer(CustomerRecord(name='Backup customer'))
        sid=candidate.create_service(ServiceRecord(cid,'Whole house',fee='600',hours='4'))
        candidate.create_job(candidate.new_job_for_customer(cid,service_id=sid))
    before=file_fingerprint(source);info=inspect_backup(source,KEY,db.db_path)
    manager=DatabaseBackupManager(db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    _,safety,_=restore_backup(manager,source,context.store,context.settings,expected_info=info)
    assert file_fingerprint(source)==before
    assert CustomerDatabase(safety,context.settings,key_hex=KEY).get_customer(customer_id)
    cid=7 if version==2 else cid
    assert len(db.list_services(cid))==(1 if version==2 else 2)
    if version==3:assert db.list_jobs(cid)[0]['service_name']=='Whole house'


def test_backup_missing_service_table_or_cross_customer_link_rejected(context,customer_id,tmp_path):
    path=tmp_path/'broken.db';db=CustomerDatabase(path,key_hex=KEY)
    a=db.create_customer(CustomerRecord(name='A'));b=db.create_customer(CustomerRecord(name='B'))
    job=db.create_job(db.new_job_for_customer(a));sid=db.list_services(b)[0]['id']
    with db.connect() as conn:conn.execute('UPDATE jobs SET service_id=? WHERE id=?',(sid,job))
    with pytest.raises(ValueError,match='links'):inspect_backup(path,KEY,context.db.db_path)
    with db.connect() as conn:
        conn.execute('UPDATE jobs SET service_id=NULL')
        conn.execute('DROP TABLE customer_services')
    with pytest.raises(ValueError,match='services'):inspect_backup(path,KEY,context.db.db_path)


def test_service_edit_does_not_revalidate_unrelated_historical_contact_details(context,customer_id):
    db=context.db;usual=db.list_services(customer_id)[0]
    with db.connect() as conn:conn.execute("UPDATE customers SET phone='123' WHERE id=?",(customer_id,))
    db.update_service(usual['id'],record(ServiceRecord,usual,fee='500',hours='3'))
    assert db.get_customer(customer_id)['phone']=='123'
    assert db.get_customer(customer_id)['default_fee']=='500.00'
    assert db.list_customers('500.00')[0]['id']==customer_id


def test_corrupt_service_details_cannot_replace_live_records(context,customer_id,tmp_path):
    source=tmp_path/'bad-services.db';candidate=CustomerDatabase(source,key_hex=KEY)
    cid=candidate.create_customer(CustomerRecord(name='Backup customer'))
    with candidate.connect() as conn:conn.execute("UPDATE customer_services SET equipment='invalid json'")
    before=file_fingerprint(context.db.db_path)
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    with pytest.raises(ValueError):restore_backup(manager,source,context.store,context.settings)
    assert file_fingerprint(context.db.db_path)==before
    assert context.db.get_customer(customer_id)['name']=='Mary Window'
