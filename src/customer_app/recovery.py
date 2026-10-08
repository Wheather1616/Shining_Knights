"""Validate and stage recovery points before replacing the live encrypted database."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil

from .config import AppSettings
from .database import SCHEMA_VERSION
from .db_crypto import open_encrypted_connection, verify_encrypted_database


def settings_snapshot_path(backup):
    return Path(backup).with_suffix('.settings.json')


def file_fingerprint(path):
    import hashlib
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect_backup(backup, key_hex, live_path):
    backup = Path(backup)
    if not backup.is_file() or backup.resolve() == Path(live_path).resolve():
        raise ValueError('Choose a saved backup, rather than the current records file.')
    verify_encrypted_database(backup, key_hex)
    connection = open_encrypted_connection(backup, key_hex)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'customers', 'jobs', 'crm_schema'} <= tables:
            raise ValueError('This is not a customer and jobs backup.')
        versions = connection.execute('SELECT version FROM crm_schema').fetchall()
        if len(versions) != 1 or versions[0][0] not in (1, 2, 3, SCHEMA_VERSION):
            raise ValueError('This backup uses a different app version.')
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Customer and job links in this backup are damaged.')
        # Verify the full column contract, including empty tables, before accepting.
        from .models import CustomerRecord, JobRecord
        required = {'customers': set(CustomerRecord.__dataclass_fields__) - {'default_fee'} | {'default_fee_cents'},
                    'jobs': set(JobRecord.__dataclass_fields__) - {'fee'} | {'fee_cents', 'deleted_at'}}
        if versions[0][0] == 1:
            required['customers'] -= {'first_name', 'last_name', 'default_hours'}
            required['jobs'] -= {'hours'}
        if versions[0][0] < 3:
            required['jobs'] -= {'service_id','service_name'}
        else:
            required['customer_services'] = {'id','customer_id','name','job_type','equipment','fee_cents','hours','notes','active','is_default','created_at','updated_at'}
            if 'customer_services' not in tables:
                raise ValueError('This backup is missing customer services.')
            if connection.execute('''SELECT 1 FROM jobs j JOIN customer_services s ON s.id=j.service_id
                WHERE s.customer_id<>j.customer_id LIMIT 1''').fetchone():
                raise ValueError('Customer and service links in this backup are damaged.')
        for table, columns in required.items():
            present = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
            if not columns <= present:
                raise ValueError('This backup is missing required record details.')
        counts = {table: connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in ('customers', 'jobs')}
    finally:
        connection.close()
    snapshot = settings_snapshot_path(backup)
    settings = AppSettings.from_dict(json.loads(snapshot.read_text(encoding='utf-8'))) if snapshot.exists() else None
    return {'path': backup, 'modified': backup.stat().st_mtime, 'settings': settings,
            'fingerprint': file_fingerprint(backup),
            'settings_fingerprint': file_fingerprint(snapshot) if snapshot.exists() else None, **counts}


def restore_backup(manager, backup, store, current_settings, *, expected_info=None):
    """Stage verified bytes, create a safety copy, and roll back on write failures.

    The GUI serialises this with other database work. Connections are scoped per
    operation, so no live database handle remains open at the replacement step.
    The safety point is retained for recovery after an interrupted application.
    """
    backup = Path(backup)
    live = manager.db_path
    if not backup.is_file() or backup.resolve() == live.resolve():
        raise ValueError('Choose a saved backup, rather than the current records file.')
    staged = live.with_name(live.name + '.restore.tmp')
    rollback = live.with_name(live.name + '.restore-rollback.tmp')
    if rollback.exists():
        raise ValueError('An interrupted restore needs recovery before another restore can begin.')
    rollback_settings = live.with_name(live.name + ".restore-settings-rollback.json")
    candidate = copy.deepcopy(current_settings)
    original_settings = store.settings_path.read_bytes() if store.settings_path.exists() else None
    replaced = False
    try:
        # Take a private snapshot so a later source-file change cannot bypass validation.
        shutil.copyfile(backup, staged)
        if os.name == 'posix':
            staged.chmod(0o600)
        info = inspect_backup(staged, manager.key_hex, live)
        snapshot = settings_snapshot_path(backup)
        snapshot_bytes = snapshot.read_bytes() if snapshot.exists() else None
        if expected_info:
            import hashlib
            settings_hash = hashlib.sha256(snapshot_bytes).hexdigest() if snapshot_bytes is not None else None
            if info['fingerprint'] != expected_info['fingerprint'] or settings_hash != expected_info['settings_fingerprint']:
                raise ValueError('The selected backup has changed. Choose it again before restoring.')
        if snapshot_bytes is not None:
            candidate = AppSettings.from_dict(json.loads(snapshot_bytes))
        candidate.db_path = live
        candidate.validate()
        # Verify data with its restored field definitions without editing the snapshot.
        from .database import CustomerDatabase
        staged_db = CustomerDatabase(staged, candidate, key_hex=manager.key_hex)
        for customer in staged_db.list_customers(include_inactive=True):
            staged_db.list_services(customer['id'],include_archived=True)
        staged_db.list_jobs(include_deleted=True)
        safety = manager.create_backup()
        # Convert any live WAL into the main file before replacing it.
        connection = open_encrypted_connection(live, manager.key_hex)
        try:
            connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        finally:
            connection.close()
        with rollback_settings.open('w', encoding='utf-8') as handle:
            json.dump(current_settings.to_dict(), handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == 'posix': rollback_settings.chmod(0o600)
        os.replace(live, rollback)
        try:
            os.replace(staged, live)
            replaced = True
            store.save(candidate)
            rollback.unlink()
        except Exception:
            live.unlink(missing_ok=True)
            os.replace(rollback, live)
            replaced = False
            if original_settings is None:
                store.settings_path.unlink(missing_ok=True)
            elif not store.settings_path.exists() or store.settings_path.read_bytes() != original_settings:
                temporary = store.settings_path.with_name(store.settings_path.name + '.recovery.tmp')
                temporary.write_bytes(original_settings)
                os.replace(temporary, store.settings_path)
            rollback_settings.unlink(missing_ok=True)
            raise
        try:
            rollback_settings.unlink(missing_ok=True)
        except OSError:
            pass  # Committed restore; an orphan metadata file is safe to remove later.
        return candidate, safety, info
    finally:
        staged.unlink(missing_ok=True)
        # Never remove rollback bytes after a failed recovery operation.
        if not replaced and rollback.exists() and not live.exists():
            os.replace(rollback, live)


def recover_interrupted_restore(live_path, store):
    """Roll back a restore interrupted before its final commit on next startup."""
    live = Path(live_path)
    rollback = live.with_name(live.name + '.restore-rollback.tmp')
    rollback_settings = live.with_name(live.name + '.restore-settings-rollback.json')
    if not rollback.exists():
        try:
            rollback_settings.unlink(missing_ok=True)
        except OSError:
            pass
        return
    # Saving the original settings first allows a failed startup recovery to retry.
    if not rollback_settings.exists():
        raise ValueError('An interrupted restore needs its safety copy. Existing files have been preserved.')
    settings = AppSettings.from_dict(json.loads(rollback_settings.read_text(encoding='utf-8')))
    store.save(settings)
    os.replace(rollback, live)
    rollback_settings.unlink(missing_ok=True)
