"""Render actual widgets with synthetic jobs in a disposable encrypted database."""
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from customer_app.config import AppSettings, FieldDefinition, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord, JobRecord
from customer_app.ui.main_window import CustomerMainWindow
from customer_app.ui.theme import apply_application_theme

app = QApplication([])
apply_application_theme(app)
output = Path(__file__).parent / 'screenshots'
output.mkdir(exist_ok=True)
with TemporaryDirectory(prefix='jobs-preview-') as temporary:
    root = Path(temporary)
    settings = AppSettings(db_path=root/'jobs.db')
    # A compact browse configuration, using the existing field controls.
    for field in settings.job_fields:
        field.browse_column = field.key in ('job_type', 'status', 'fee', 'payment_status')
    settings.job_fields.append(FieldDefinition('weather', 'Weather', 'dropdown', options=['Dry', 'Rain']))
    store = SettingsStore(root/'settings.json'); store.save(settings)
    db = CustomerDatabase(settings.db_path, settings, key_hex='12' * 32)
    ids = []
    for name, suburb, day, fee, status, payment in (
            ('Mary Window', 'Coogee', '2026-10-02', '150', 'Scheduled', 'Unpaid'),
            ('Luke Garden', 'Randwick', '2026-10-02', '180', 'Scheduled', 'Unpaid'),
            ('Sarah Bell', 'Clovelly', '2026-10-02', '180', 'Completed', 'Paid'),
            ('Harbour Café', 'Maroubra', '2026-10-03', '220', 'In progress', 'Unpaid'),
            ('Alex Reed', 'Bondi', '2026-10-03', '120', 'Scheduled', 'Unpaid'),
            ('Ocean View', 'Coogee', '2026-10-04', '150', 'Scheduled', 'Unpaid'),
            ('James Bell', 'Randwick', '2026-10-04', '150', 'Scheduled', 'Unpaid')):
        customer = db.create_customer(CustomerRecord(name=name, suburb=suburb, address_line_1='1 Ocean Street',
            state='NSW', postcode='2034', phone='0412 345 678', email='mary@example.com'))
        ids.append(db.create_job(JobRecord(customer, scheduled_date=day,
            completed_date=day if status == 'Completed' else '', fee=fee, status=status,
            job_type='External windows', equipment=['3m ladder'], payment_type='Cash', payment_status=payment,
            notes='Use the side gate. Please call before arriving.', custom_fields={'weather': 'Dry'})))
    window = CustomerMainWindow(db=db, settings_store=store, enable_backups=False)
    window.tabs.setCurrentIndex(2); window.show(); app.processEvents()
    page = window.jobs_page
    window.grab().save(str(output/'jobs-unselected.png'))
    page.tree.setCurrentItem(page.items[ids[0]])
    for job_id in (ids[0], ids[1], ids[4]):
        page.items[job_id].setCheckState(0, Qt.CheckState.Checked)
    page.groups[('date', '2026-10-04')].setExpanded(False)
    for width, height in ((1250, 820), (900, 690)):
        window.resize(width, height); app.processEvents()
        window.grab().save(str(output/f'jobs-{width}.png'))
        print({'window': window.size().toTuple(), 'list': page.list_card.size().toTuple(),
            'detail': page.detail_card.size().toTuple(), 'viewport': page.tree.viewport().size().toTuple(),
            'footer': page.selection_caption.size().toTuple(), 'row': page.tree.visualItemRect(page.items[ids[0]]).getRect()})
    window.resize(1250, 820)
    page.status_filter.showPopup(); app.processEvents()
    page.status_filter.view().window().grab().save(str(output/'jobs-dropdown.png'))
    page.status_filter.hidePopup()
    window.close(); app.processEvents()
