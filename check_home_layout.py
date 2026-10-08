"""Render Home and the shared header using a disposable database only."""
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication

from customer_app.config import AppSettings, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord, JobRecord
from customer_app.ui.main_window import CustomerMainWindow
from customer_app.ui.theme import apply_application_theme

app = QApplication([])
apply_application_theme(app)
output = Path(__file__).parent / 'screenshots'
output.mkdir(exist_ok=True)
with TemporaryDirectory(prefix='home-preview-') as temporary:
    root = Path(temporary)
    settings = AppSettings(db_path=root / 'customers.db')
    store = SettingsStore(root / 'settings.json')
    store.save(settings)
    db = CustomerDatabase(settings.db_path, settings, key_hex='12' * 32)
    for i, (name, suburb) in enumerate([('Mary Wilson', 'Coogee'), ('Ben Clark', 'Randwick'),
                                      ('Sarah Evans', 'Maroubra'), ('David Lewis', 'Clovelly'), ('Anna Brown', 'Bondi')]):
        cid = db.create_customer(CustomerRecord(name=name, suburb=suburb))
        db.create_job(JobRecord(cid, scheduled_date=(date.today() + timedelta(days=i // 2)).isoformat(), job_type='External windows'))
    for name, suburb, offset in [('Peter Harris', 'Bronte', -1), ('Helen Moore', 'Kingsford', 6)]:
        db.create_customer(CustomerRecord(name=name, suburb=suburb, first_service_date=(date.today() + timedelta(days=offset)).isoformat()))
    window = CustomerMainWindow(db=db, settings_store=store, enable_backups=False)
    window.show()
    for width, height in [(1250, 820), (900, 690)]:
        window.resize(width, height)
        app.processEvents()
        window.grab().save(str(output / f'home-{width}.png'))
    overdue = db.create_customer(CustomerRecord(name='Sample overdue job'))
    db.create_job(JobRecord(overdue, scheduled_date=(date.today() - timedelta(days=1)).isoformat()))
    window.refresh_all()
    for width, height in [(1250, 820), (900, 690)]:
        window.resize(width, height)
        app.processEvents()
        window.grab().save(str(output / f'home-overdue-{width}.png'))
    for index, name in [(1, 'customers'), (2, 'jobs'), (3, 'settings')]:
        window.tabs.setCurrentIndex(index)
        app.processEvents()
        window.grab().save(str(output / f'header-{name}.png'))
    window.configuration.discard()
    window.close()
