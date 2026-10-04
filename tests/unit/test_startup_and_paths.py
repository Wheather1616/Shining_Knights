from pathlib import Path
from types import SimpleNamespace
import runpy
import sys
import pytest
from customer_app import paths, qt_bootstrap, single_instance

ORIGINAL_SUPPORT_DIR=paths.app_support_dir

@pytest.mark.parametrize('platform,variable,expected',[
    ('win32','LOCALAPPDATA','custom/ShiningKnights'),
    ('darwin',None,'home/Library/Application Support/ShiningKnights'),
    ('linux','XDG_DATA_HOME','custom/ShiningKnights'),
    ('linux',None,'home/.local/share/ShiningKnights'),
    ('win32',None,'home/AppData/Local/ShiningKnights')])
def test_native_app_data_paths(tmp_path,monkeypatch,platform,variable,expected):
    with monkeypatch.context() as patch:
        patch.setattr(paths.sys,'platform',platform)
        patch.setattr(Path,'home',lambda:tmp_path/'home')
        for env in ('LOCALAPPDATA','XDG_DATA_HOME'): patch.delenv(env,raising=False)
        if variable: patch.setenv(variable,str(tmp_path/'custom'))
        assert ORIGINAL_SUPPORT_DIR()==tmp_path/expected

def test_default_database_and_backups_use_isolated_storage(isolated_storage):
    assert paths.default_db_path()==isolated_storage/'data/customers.db'
    assert paths.default_backup_dir()==isolated_storage/'backups'

def test_qt_bootstrap_discovers_platform_plugins_and_respects_existing_path(tmp_path,monkeypatch):
    import PySide6
    platform=tmp_path/'PySide6/Qt/plugins/platforms'; platform.mkdir(parents=True)
    monkeypatch.setattr(PySide6,'__file__',str(tmp_path/'PySide6/__init__.py'))
    monkeypatch.delenv('QT_QPA_PLATFORM_PLUGIN_PATH',raising=False)
    monkeypatch.delenv('QT_PLUGIN_PATH',raising=False)
    qt_bootstrap.configure_qt_plugin_paths()
    assert qt_bootstrap.os.environ['QT_QPA_PLATFORM_PLUGIN_PATH']==str(platform)
    monkeypatch.setenv('QT_QPA_PLATFORM_PLUGIN_PATH','existing-user-path')
    qt_bootstrap.configure_qt_plugin_paths()
    assert qt_bootstrap.os.environ['QT_QPA_PLATFORM_PLUGIN_PATH']=='existing-user-path'

def test_module_entrypoint_calls_qt_bootstrap_before_app_run(monkeypatch):
    order=[]
    monkeypatch.setattr(qt_bootstrap,'configure_qt_plugin_paths',lambda:order.append('plugins'))
    stub=SimpleNamespace(run=lambda:order.append('run') or 7)
    monkeypatch.setitem(sys.modules,'customer_app.app',stub)
    with pytest.raises(SystemExit) as exit_info: runpy.run_module('customer_app',run_name='__main__')
    assert exit_info.value.code==7
    assert order==['plugins','run']

def test_primary_lock_excludes_secondary_and_is_released(qapp,monkeypatch):
    first=single_instance.SingleInstanceManager(); second=single_instance.SingleInstanceManager()
    monkeypatch.setattr(first,'_start_server',lambda:None)
    monkeypatch.setattr(second,'_start_server',lambda:None)
    monkeypatch.setattr(second,'notify_existing_instance',lambda:True)
    try:
        assert first.acquire()==(True,False)
        assert second.acquire()==(False,True)
        first.release()
        assert second.acquire()==(True,False)
    finally:
        first.release(); second.release()

def test_endpoint_failure_releases_lock(qapp,monkeypatch):
    manager=single_instance.SingleInstanceManager()
    monkeypatch.setattr(manager.server,'listen',lambda *a:False)
    monkeypatch.setattr(manager.server,'errorString',lambda:'Injected endpoint error')
    monkeypatch.setattr(single_instance.QLocalServer,'removeServer',lambda *a:False)
    with pytest.raises(RuntimeError,match='Injected endpoint error'): manager.acquire()
    assert not manager._owns_lock
    other=single_instance.SingleInstanceManager()
    assert other.lock.tryLock(0); other.lock.unlock()

@pytest.mark.parametrize('successful',[True,False])
def test_secondary_notification_retries_and_sends_activation(qapp,monkeypatch,successful):
    waits=[]; writes=[]
    class Socket:
        def connectToServer(self,name): pass
        def waitForConnected(self,timeout):
            waits.append(timeout)
            return successful and timeout==550
        def write(self,data): writes.append(data)
        def flush(self): pass
        def waitForBytesWritten(self,timeout): pass
        def disconnectFromServer(self): pass
        def abort(self): pass
    monkeypatch.setattr(single_instance,'QLocalSocket',Socket)
    manager=single_instance.SingleInstanceManager()
    assert manager.notify_existing_instance()==successful
    assert waits==[150,300,550]
    assert writes==([b'activate\n'] if successful else [])

def test_pending_connections_are_drained_with_one_activation(qapp,qtbot):
    manager=single_instance.SingleInstanceManager()
    closed=[]
    class Socket:
        def disconnectFromServer(self): closed.append('disconnect')
        def deleteLater(self): closed.append('delete')
    pending=[Socket(),Socket()]
    manager.server=SimpleNamespace(hasPendingConnections=lambda:bool(pending),nextPendingConnection=lambda:pending.pop())
    signals=[]; manager.activation_requested.connect(lambda:signals.append(True))
    with qtbot.waitSignal(manager.activation_requested,timeout=1000): manager._handle_new_connection()
    manager._handle_new_connection()
    assert signals==[True]
    assert closed==['disconnect','delete','disconnect','delete']
