"""Render synthetic customer states against the actual PySide6 implementation."""
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication

from customer_app.config import AppSettings, FieldDefinition, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord, JobRecord
from customer_app.ui.main_window import CustomerMainWindow
from customer_app.ui.theme import apply_application_theme


app = QApplication([])
apply_application_theme(app)
destination = Path(__file__).parent / 'screenshots'
destination.mkdir(exist_ok=True)
with TemporaryDirectory(prefix='customer-layout-') as directory:
    root = Path(directory)
    settings = AppSettings(db_path=root / 'customers.db')
    settings.customer_fields.append(FieldDefinition('gate_code', 'Gate code', browse_column=True))
    store = SettingsStore(root / 'settings.json'); store.save(settings)
    db = CustomerDatabase(settings.db_path, settings, key_hex='12' * 32)
    customer_id = db.create_customer(CustomerRecord(name='Mary Window', phone='0412 345 678',
        email='mary@example.com', address_line_1='1 Ocean Street', suburb='Coogee', state='NSW', postcode='2034',
        frequency_value=1, frequency_unit='months', default_fee='150', default_job_type='Solar panels',
        default_equipment=['3m ladder', '6m ladder'], default_payment_type='Cash',
        notes='Use the side gate. Please call before arriving.', custom_fields={'gate_code': '0042'}))
    db.create_job(JobRecord(customer_id, status='Completed', completed_date='2026-10-02', fee='150',
        job_type='Solar panels', payment_type='Cash', payment_status='Paid'))
    window = CustomerMainWindow(db=db, settings_store=store, enable_backups=False)
    window.tabs.setCurrentIndex(1); window.show(); app.processEvents()
    window.grab().save(str(destination / 'customers-unselected.png'))
    window.customer_table.selectRow(0)
    for width, height in ((1250, 820), (900, 690)):
        window.resize(width, height); app.processEvents()
        window.grab().save(str(destination / f'customers-{width}.png'))
        print({'window': [window.width(), window.height()], 'history': [window.history.width(), window.history.height()],
            'viewport_height': window.history.viewport().height(), 'profile_height': window.customer_page.overview_scroll.height()})
        page=window.customer_page
        print('sizes:', {'profile_content': page.overview_scroll.widget().size().toTuple(),
            'profile_hint': page.overview_scroll.widget().minimumSizeHint().toTuple(),
            'job_page': page.detail_tabs.widget(0).size().toTuple(),
            'job_page_hint': page.detail_tabs.widget(0).minimumSizeHint().toTuple(),
            'history': page.history.geometry().getRect(), 'edit': page.edit_job_button.geometry().getRect(),
            'page_min_hint': page.minimumSizeHint().toTuple()})
    window.resize(1250, 820)
    window.customer_page.detail_tabs.setCurrentIndex(1); app.processEvents()
    window.grab().save(str(destination / 'customer-service.png'))
    window.customer_page.detail_tabs.setCurrentIndex(2); app.processEvents()
    window.grab().save(str(destination / 'customer-notes.png'))
    window.close(); app.processEvents()
