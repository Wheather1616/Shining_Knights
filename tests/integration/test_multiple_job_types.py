"""List-valued work types, encrypted migrations and immutable visit snapshots."""
from contextlib import closing
from dataclasses import fields
from pathlib import Path

import pytest

from customer_app.backup import DatabaseBackupManager
from customer_app.config import AppSettings, FieldDefinition
from customer_app.database import CustomerDatabase, SCHEMA_VERSION
from customer_app.db_crypto import open_encrypted_connection
from customer_app.models import CustomerRecord, JobRecord, ServiceRecord, ValidationError
from customer_app.recovery import inspect_backup, restore_backup, file_fingerprint
from tests.conftest import KEY
from tests.integration.test_customer_workflow_storage import legacy_database
from tests.integration.test_customer_services import version_two


def record(cls, saved, **changes):
    return cls(**{**{f.name:saved[f.name] for f in fields(cls)},**changes})


def version_three(path, job_type='Internal windows'):
    schema=(Path(__file__).parents[1]/'fixtures/schema_v3.sql').read_text()
    with closing(open_encrypted_connection(path,KEY,validate=False)) as conn:
        conn.executescript(schema)
        with conn:
            conn.execute("""INSERT INTO customers(id,name,default_job_type,default_fee_cents,default_hours,created_at,updated_at)
                VALUES(7,'Mary Brown',?,50000,'3.00','created','updated')""",(job_type,))
            conn.execute("""INSERT INTO customer_services(id,customer_id,name,job_type,fee_cents,hours,is_default,created_at,updated_at)
                VALUES(21,7,'Indoor windows',?,50000,'3.00',1,'created','updated')""",(job_type,))
            conn.execute("""INSERT INTO jobs(id,customer_id,service_id,service_name,job_type,fee_cents,hours,created_at,updated_at)
                VALUES(11,7,21,'Original indoor name',?,45000,'2.50','created','updated')""",(job_type,))
    return path


@pytest.mark.parametrize('choice',['Internal windows','', 'Windows, screens', '["Windows"]'])
def test_v3_migration_preserves_whole_option_and_job_snapshot(tmp_path,choice):
    path=version_three(tmp_path/'legacy.db',choice)
    db=CustomerDatabase(path,key_hex=KEY);expected=[choice] if choice else []
    assert db.get_customer(7)['default_job_type']==expected
    assert db.get_service(21)['job_type']==expected
    job=db.get_job(11)
    assert job['job_type']==expected and job['service_id']==21
    assert (job['service_name'],job['fee'],job['hours'],job['updated_at'])==('Original indoor name','450.00','2.50','updated')
    with db.connect() as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0]==SCHEMA_VERSION
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert not path.read_bytes().startswith(b'SQLite format 3')
    assert CustomerDatabase(path,key_hex=KEY).get_job(11)==job


@pytest.mark.parametrize('version',[1,2,3])
def test_interruption_rolls_back_all_upgrade_steps(tmp_path,version):
    factory={1:legacy_database,2:version_two,3:version_three}[version]
    path=factory(tmp_path/'legacy.db')
    class Interrupted(CustomerDatabase):
        @staticmethod
        def _migrate_v3(conn):
            CustomerDatabase._migrate_v3(conn)
            raise OSError('Injected interruption at last upgrade step')
    with pytest.raises(OSError):Interrupted(path,key_hex=KEY)
    with closing(open_encrypted_connection(path,KEY)) as conn:
        assert conn.execute('SELECT version FROM crm_schema').fetchone()[0]==version
        if version<3:assert not conn.execute("SELECT name FROM sqlite_master WHERE name='customer_services'").fetchone()
        if version==3:assert conn.execute('SELECT job_type FROM jobs').fetchone()[0]=='Internal windows'
        if version==1:assert 'first_name' not in {r[1] for r in conn.execute('PRAGMA table_info(customers)')}
    assert CustomerDatabase(path,key_hex=KEY).get_job(11)


def test_multiple_types_roundtrip_defaults_selection_search_and_snapshots(context,customer_id):
    db=context.db;types=['Internal windows','Screens','Internal windows']
    sid=db.create_service(ServiceRecord(customer_id,'Inside and screens',types,fee='500',hours='3'))
    assert db.get_service(sid)['job_type']==['Internal windows','Screens']
    db.set_usual_service(sid)
    assert db.get_customer(customer_id)['default_job_type']==['Internal windows','Screens']
    jid=db.create_job(db.new_job_for_customer(customer_id,service_id=sid))
    db.update_service(sid,record(ServiceRecord,db.get_service(sid),job_type=['External windows']))
    assert db.get_job(jid)['job_type']==['Internal windows','Screens']
    assert db.list_jobs(search='screens')[0]['id']==jid
    assert db.new_job_for_customer(customer_id).job_type==['External windows']
    c=db.get_customer(customer_id)
    db.update_customer(customer_id,record(CustomerRecord,c,default_job_type=['Skylights','Screens']))
    assert db.get_service(sid)['job_type']==['Skylights','Screens']
    db.update_job(jid,record(JobRecord,db.get_job(jid),job_type=['Screens']))
    assert db.get_job(jid)['job_type']==['Screens']
    assert db.get_service(sid)['job_type']==['Skylights','Screens']


@pytest.mark.parametrize('value',[None,True,12,{},['Invalid'],['Screens',3],[''],[' ']])
def test_invalid_work_types_rejected_for_each_record(context,customer_id,value):
    db=context.db
    with pytest.raises(ValidationError):db.create_service(ServiceRecord(customer_id,'Invalid',value))
    with pytest.raises(ValidationError):db.create_customer(CustomerRecord(name='Invalid',default_job_type=value))
    with pytest.raises(ValidationError):db.create_job(JobRecord(customer_id,job_type=value))
    assert len(db.list_services(customer_id))==1
    assert db.list_jobs(customer_id)==[]


def test_withdrawn_choices_can_stay_but_cannot_be_added_to_another_record(context,customer_id):
    db=context.db
    sid=db.create_service(ServiceRecord(customer_id,'Inside', ['Internal windows','Screens']))
    jid=db.create_job(db.new_job_for_customer(customer_id,service_id=sid))
    context.settings.job_type_options.remove('Screens')
    db.update_service(sid,record(ServiceRecord,db.get_service(sid),hours='4'))
    db.update_job(jid,record(JobRecord,db.get_job(jid),hours='4'))
    assert db.get_job(jid)['job_type']==['Internal windows','Screens']
    assert db.new_job_for_customer(customer_id,service_id=sid).job_type==['Internal windows']
    with pytest.raises(ValidationError):db.create_service(ServiceRecord(customer_id,'New',['Screens']))
    with pytest.raises(ValidationError):db.create_job(JobRecord(customer_id,job_type=['Screens']))


def test_old_settings_preserve_labels_required_flags_custom_questions_and_options(context):
    old=context.settings.to_dict()
    for entity,key in [('customer_fields','default_job_type'),('job_fields','job_type')]:
        field=next(f for f in old[entity] if f['key']==key)
        field.update(field_type='dropdown',label='Work to do',required=True,browse_column=False)
    old['job_fields'].append(FieldDefinition('extra_choices','Extra choices','dropdown',options=['One','Two']).to_dict())
    loaded=AppSettings.from_dict(old)
    for entity,key in [('customers','default_job_type'),('jobs','job_type')]:
        field=next(f for f in loaded.fields_for(entity) if f.key==key)
        assert (field.field_type,field.label,field.required,field.browse_column)==('multiselect','Work to do',True,False)
        assert field.options==context.settings.job_type_options
    assert next(f for f in loaded.job_fields if f.key=='extra_choices').field_type=='dropdown'
    assert AppSettings.from_dict(loaded.to_dict()).to_dict()==loaded.to_dict()


@pytest.mark.parametrize('version',[3,4])
def test_backup_restore_supports_single_and_multiple_types(context,customer_id,tmp_path,version):
    source=tmp_path/'source.db'
    if version==3:version_three(source);cid=7;sid=21;jid=11
    else:
        candidate=CustomerDatabase(source,key_hex=KEY)
        cid=candidate.create_customer(CustomerRecord(name='Saved customer'))
        sid=candidate.create_service(ServiceRecord(cid,'Whole house',['Internal windows','Screens'],fee='600',hours='4'))
        jid=candidate.create_job(candidate.new_job_for_customer(cid,service_id=sid))
    before=file_fingerprint(source);info=inspect_backup(source,KEY,context.db.db_path)
    manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    _,safety,_=restore_backup(manager,source,context.store,context.settings,expected_info=info)
    assert file_fingerprint(source)==before
    assert context.db.get_job(jid)['job_type']==(['Internal windows'] if version==3 else ['Internal windows','Screens'])
    assert context.db.get_service(sid)['customer_id']==cid
    assert CustomerDatabase(safety,context.settings,key_hex=KEY).get_customer(customer_id)
