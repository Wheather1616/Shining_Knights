"""Shared isolation: disposable data, explicit test keys and managed Qt widgets."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('PYTEST_QT_API', 'pyside6')

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import pytest
from hypothesis import settings as hypothesis_settings
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QPushButton

from customer_app.config import AppSettings, FieldDefinition, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord
from customer_app.ui.theme import apply_application_theme

KEY = '12' * 32  # Disposable fixture key, never a user's stored encryption key.
hypothesis_settings.register_profile('repeatable', max_examples=100, derandomize=True, deadline=None)
hypothesis_settings.load_profile('repeatable')

def pytest_addoption(parser):
    parser.addoption('--run-platform-tests', action='store_true', help='Also exercise native local IPC endpoints.')

def pytest_collection_modifyitems(config, items):
    for item in items:
        for kind in ('unit','integration','ui','platform'):
            if kind in Path(str(item.path)).parts: item.add_marker(getattr(pytest.mark,kind))
        if 'platform' in item.keywords and not config.getoption('--run-platform-tests'):
            item.add_marker(pytest.mark.skip(reason='Native IPC is opt-in: use --run-platform-tests.'))

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item,call):
    outcome=yield
    report=outcome.get_result()
    if report.when=='call' and report.failed and 'qtbot' in item.funcargs:
        # Save only failing test widgets; their data is synthetic and isolated.
        try:
            from PySide6.QtWidgets import QApplication
            import re
            destination=Path(item.config.rootpath)/'reports/failures'
            destination.mkdir(parents=True,exist_ok=True)
            stem=re.sub(r'[^a-zA-Z0-9_-]+','_',item.nodeid)
            app=QApplication.instance()
            if app:
                for index,widget in enumerate(app.topLevelWidgets()):
                    if widget.isVisible(): widget.grab().save(str(destination/f'{stem}_{index}.png'))
        except Exception as exc:
            report.sections.append(('Screenshot capture',str(exc)))

@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Default app paths resolve only inside this test; real keyring access fails."""
    from customer_app import paths, config, single_instance, security
    from customer_app.ui import main_window
    data = tmp_path / 'user-data'
    monkeypatch.setattr(paths,'app_support_dir',lambda:data)
    monkeypatch.setattr(config,'app_support_dir',lambda:data)
    monkeypatch.setattr(single_instance,'app_support_dir',lambda:data)
    monkeypatch.setattr(main_window,'default_backup_dir',lambda:data/'backups')
    def forbidden(*args, **kwargs):
        raise AssertionError('A test attempted to access the real OS credential store.')
    for name in ('get_password','set_password','get_keyring'):
        monkeypatch.setattr(security.keyring,name,forbidden)
    return data

@pytest.fixture(scope='session')
def qapp(qapp_args, qapp_cls):
    # Override pytest-qt's application fixture to apply the production theme once.
    app = qapp_cls.instance() or qapp_cls(qapp_args)
    apply_application_theme(app)
    yield app

@dataclass
class Context:
    db: CustomerDatabase
    settings: AppSettings
    store: SettingsStore

@pytest.fixture
def context(tmp_path):
    settings = AppSettings(db_path=tmp_path/'customers.db')
    settings.customer_fields.append(FieldDefinition('gate_code','Gate code',browse_column=True))
    settings.job_fields.append(FieldDefinition('weather','Weather','dropdown',options=['Dry','Rain']))
    store = SettingsStore(tmp_path/'crm-settings.json')
    store.save(settings)
    return Context(CustomerDatabase(settings.db_path,settings,key_hex=KEY),settings,store)

@pytest.fixture
def customer_id(context):
    return context.db.create_customer(CustomerRecord(name='Mary Window',phone='0412 345 678',
        address_line_1='1 Ocean Street',suburb='Coogee',state='NSW',postcode='2034',
        frequency_value=8,frequency_unit='weeks',default_fee='180.00',
        default_job_type='External windows',default_equipment=['3m ladder'],
        default_payment_type='Bank transfer',custom_fields={'gate_code':'0042'}))

@pytest.fixture
def window(context, qtbot):
    from customer_app.ui.main_window import CustomerMainWindow
    widget = CustomerMainWindow(db=context.db,settings_store=context.store,enable_backups=False)
    qtbot.addWidget(widget)
    widget.show()
    return widget

@pytest.fixture
def messages(monkeypatch):
    """Record native prompts without blocking; confirmation defaults to No."""
    calls=[]
    for kind in ('warning','information','critical'):
        def record(parent,title,text,*args,_kind=kind,**kwargs):
            calls.append((_kind,title,text))
            return QMessageBox.StandardButton.Ok
        monkeypatch.setattr(QMessageBox,kind,record)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.No)
    return calls

@pytest.fixture
def click(qtbot):
    def perform(widget, text):
        matches=[b for b in widget.findChildren(QPushButton) if b.text()==text and b.isVisible()]
        assert len(matches)==1, (text,[b.text() for b in widget.findChildren(QPushButton)])
        qtbot.mouseClick(matches[0],Qt.MouseButton.LeftButton)
    return perform

@pytest.fixture
def today(monkeypatch):
    """Fix the date where it is consumed, without altering Python's global clock."""
    from customer_app import database
    from customer_app.ui import forms, main_window
    class FixedDate(date):
        @classmethod
        def today(cls): return cls(2026,10,2)
    for module in (database,forms,main_window): monkeypatch.setattr(module,'date',FixedDate)
    return FixedDate.today()
