from types import SimpleNamespace
import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from customer_app import app as bootstrap

class Instance(QObject):
    activation_requested=Signal()
    def __init__(self,result=(True,False),error=None):
        super().__init__(); self.result=result; self.error=error; self.released=False
    def acquire(self):
        if self.error: raise self.error
        return self.result
    def release(self): self.released=True

def test_primary_bootstrap_shows_window_and_wires_activation(qapp,window,monkeypatch):
    instance=Instance()
    monkeypatch.setattr(bootstrap,'QApplication',lambda *a:qapp)
    monkeypatch.setattr(bootstrap,'SingleInstanceManager',lambda *a:instance)
    monkeypatch.setattr(bootstrap,'CustomerMainWindow',lambda:window)
    monkeypatch.setattr(qapp,'exec',lambda:0)
    activated=[]
    monkeypatch.setattr(window,'show_normal',lambda:activated.append(True))
    assert bootstrap.run()==0
    assert window.isVisible()
    instance.activation_requested.emit()
    assert activated==[True]
    # Exercise cleanup callbacks without quitting pytest's session application.
    window.prepare_shutdown(); instance.release()
    qapp.aboutToQuit.disconnect(window.prepare_shutdown)
    qapp.aboutToQuit.disconnect(instance.release)

@pytest.mark.parametrize('notified',[True,False])
def test_secondary_bootstrap_never_initialises_database_window(qapp,monkeypatch,messages,notified):
    instance=Instance((False,notified))
    monkeypatch.setattr(bootstrap,'QApplication',lambda *a:qapp)
    monkeypatch.setattr(bootstrap,'SingleInstanceManager',lambda *a:instance)
    def forbidden(): raise AssertionError('Secondary launch constructed a window')
    monkeypatch.setattr(bootstrap,'CustomerMainWindow',forbidden)
    assert bootstrap.run()==0
    assert bool(messages)==(not notified)

def test_startup_error_releases_instance_and_reports_preserved_data(qapp,monkeypatch,messages):
    instance=Instance(error=RuntimeError('Cannot acquire lock'))
    monkeypatch.setattr(bootstrap,'QApplication',lambda *a:qapp)
    monkeypatch.setattr(bootstrap,'SingleInstanceManager',lambda *a:instance)
    assert bootstrap.run()==1
    assert instance.released
    assert messages[-1][0]=='critical'
    assert 'Existing data will not be reset' in messages[-1][2]
