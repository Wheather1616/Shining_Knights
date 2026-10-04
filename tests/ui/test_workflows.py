"""User interaction tests against real widgets and a disposable encrypted database."""
import csv
from dataclasses import asdict
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QFileDialog, QMessageBox
import pytest
from customer_app.models import CustomerRecord, JobRecord
from customer_app.ui.forms import CustomerDialog, JobDialog, RecordForm
from customer_app.ui.field_settings import FieldDialog

def drive_modal(open_action, dialog_class, action):
    """Interact inside a real exec() loop, and always close it even on failure."""
    errors=[]
    def perform():
        dialog=QApplication.activeModalWidget()
        try:
            assert isinstance(dialog,dialog_class),type(dialog)
            action(dialog)
        except BaseException as exc: errors.append(exc)
        finally:
            if isinstance(dialog,QDialog) and dialog.isVisible(): dialog.reject()
    timer=QTimer(); timer.setSingleShot(True); timer.timeout.connect(perform)
    timer.start(0)
    try: open_action()
    finally: timer.stop()
    if errors: raise errors[0]

def test_add_customer_then_job_through_main_window_buttons(window,context,qtbot,click,today):
    def fill_customer(dialog):
        qtbot.keyClicks(dialog.form.widgets['name'],'Mary Window')
        qtbot.keyClicks(dialog.form.widgets['suburb'],'Coogee')
        dialog.form.frequency.setCurrentText('Every 8 weeks')
        qtbot.keyClicks(dialog.form.widgets['default_fee'],'180.00')
        qtbot.keyClicks(dialog.form.widgets['gate_code'],'0042')
        dialog.form.widgets['default_job_type'].setCurrentText('External windows')
        with qtbot.waitSignal(dialog.accepted,timeout=1000): click(dialog,'Save')
    drive_modal(lambda:click(window,'Add customer'),CustomerDialog,fill_customer)
    assert window.tabs.currentIndex()==1
    assert window.customer_table.rowCount()==1
    customer=context.db.list_customers()[0]
    assert customer['frequency_value']==8
    assert customer['custom_fields']['gate_code']=='0042'
    def fill_job(dialog):
        assert dialog.form.widgets['fee'].text()=='180.00'
        dialog.form.widgets['status'].setCurrentText('Completed')
        assert dialog.form.widgets['completed_date'].text()=='02/10/2026'
        dialog.form.widgets['weather'].setCurrentText('Dry')
        with qtbot.waitSignal(dialog.accepted,timeout=1000): click(dialog,'Save')
    drive_modal(lambda:click(window,'Add job for customer'),JobDialog,fill_job)
    job=context.db.list_jobs()[0]
    assert job['status']=='Completed'
    assert job['custom_fields']['weather']=='Dry'
    assert context.db.customer_summary(customer['id'])['jobs_completed']==1

def test_customer_cancel_does_not_create_a_record(window,context,qtbot,click):
    def cancel(dialog):
        qtbot.keyClicks(dialog.form.widgets['name'],'Discard me')
        with qtbot.waitSignal(dialog.rejected,timeout=1000): click(dialog,'Cancel')
    drive_modal(lambda:click(window,'Add customer'),CustomerDialog,cancel)
    assert context.db.list_customers()==[]
    assert window.customer_table.rowCount()==0

@pytest.mark.parametrize('name,field,value,message',[('','name','','required'),('Mary','first_service_date','31/02/2026','use dd/mm/yyyy'),('Mary','default_fee','1.001','two decimal')])
def test_invalid_customer_save_keeps_form_open_and_database_empty(context,qtbot,click,messages,name,field,value,message):
    dialog=CustomerDialog(context.db,context.settings); qtbot.addWidget(dialog); dialog.show()
    dialog.form.widgets['name'].setText(name)
    dialog.form.widgets[field].setText(value)
    click(dialog,'Save')
    assert dialog.isVisible()
    assert dialog.saved_id is None
    assert context.db.list_customers()==[]
    assert any(message in text for _,_,text in messages)

def test_failed_database_save_reports_error_and_preserves_input(context,qtbot,click,messages,monkeypatch):
    dialog=CustomerDialog(context.db,context.settings); qtbot.addWidget(dialog); dialog.show()
    dialog.form.widgets['name'].setText('Keep my input')
    def fail(record): raise OSError('Disk full')
    monkeypatch.setattr(context.db,'create_customer',fail)
    click(dialog,'Save')
    assert dialog.isVisible()
    assert dialog.form.widgets['name'].text()=='Keep my input'
    assert messages[-1][2]=='Disk full'

def test_job_edit_preserves_customer_and_clears_completed_date(context,customer_id,qtbot,click,today):
    job=context.db.create_job(JobRecord(customer_id,status='Completed',completed_date='2026-10-01',fee='180.00'))
    dialog=JobDialog(context.db,context.settings,job_id=job); qtbot.addWidget(dialog); dialog.show()
    assert not dialog.customer.isEnabled()
    dialog.form.widgets['status'].setCurrentText('Scheduled')
    assert dialog.form.widgets['completed_date'].text()==''
    with qtbot.waitSignal(dialog.accepted,timeout=1000): click(dialog,'Save')
    assert context.db.get_job(job)['completed_date']==''
    assert context.db.get_job(job)['customer_id']==customer_id

def test_job_customer_switch_loads_the_selected_customer_defaults(context,customer_id,qtbot,click):
    second=context.db.create_customer(CustomerRecord(name='Other Customer',default_fee='220.00'))
    dialog=JobDialog(context.db,context.settings,customer_id=customer_id); qtbot.addWidget(dialog); dialog.show()
    dialog.customer.setCurrentIndex(dialog.customer.findData(second))
    assert dialog.form.widgets['fee'].text()=='220.00'
    with qtbot.waitSignal(dialog.accepted,timeout=1000): click(dialog,'Save')
    assert context.db.get_job(dialog.saved_id)['customer_id']==second

def test_add_job_with_no_active_customer_gives_guidance(window,context,click,messages):
    click(window,'Add job')
    assert messages[-1][1]=='Add a customer first'
    assert context.db.list_jobs()==[]

def test_search_profile_and_duplicate_customer_grouping(window,context,customer_id,qtbot):
    other=context.db.create_customer(CustomerRecord(name='Mary Window',suburb='Randwick'))
    context.db.create_job(context.db.new_job_for_customer(customer_id))
    context.db.create_job(context.db.new_job_for_customer(other))
    window.refresh_all(); window.tabs.setCurrentIndex(1)
    window.customer_table.selectRow(0)
    assert window.history.rowCount()==1
    assert 'Coogee' in window.profile.text()
    window.tabs.setCurrentIndex(2)
    window.group_by.setCurrentIndex(window.group_by.findData('customer'))
    assert window.jobs_tree.topLevelItemCount()==2
    window.tabs.setCurrentIndex(1)
    qtbot.keyClicks(window.customer_search,'Randwick')
    qtbot.waitUntil(lambda:window.customer_table.rowCount()==1)
    assert window.selected_customer is None
    assert 'Select a customer' in window.profile.text()

def test_customer_deactivation_requires_confirmation_and_keeps_history(window,context,customer_id,click,messages,monkeypatch):
    job=context.db.create_job(context.db.new_job_for_customer(customer_id)); window.refresh_all()
    window.tabs.setCurrentIndex(1); window.customer_table.selectRow(0)
    click(window,'Activate / deactivate')
    assert context.db.get_customer(customer_id)['active'] is True
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.Yes)
    click(window,'Activate / deactivate')
    assert context.db.get_customer(customer_id)['active'] is False
    assert context.db.get_job(job) is not None
    window.inactive.setChecked(True)
    assert window.customer_table.rowCount()==1

def test_complete_trash_and_restore_through_job_buttons(window,context,customer_id,click,messages,monkeypatch,today):
    job=context.db.create_job(context.db.new_job_for_customer(customer_id,'2026-10-01')); window.refresh_all()
    window.tabs.setCurrentIndex(2)
    window.jobs_tree.setCurrentItem(window.jobs_tree.topLevelItem(0).child(0))
    click(window,'Mark completed')
    assert context.db.get_job(job)['status']=='Completed'
    window.jobs_tree.setCurrentItem(window.jobs_tree.topLevelItem(0).child(0))
    click(window,'Move to Trash')  # Cancel is the default fixture response.
    assert context.db.get_job(job)['deleted_at'] is None
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    click(window,'Move to Trash')
    assert context.db.list_jobs()==[]
    window.job_filter.setCurrentText('Trash')
    assert len(window.job_rows)==1
    window.jobs_tree.setCurrentItem(window.jobs_tree.topLevelItem(0).child(0))
    click(window,'Edit job')
    assert messages[-1][1]=='Restore job first'
    click(window,'Restore job')
    assert context.db.get_job(job)['deleted_at'] is None
    assert context.db.customer_summary(customer_id)['jobs_completed']==1

def test_job_filters_exclude_cancelled_completed_and_trashed_overdue_records(window,context,customer_id,today):
    db=context.db
    overdue=db.create_job(JobRecord(customer_id,scheduled_date='2026-10-01'))
    upcoming=db.create_job(JobRecord(customer_id,scheduled_date='2026-10-05'))
    cancelled=db.create_job(JobRecord(customer_id,scheduled_date='2026-10-01',status='Cancelled'))
    trashed=db.create_job(JobRecord(customer_id,scheduled_date='2026-10-01')); db.trash_job(trashed)
    window.refresh_all(); window.job_filter.setCurrentText('Overdue')
    assert [j['id'] for j in window.job_rows]==[overdue]
    window.job_filter.setCurrentText('Upcoming')
    assert {j['id'] for j in window.job_rows}=={overdue,upcoming}
    window.job_filter.setCurrentText('Cancelled')
    assert [j['id'] for j in window.job_rows]==[cancelled]
    window.job_filter.setCurrentText('Trash')
    assert [j['id'] for j in window.job_rows]==[trashed]

def test_settings_save_emits_signal_updates_columns_and_new_forms(window,context,qtbot,click,messages):
    window.tabs.setCurrentIndex(3); page=window.configuration
    page.tabs.setCurrentIndex(1)
    page.tables['customers'].cellWidget(0,1).setText('Customer name')
    page.lookups['equipment_options'].setPlainText('Ladder\nWater-fed pole')
    with qtbot.waitSignal(page.settings_saved,timeout=1000): click(page,'Save configuration')
    assert context.store.load().customer_fields[0].label=='Customer name'
    assert window.customer_table.horizontalHeaderItem(0).text()=='Customer name'
    assert window.db.settings.equipment_options==['Ladder','Water-fed pole']
    form=RecordForm(window.settings,'customers',asdict(CustomerRecord())); qtbot.addWidget(form)
    assert form.widgets['default_equipment'].item(0).text()=='Ladder'

def test_invalid_field_configuration_is_not_persisted_or_applied(window,context,click,messages):
    window.tabs.setCurrentIndex(3); page=window.configuration
    before=context.store.settings_path.read_bytes()
    page.tables['customers'].cellWidget(0,1).setText('')
    click(page,'Save configuration')
    assert context.store.settings_path.read_bytes()==before
    assert window.settings.customer_fields[0].label=='Client name'
    assert messages[-1][1]=='Configuration could not be saved'

def test_custom_dropdown_added_via_dialog_is_available_in_new_forms(window,context,qtbot,click,messages):
    window.tabs.setCurrentIndex(3); page=window.configuration; page.tabs.setCurrentIndex(1)
    def add_field(dialog):
        qtbot.keyClicks(dialog.label,'Access type')
        assert dialog.key.text()=='access_type'
        dialog.kind.setCurrentText('dropdown'); dialog.options.setPlainText('Open\nLocked')
        click(dialog,'OK')
    drive_modal(lambda:click(page,'Add custom field'),FieldDialog,add_field)
    click(page,'Save configuration')
    form=RecordForm(window.settings,'customers',asdict(CustomerRecord())); qtbot.addWidget(form)
    assert [form.widgets['access_type'].itemText(i) for i in range(3)]==['Choose…','Open','Locked']

def test_customer_export_quotes_formula_text_and_preserves_unicode(window,context,qtbot,tmp_path,monkeypatch,click):
    context.db.create_customer(CustomerRecord(name='=SUM(1,2)',notes='Café, "Gate"\nSecond line'))
    window.refresh_all(); window.tabs.setCurrentIndex(1)
    path=tmp_path/'customers.csv'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**kw:(str(path),'CSV files (*.csv)'))
    click(window,'Export CSV')
    with path.open(encoding='utf-8-sig',newline='') as handle: rows=list(csv.DictReader(handle))
    assert rows[0]['Client name']=="'=SUM(1,2)"
    assert rows[0]['Customer / access notes']=='Café, "Gate"\nSecond line'

def test_job_export_includes_customer_link_and_configured_custom_field(window,context,customer_id,tmp_path,monkeypatch,click):
    job=JobRecord(customer_id,custom_fields={'weather':'Dry'}); context.db.create_job(job)
    window.refresh_all(); window.tabs.setCurrentIndex(2)
    path=tmp_path/'jobs.csv'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**kw:(str(path),'CSV files (*.csv)'))
    click(window,'Export CSV')
    with path.open(encoding='utf-8-sig',newline='') as handle: rows=list(csv.DictReader(handle))
    assert rows[0]['Customer ID']==str(customer_id)
    assert rows[0]['Customer']=='Mary Window'
    assert rows[0]['Weather']=='Dry'

def test_cancelled_export_writes_no_file(window,tmp_path,monkeypatch,click):
    before=set(tmp_path.rglob('*'))
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**kw:('',''))
    window.tabs.setCurrentIndex(1); click(window,'Export CSV')
    assert set(tmp_path.rglob('*'))==before

def test_automatic_backup_failure_is_visible_without_a_modal(window,monkeypatch):
    class FailedBackup:
        def create_backup_if_due(self): raise OSError('Backup volume unavailable')
    window.backup_manager=FailedBackup(); window.automatic_backup()
    assert 'Automatic backup failed: Backup volume unavailable'==window.backup_label.text()
    window.prepare_shutdown()
    assert not window.backup_timer.isActive()
