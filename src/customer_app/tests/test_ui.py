import os
os.environ['QT_QPA_PLATFORM']='offscreen'

from dataclasses import asdict
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from customer_app.config import AppSettings, FieldDefinition, SettingsStore
from customer_app.database import CustomerDatabase
from customer_app.models import CustomerRecord
from customer_app.ui.forms import CustomerDialog, JobDialog, RecordForm
from customer_app.ui.main_window import CustomerMainWindow

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def setup(tmp_path):
    settings=AppSettings(db_path=tmp_path/'customers.db')
    settings.customer_fields.append(FieldDefinition('gate_code','Gate code',browse_column=True))
    settings.job_fields.append(FieldDefinition('weather','Weather','dropdown',options=['Dry','Rain']))
    store=SettingsStore(tmp_path/'settings.json'); store.save(settings)
    db=CustomerDatabase(settings.db_path,settings,key_hex='12'*32)
    return db,settings,store


def test_customer_and_job_forms_save_end_to_end(app,setup):
    db,settings,store=setup
    c=CustomerDialog(db,settings)
    c.form.widgets['name'].setText('Mary Window')
    c.form.widgets['address_line_1'].setText('1 Ocean Street')
    c.form.widgets['suburb'].setText('Coogee')
    c.form.widgets['phone'].setText('0412 345 678')
    c.form.frequency.setCurrentText('Every 8 weeks')
    c.form.widgets['default_fee'].setText('180.00')
    c.form.widgets['gate_code'].setText('0042')
    c.form.widgets['default_job_type'].setCurrentText('External windows')
    c.save()
    assert c.result() == QDialog.DialogCode.Accepted
    saved=db.get_customer(c.saved_id)
    assert saved['frequency_value'] == 8
    assert saved['custom_fields']['gate_code'] == '0042'
    j=JobDialog(db,settings,customer_id=c.saved_id)
    assert j.form.widgets['fee'].text() == '180.00'
    assert j.form.widgets['scheduled_date'].text() == ''
    j.form.widgets['status'].setCurrentText('Completed')
    assert j.form.widgets['completed_date'].text() == date.today().strftime('%d/%m/%Y')
    j.form.widgets['weather'].setCurrentText('Dry')
    j.save()
    assert j.result() == QDialog.DialogCode.Accepted
    assert db.customer_summary(c.saved_id)['jobs_completed'] == 1
    assert db.get_job(j.saved_id)['custom_fields']['weather'] == 'Dry'
    edit=JobDialog(db,settings,job_id=j.saved_id)
    edit.form.widgets['status'].setCurrentText('Scheduled')
    assert edit.form.widgets['completed_date'].text() == ''
    edit.save()
    assert db.customer_summary(c.saved_id)['jobs_completed'] == 0


def test_main_window_grouping_and_profile(app,setup):
    db,settings,store=setup
    c=db.create_customer(CustomerRecord(name='Alex',suburb='Coogee'))
    other=db.create_customer(CustomerRecord(name='Alex',suburb='Randwick'))
    db.create_job(db.new_job_for_customer(c)); db.create_job(db.new_job_for_customer(other))
    w=CustomerMainWindow(db=db,settings_store=store,enable_backups=False)
    w.show(); app.processEvents()
    assert w.customer_table.rowCount() == 2
    w.customer_table.selectRow(0); app.processEvents()
    assert w.selected_customer == c
    assert w.history.rowCount() == 1
    w.group_by.setCurrentIndex(w.group_by.findData('customer')); app.processEvents()
    assert w.jobs_tree.topLevelItemCount() == 2
    w.customer_search.setText('Randwick'); app.processEvents()
    assert w.customer_table.rowCount() == 1
    assert w.selected_customer is None
    w.close()


def test_settings_apply_and_custom_column(app,setup,monkeypatch):
    monkeypatch.setattr(QMessageBox,'information',lambda *args:QMessageBox.StandardButton.Ok)
    db,settings,store=setup
    w=CustomerMainWindow(db=db,settings_store=store,enable_backups=False)
    table=w.configuration.tables['customers']
    table.cellWidget(0,1).setText('Customer name')
    w.configuration.lookups['equipment_options'].setPlainText('Ladder\nWater-fed pole')
    w.configuration.save()
    assert w.settings.customer_fields[0].label == 'Customer name'
    assert w.customer_table.horizontalHeaderItem(0).text() == 'Customer name'
    assert w.db.settings.equipment_options == ['Ladder','Water-fed pole']
    assert store.load().equipment_options == ['Ladder','Water-fed pole']
    w.close()
