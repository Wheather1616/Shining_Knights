"""Preview customer details and service controls using disposable synthetic records."""
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication, QScrollArea

from customer_app.config import AppSettings, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord
from customer_app.ui.forms import CustomerDialog
from customer_app.ui.theme import apply_application_theme

app = QApplication([])
apply_application_theme(app)
out = Path(__file__).parent / 'screenshots'
out.mkdir(exist_ok=True)
with TemporaryDirectory(prefix='customer-input-preview-') as temporary:
    root = Path(temporary)
    settings = AppSettings(db_path=root/'customers.db')
    store = SettingsStore(root/'settings.json')
    store.save(settings)
    db = CustomerDatabase(settings.db_path, settings, key_hex='12'*32)
    cid = db.create_customer(CustomerRecord(first_name='Mary Jane', last_name='Brown', phone='0457516182',
        email='mary@example.com', address_line_1='1 Ocean Street', suburb='Coogee', state='NSW', postcode='2034',
        frequency_value=8, frequency_unit='weeks', first_service_date='2026-10-20',
        default_equipment=['3m ladder','Water-fed pole'], default_job_type='External windows',
        default_fee='150', default_hours='1.5', default_payment_type='Cash'))
    dialog = CustomerDialog(db, settings, cid)
    dialog.show()
    scroll = dialog.findChild(QScrollArea)
    for width in (760,560):
        dialog.resize(width,780)
        app.processEvents()
        scroll.verticalScrollBar().setValue(0)
        app.processEvents()
        dialog.grab().save(str(out/f'customer-input-contact-{width}.png'))
        scroll.ensureWidgetVisible(dialog.form.widgets['default_equipment'], 0, 0)
        app.processEvents()
        dialog.grab().save(str(out/f'customer-input-service-{width}.png'))
        scroll.ensureWidgetVisible(dialog.form.widgets['default_fee'], 0, 0)
        app.processEvents()
        dialog.grab().save(str(out/f'customer-input-charge-{width}.png'))
        print(width, 'actual width', dialog.width(), 'horizontal scroll', scroll.horizontalScrollBar().maximum())
    dialog.resize(760,780)
    scroll.ensureWidgetVisible(dialog.form.widgets['first_service_date'],0,0)
    dialog.form.widgets['first_service_date'].show_calendar()
    app.processEvents()
    dialog.form.widgets['first_service_date'].popup.grab().save(str(out/'customer-input-calendar.png'))
    dialog.form.widgets['first_service_date'].popup.hide()
    dialog.close()
