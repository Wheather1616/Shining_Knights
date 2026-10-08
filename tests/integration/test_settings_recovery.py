"""Real encrypted restore, settings snapshots and failure recovery contracts."""
import copy
import json
import os
from pathlib import Path
import shutil

import pytest
from customer_app.backup import DatabaseBackupManager
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord
from customer_app.recovery import inspect_backup, restore_backup, settings_snapshot_path, recover_interrupted_restore
from tests.conftest import KEY


def manager_for(context,tmp_path, settings=True):
    return DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,
                                 settings_store=context.store if settings else None)


def test_restore_records_links_trash_and_settings_with_retained_safety_copy(context,customer_id,tmp_path):
    job = context.db.create_job(context.db.new_job_for_customer(customer_id)); context.db.trash_job(job)
    manager = manager_for(context,tmp_path); point = manager.create_backup()
    changed = copy.deepcopy(context.settings); changed.default_payment_method='Card'; context.store.save(changed)
    later = context.db.create_customer(CustomerRecord(name='Later'))
    restored,safety,info = restore_backup(manager,point,context.store,changed)
    assert context.db.get_customer(later) is None
    assert context.db.get_job(job)['customer_id'] == customer_id
    assert context.db.get_job(job)['deleted_at'] is not None
    assert restored.default_payment_method == '' and context.store.load() == restored
    old = CustomerDatabase(safety,changed,key_hex=KEY)
    assert old.get_customer(later)['name'] == 'Later'
    assert json.loads(settings_snapshot_path(safety).read_text())['default_payment_method'] == 'Card'
    assert info['customers'] == 1 and info['jobs'] == 1
    assert not list(context.db.db_path.parent.glob('*.restore*.tmp'))


def test_database_only_older_backup_keeps_current_settings(context,customer_id,tmp_path):
    manager = manager_for(context,tmp_path,settings=False); point=manager.create_backup()
    changed = copy.deepcopy(context.settings); changed.default_payment_method='Cash'; context.store.save(changed)
    assert inspect_backup(point,KEY,context.db.db_path)['settings'] is None
    restored,_,_ = restore_backup(manager,point,context.store,changed)
    assert restored.default_payment_method == 'Cash'


@pytest.mark.parametrize('damage',['bytes','wrong_key','schema','links','settings','columns','live'])
def test_invalid_restore_never_replaces_current_database_or_settings(context,customer_id,tmp_path,damage):
    manager=manager_for(context,tmp_path); point=manager.create_backup()
    if damage == 'bytes': point.write_bytes(b'corrupt')
    elif damage == 'wrong_key':
        other=CustomerDatabase(tmp_path/'other.db',key_hex='34'*32)
        shutil.copyfile(other.db_path,point)
    elif damage in ('schema','links','columns'):
        db=CustomerDatabase(point,context.settings,key_hex=KEY)
        with db.connect() as conn:
            if damage == 'schema': conn.execute('UPDATE crm_schema SET version=999')
            elif damage == 'columns': conn.execute('ALTER TABLE customers DROP COLUMN email')
            else:
                conn.execute('PRAGMA foreign_keys=OFF')
                conn.execute("INSERT INTO jobs(customer_id,created_at,updated_at) VALUES(999,'now','now')")
    elif damage == 'settings': settings_snapshot_path(point).write_text('{invalid')
    elif damage == 'live': point=context.db.db_path
    before=context.db.db_path.read_bytes(); settings_before=context.store.settings_path.read_bytes()
    with pytest.raises(Exception): restore_backup(manager,point,context.store,context.settings)
    assert context.db.db_path.read_bytes() == before
    assert context.store.settings_path.read_bytes() == settings_before
    assert context.db.get_customer(customer_id)['name'] == 'Mary Window'


def test_safety_backup_failure_prevents_restore(context,customer_id,tmp_path,monkeypatch):
    manager=manager_for(context,tmp_path); point=manager.create_backup()
    context.db.create_customer(CustomerRecord(name='Keep me'))
    before=context.db.db_path.read_bytes()
    def fail(): raise OSError('No space for safety copy')
    monkeypatch.setattr(manager,'create_backup',fail)
    with pytest.raises(OSError): restore_backup(manager,point,context.store,context.settings)
    assert context.db.db_path.read_bytes() == before


@pytest.mark.parametrize('failure',['settings','publish'])
def test_restore_write_failure_rolls_back_live_records_and_settings(context,customer_id,tmp_path,monkeypatch,failure):
    from customer_app import recovery
    manager=manager_for(context,tmp_path); point=manager.create_backup()
    later=context.db.create_customer(CustomerRecord(name='Keep later record'))
    before=context.store.settings_path.read_bytes()
    if failure == 'settings':
        def fail(*a): raise OSError('Settings disk unavailable')
        monkeypatch.setattr(context.store,'save',fail)
    else:
        real_replace = recovery.os.replace
        def fail(source,destination):
            if str(source).endswith('.restore.tmp'): raise OSError('Publish failure')
            return real_replace(source,destination)
        monkeypatch.setattr(recovery.os,'replace',fail)
    with pytest.raises(OSError): restore_backup(manager,point,context.store,context.settings)
    assert context.db.get_customer(later)['name'] == 'Keep later record'
    assert context.store.settings_path.read_bytes() == before
    assert len(manager._backup_files()) == 2


def test_interrupted_restore_rolls_back_on_next_startup(context,customer_id,tmp_path):
    live=context.db.db_path
    rollback=live.with_name(live.name+'.restore-rollback.tmp')
    rollback_settings=live.with_name(live.name+'.restore-settings-rollback.json')
    shutil.copyfile(live,rollback)
    rollback_settings.write_text(json.dumps(context.settings.to_dict()))
    later=context.db.create_customer(CustomerRecord(name='Partial restore'))
    changed=copy.deepcopy(context.settings); changed.default_payment_method='Card';context.store.save(changed)
    recover_interrupted_restore(live,context.store)
    assert context.db.get_customer(later) is None
    assert context.db.get_customer(customer_id)['name'] == 'Mary Window'
    assert context.store.load().default_payment_method == ''
    assert not rollback.exists() and not rollback_settings.exists()


def test_failed_settings_snapshot_does_not_publish_partial_backup(context,tmp_path,monkeypatch):
    manager=manager_for(context,tmp_path)
    def fail(): raise ValueError('Unreadable settings')
    monkeypatch.setattr(context.store,'load',fail)
    with pytest.raises(ValueError): manager.create_backup()
    assert list(manager.backup_dir.iterdir()) == []


def test_retention_removes_matching_settings_snapshot(context,tmp_path):
    manager=manager_for(context,tmp_path); old=manager.create_backup(); latest=manager.create_backup()
    os.utime(old,(1,1));manager.prune_backups()
    assert not old.exists() and not settings_snapshot_path(old).exists()
    assert latest.exists() and settings_snapshot_path(latest).exists()


@pytest.mark.parametrize('changed',['records','settings'])
def test_backup_changed_after_review_is_rejected(context,customer_id,tmp_path,changed):
    manager=manager_for(context,tmp_path);point=manager.create_backup()
    info=inspect_backup(point,KEY,context.db.db_path)
    if changed == 'records':
        snapshot=CustomerDatabase(point,context.settings,key_hex=KEY)
        snapshot.create_customer(CustomerRecord(name='Changed backup'))
    else:
        settings=copy.deepcopy(context.settings);settings.default_payment_method='Cash'
        settings_snapshot_path(point).write_text(json.dumps(settings.to_dict()))
    before=context.db.db_path.read_bytes()
    with pytest.raises(ValueError,match='changed'):
        restore_backup(manager,point,context.store,context.settings,expected_info=info)
    assert context.db.db_path.read_bytes() == before


def test_commit_cleanup_failure_rolls_back_both_files(context,customer_id,tmp_path,monkeypatch):
    manager=manager_for(context,tmp_path);point=manager.create_backup()
    later=context.db.create_customer(CustomerRecord(name='Later record'))
    changed=copy.deepcopy(context.settings);changed.default_payment_method='Card';context.store.save(changed)
    real_unlink=Path.unlink
    def fail(path,*args,**kwargs):
        if str(path).endswith('.restore-rollback.tmp'): raise OSError('Cleanup blocked')
        return real_unlink(path,*args,**kwargs)
    monkeypatch.setattr(Path,'unlink',fail)
    with pytest.raises(OSError): restore_backup(manager,point,context.store,changed)
    assert context.db.get_customer(later)['name'] == 'Later record'
    assert context.store.load().default_payment_method == 'Card'
