"""Render the named-service workflow with disposable synthetic encrypted data."""
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from customer_app.config import AppSettings, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord, ServiceRecord
from customer_app.ui.forms import JobDialog
from customer_app.ui.customer_services import ServiceDialog
from customer_app.ui.main_window import CustomerMainWindow
from customer_app.ui.theme import apply_application_theme

app=QApplication([]);apply_application_theme(app)
out=Path(__file__).parent/'screenshots';out.mkdir(exist_ok=True)
with TemporaryDirectory(prefix='customer-services-preview-') as temporary:
    root=Path(temporary);settings=AppSettings(db_path=root/'customers.db')
    store=SettingsStore(root/'settings.json');store.save(settings)
    db=CustomerDatabase(settings.db_path,settings,key_hex='12'*32)
    cid=db.create_customer(CustomerRecord(first_name='Mary',last_name='Brown',phone='0412345678',
        address_line_1='1 Ocean Street',suburb='Coogee',state='NSW',postcode='2034',
        default_job_type='Internal windows',default_fee='500',default_hours='3'))
    usual=db.list_services(cid)[0]
    db.update_service(usual['id'],ServiceRecord(cid,'Indoor windows','Internal windows',['3m ladder'],'500','3'))
    whole=db.create_service(ServiceRecord(cid,'Whole house',['Internal windows','External windows','Screens'],['Water-fed pole','3m ladder'],'600','4',job_type_sides={'Internal windows':'inside','External windows':'outside','Screens':'both'}))
    db.create_job(db.new_job_for_customer(cid,'2026-10-12',service_id=whole))
    window=CustomerMainWindow(db=db,settings_store=store,enable_backups=False);window.show()
    window.tabs.setCurrentIndex(1);window.customer_table.selectRow(0)
    page=window.customer_page;page.detail_tabs.setCurrentIndex(page.detail_tabs.indexOf(page.services))
    for size in [(1250,820),(900,690)]:
        window.resize(*size);app.processEvents();window.grab().save(str(out/f'customer-services-{size[0]}.png'))
        print('Services window:',size,'table:',page.services.table.size().toTuple(),'actual window:',window.size().toTuple())
    edit=ServiceDialog(db,settings,cid,whole);edit.show()
    for width in (650,520):
        edit.resize(width,760);app.processEvents();edit.grab().save(str(out/f'service-editor-{width}.png'))
    edit.close()
    dialog=JobDialog(db,settings,customer_id=cid);dialog.show()
    dialog.service.setCurrentIndex(dialog.service.findData(whole));app.processEvents()
    dialog.grab().save(str(out/'job-service-selection.png'))
    dialog.service.showPopup();app.processEvents();dialog.grab().save(str(out/'job-service-options.png'))
    dialog.service.hidePopup();dialog.close();window.close()
