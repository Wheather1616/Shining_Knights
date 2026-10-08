"""Actual Qt interactions for named services and visit-specific overrides."""
import csv
from dataclasses import fields
from datetime import timedelta

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QDialog, QScrollArea

from customer_app.models import CustomerRecord, JobRecord, ServiceRecord
from customer_app.ui.customer_services import ServiceDialog
from customer_app.ui.forms import JobDialog
from tests.ui.test_customer_page import select_customer
from tests.ui.test_workflows import drive_modal


def service_page(window,customer_id):
    window.refresh_all();select_customer(window,customer_id)
    page=window.customer_page
    page.detail_tabs.setCurrentIndex(page.detail_tabs.indexOf(page.services))
    return page.services


def select_service(page,sid):
    for row,record in enumerate(page.records):
        if record['id']==sid:page.table.selectRow(row);return
    raise AssertionError('Service not shown')


def add_profiles(context,customer_id):
    return [context.db.create_service(ServiceRecord(customer_id,'Indoor windows','Internal windows',['3m ladder'],'500','3',notes='Inside only')),
            context.db.create_service(ServiceRecord(customer_id,'Whole house','Internal + external',['Water-fed pole'],'600','4'))]


def test_add_edit_usual_and_archive_services_through_customer_screen(window,context,customer_id,qtbot,click):
    page=service_page(window,customer_id)
    def fill(dialog):
        qtbot.keyClicks(dialog.name,'Indoor windows')
        qtbot.keyClicks(dialog.fee,'500');qtbot.keyClicks(dialog.hours,'3')
        dialog.job_type.checkboxes['Internal windows'].setChecked(True)
        dialog.equipment.checkboxes['3m ladder'].setChecked(True)
        dialog.notes.setPlainText('Inside only');click(dialog,'Save')
    drive_modal(lambda:click(window,'Add service'),ServiceDialog,fill)
    assert 'Service saved' in page.message.text()
    indoor=next(s for s in page.records if s['name']=='Indoor windows')
    assert indoor['fee']=='500.00' and indoor['hours']=='3.00'
    select_service(page,indoor['id'])
    def edit(dialog):
        assert dialog.name.text()=='Indoor windows'
        dialog.fee.setText('550');click(dialog,'Save')
    drive_modal(lambda:click(window,'Edit service'),ServiceDialog,edit)
    assert context.db.get_service(indoor['id'])['fee']=='550.00'
    select_service(page,indoor['id']);click(window,'Make usual')
    assert context.db.new_job_for_customer(customer_id).service_id==indoor['id']
    assert not page.archive_button.isEnabled()
    original=next(s for s in page.records if s['name']=='Usual service')
    select_service(page,original['id']);click(window,'Archive service')
    assert not context.db.get_service(original['id'])['active']
    assert len(page.records)==1
    qtbot.mouseClick(page.archived,Qt.MouseButton.LeftButton)
    select_service(page,original['id']);click(window,'Restore service')
    assert context.db.get_service(original['id'])['active']


def test_cancel_and_validation_keep_service_editor_without_writing(context,customer_id,qtbot,messages,click):
    before=context.db.list_services(customer_id)
    dialog=ServiceDialog(context.db,context.settings,customer_id);qtbot.addWidget(dialog);dialog.show()
    click(dialog,'Save')
    assert dialog.isVisible() and 'service name' in messages[-1][2]
    dialog.name.setText('Bad fee');dialog.fee.setText('1.001');click(dialog,'Save')
    assert dialog.isVisible() and 'decimal' in messages[-1][2]
    click(dialog,'Cancel')
    assert dialog.result()==QDialog.DialogCode.Rejected and context.db.list_services(customer_id)==before


def test_booking_service_switch_preserves_unfinished_inputs_and_snapshots(context,customer_id,qtbot,click):
    indoor,whole=add_profiles(context,customer_id)
    dialog=JobDialog(context.db,context.settings,customer_id=customer_id);qtbot.addWidget(dialog);dialog.show()
    widgets=dialog.form.widgets
    widgets['scheduled_date'].setText('not yet a date')
    widgets['payment_status'].setCurrentIndex(widgets['payment_status'].findData('Invoiced'))
    widgets['weather'].setCurrentIndex(widgets['weather'].findData('Rain'))
    widgets['notes'].setPlainText('Keep the gate closed')
    dialog.service.setCurrentIndex(dialog.service.findData(indoor))
    assert widgets['scheduled_date'].text()=='not yet a date'
    assert widgets['payment_status'].currentData()=='Invoiced' and widgets['weather'].currentData()=='Rain'
    assert widgets['notes'].toPlainText()=='Keep the gate closed'
    assert widgets['fee'].text()=='500.00' and widgets['hours'].text()=='3.00'
    dialog.service.setCurrentIndex(dialog.service.findData(whole))
    assert widgets['fee'].text()=='600.00' and widgets['hours'].text()=='4.00'
    assert widgets['equipment'].selected_values()==['Water-fed pole']
    widgets['fee'].setText('625');widgets['hours'].setText('4.5');widgets['scheduled_date'].setText('12/10/2026')
    click(dialog,'Save')
    job=context.db.get_job(dialog.saved_id)
    assert (job['service_id'],job['service_name'],job['fee'],job['hours'])==(whole,'Whole house','625.00','4.50')
    assert job['custom_fields']['weather']=='Rain' and job['payment_status']=='Invoiced'
    assert context.db.get_service(whole)['fee']=='600.00'


def test_new_service_notes_change_without_replacing_personal_notes(context,customer_id,qtbot):
    indoor,whole=add_profiles(context,customer_id)
    dialog=JobDialog(context.db,context.settings,customer_id=customer_id);qtbot.addWidget(dialog)
    dialog.service.setCurrentIndex(dialog.service.findData(indoor))
    assert dialog.form.widgets['notes'].toPlainText()=='Inside only'
    dialog.service.setCurrentIndex(dialog.service.findData(whole))
    assert dialog.form.widgets['notes'].toPlainText()==''
    dialog.service.setCurrentIndex(dialog.service.findData(indoor))
    dialog.service.setCurrentIndex(dialog.service.findData(None))
    assert dialog.form.widgets['fee'].text()=='500.00'  # Custom visit keeps entered values.
    dialog.save()
    assert context.db.get_job(dialog.saved_id)['service_id'] is None
    assert context.db.get_job(dialog.saved_id)['service_name']==''


def test_old_job_open_does_not_reload_renamed_or_archived_service(context,customer_id,qtbot,click):
    indoor,_=add_profiles(context,customer_id);db=context.db
    jid=db.create_job(db.new_job_for_customer(customer_id,service_id=indoor))
    profile=db.get_service(indoor)
    db.update_service(indoor,ServiceRecord(**{**{f.name:profile[f.name] for f in fields(ServiceRecord)},'name':'New name','fee':'900'}))
    db.set_service_active(indoor,False)
    dialog=JobDialog(db,context.settings,job_id=jid);qtbot.addWidget(dialog);dialog.show()
    assert '(archived)' in dialog.service.currentText()
    assert dialog.form.widgets['fee'].text()=='500.00'
    dialog.form.widgets['payment_status'].setCurrentIndex(dialog.form.widgets['payment_status'].findData('Paid'))
    click(dialog,'Save')
    assert (db.get_job(jid)['service_name'],db.get_job(jid)['fee'])==('Indoor windows','500.00')
    fresh=JobDialog(db,context.settings,customer_id=customer_id);qtbot.addWidget(fresh)
    assert fresh.service.findData(indoor)==-1


def test_switch_service_on_completed_job_keeps_status_date_and_payment(context,customer_id,qtbot,today):
    indoor,whole=add_profiles(context,customer_id);db=context.db
    visit=db.new_job_for_customer(customer_id,service_id=indoor)
    visit.status='Completed';visit.completed_date=today.isoformat();visit.payment_status='Paid'
    jid=db.create_job(visit)
    dialog=JobDialog(db,context.settings,job_id=jid);qtbot.addWidget(dialog)
    dialog.service.setCurrentIndex(dialog.service.findData(whole));dialog.save()
    saved=db.get_job(jid)
    assert saved['service_name']=='Whole house' and saved['status']=='Completed'
    assert saved['completed_date']==today.isoformat() and saved['payment_status']=='Paid'


def test_service_options_follow_customer_id_and_inactive_jobs_remain_editable(context,customer_id,qtbot):
    indoor,_=add_profiles(context,customer_id)
    other=context.db.create_customer(CustomerRecord(name='Mary Window',default_fee='50'))
    dialog=JobDialog(context.db,context.settings,customer_id=customer_id);qtbot.addWidget(dialog)
    dialog.service.setCurrentIndex(dialog.service.findData(indoor))
    dialog.customer.setCurrentIndex(dialog.customer.findData(other))
    assert dialog.form.widgets['fee'].text()=='50.00' and dialog.service.findData(indoor)==-1
    jid=context.db.create_job(context.db.new_job_for_customer(customer_id,service_id=indoor))
    context.db.set_customer_active(customer_id,False)
    edit=JobDialog(context.db,context.settings,job_id=jid);qtbot.addWidget(edit)
    assert not edit.service.isEnabled()
    edit.form.widgets['fee'].setText('510');edit.save()
    assert context.db.get_job(jid)['fee']=='510.00'


def test_customer_selection_and_archive_filter_do_not_mix_services(window,context,customer_id,qtbot):
    indoor,_=add_profiles(context,customer_id)
    other=context.db.create_customer(CustomerRecord(name='Mary Window'))
    page=service_page(window,customer_id)
    assert indoor in [s['id'] for s in page.records]
    select_customer(window,other)
    assert all(s['customer_id']==other for s in page.records)
    window.customer_search.setText('No matching name')
    assert page.table.rowCount()==0 and not page.add_button.isEnabled()


def test_jobs_home_history_and_csv_show_recorded_service_name(window,context,customer_id,qtbot,today,tmp_path,monkeypatch):
    indoor,whole=add_profiles(context,customer_id);db=context.db
    j1=db.create_job(db.new_job_for_customer(customer_id,today.isoformat(),service_id=indoor))
    j2=db.create_job(db.new_job_for_customer(customer_id,(today+timedelta(days=1)).isoformat(),service_id=whole))
    window.refresh_all();select_customer(window,customer_id)
    headers=[window.history.horizontalHeaderItem(i).text() for i in range(window.history.columnCount())]
    assert window.history.item(0,headers.index('Service')).text()=='Indoor windows'
    jobpage=window.jobs_page
    assert 'Indoor windows' in [jobpage.items[j1].text(i) for i in range(jobpage.tree.columnCount())]
    assert window.home.visits_table.item(0,3).text()=='Indoor windows'
    path=tmp_path/'visits.csv'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),'CSV files (*.csv)'))
    window.export_jobs()
    with path.open(encoding='utf-8-sig',newline='') as handle:rows=list(csv.DictReader(handle))
    assert [(r['Customer service'],r['Charge / fee (AUD)'],r['Number of hours']) for r in rows]==[('Indoor windows','$500.00','3.00'),('Whole house','$600.00','4.00')]


@pytest.mark.parametrize('size',[(1250,820),(900,690)])
def test_services_layout_actions_and_table_fit_supported_window(window,context,customer_id,qtbot,size):
    add_profiles(context,customer_id);page=service_page(window,customer_id)
    window.resize(*size);qtbot.wait(20)
    assert page.table.parentWidget().rect().contains(page.table.geometry())
    assert page.table.height()>=90
    for button in (page.add_button,page.edit_button,page.usual_button,page.archive_button):
        assert page.rect().contains(button.geometry())
        assert button.width()>=button.fontMetrics().horizontalAdvance(button.text())
    assert page.edit_button.geometry().top()>page.table.geometry().bottom()


@pytest.mark.parametrize('width',[520,650])
def test_service_editor_has_numeric_inputs_grid_and_fixed_footer(context,customer_id,qtbot,width):
    dialog=ServiceDialog(context.db,context.settings,customer_id);qtbot.addWidget(dialog)
    dialog.resize(width,620);dialog.show();qtbot.wait(20)
    qtbot.keyClicks(dialog.fee,'500abc.50');qtbot.keyClicks(dialog.hours,'3abc.25')
    assert dialog.fee.text()=='500.50' and dialog.hours.text()=='3.25'
    scroll=dialog.findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum()==0
    assert len(dialog.equipment.checkboxes)==len(context.settings.equipment_options)
    assert not dialog.equipment.findChildren(QScrollArea)


def test_returning_to_archived_service_is_rejected_without_losing_visit_inputs(context,customer_id,qtbot,messages):
    indoor,whole=add_profiles(context,customer_id);db=context.db
    jid=db.create_job(db.new_job_for_customer(customer_id,service_id=indoor));db.set_service_active(indoor,False)
    dialog=JobDialog(db,context.settings,job_id=jid);qtbot.addWidget(dialog)
    dialog.service.setCurrentIndex(dialog.service.findData(whole))
    dialog.form.widgets['scheduled_date'].setText('12/10/2026')
    dialog.service.setCurrentIndex(dialog.service.findData(indoor))
    assert 'available' in messages[-1][2]
    assert dialog.service.currentData()==whole and dialog.form.widgets['fee'].text()=='600.00'
    assert dialog.form.widgets['scheduled_date'].text()=='12/10/2026'


def test_service_editor_keeps_withdrawn_equipment_and_job_type(context,customer_id,qtbot):
    db=context.db;usual=db.list_services(customer_id)[0]
    context.settings.equipment_options.remove('3m ladder')
    context.settings.job_type_options.remove('External windows')
    dialog=ServiceDialog(db,context.settings,customer_id,usual['id']);qtbot.addWidget(dialog)
    assert dialog.job_type.selected_values()==['External windows']
    assert dialog.equipment.selected_values()==['3m ladder']
    dialog.fee.setText('500');dialog.save()
    assert dialog.saved_id==usual['id']
    assert db.get_service(usual['id'])['equipment']==['3m ladder']
    # The withdrawn choice stays on historical profiles; new visits use available choices.
    assert db.new_job_for_customer(customer_id).equipment==[]
