"""Tick-box interaction, booking defaults and readable multi-choice exports."""
import csv
from dataclasses import fields

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QFileDialog, QLabel

from customer_app.models import CustomerRecord, JobRecord, ServiceRecord
from customer_app.ui.customer_services import ServiceDialog
from customer_app.ui.forms import JobDialog, CustomerDialog
from tests.ui.test_customer_page import select_customer


def tick(qtbot,grid,choice):
    qtbot.mouseClick(grid.checkboxes[choice],Qt.MouseButton.LeftButton)


def test_service_editor_selects_several_choices_independently_and_reopens(context,customer_id,qtbot,click):
    dialog=ServiceDialog(context.db,context.settings,customer_id);qtbot.addWidget(dialog);dialog.show()
    dialog.name.setText('Inside and screens');dialog.fee.setText('500');dialog.hours.setText('3')
    tick(qtbot,dialog.job_type,'Internal windows');tick(qtbot,dialog.job_type,'Screens')
    assert dialog.job_type.selected_values()==['Internal windows','Screens']
    tick(qtbot,dialog.job_type,'Internal windows')
    assert dialog.job_type.selected_values()==['Screens']
    tick(qtbot,dialog.job_type,'Internal windows');click(dialog,'Save')
    saved=context.db.get_service(dialog.saved_id)
    assert saved['job_type']==['Internal windows','Screens'] and saved['fee']=='500.00' and saved['hours']=='3.00'
    reopened=ServiceDialog(context.db,context.settings,customer_id,dialog.saved_id);qtbot.addWidget(reopened)
    assert reopened.job_type.selected_values()==['Internal windows','Screens']


def test_customer_defaults_use_the_same_grid_and_sync_usual_service(context,customer_id,qtbot):
    dialog=CustomerDialog(context.db,context.settings,customer_id);qtbot.addWidget(dialog)
    grid=dialog.form.widgets['default_job_type']
    grid.checkboxes['Screens'].setChecked(True);grid.checkboxes['Skylights'].setChecked(True)
    dialog.save()
    assert context.db.get_customer(customer_id)['default_job_type']==['External windows','Screens','Skylights']
    assert context.db.list_services(customer_id)[0]['job_type']==['External windows','Screens','Skylights']


def test_booking_inherits_multiple_choices_and_overrides_do_not_change_service(context,customer_id,qtbot):
    db=context.db
    one=db.create_service(ServiceRecord(customer_id,'Inside',['Internal windows','Screens'],fee='500',hours='3'))
    other=db.create_service(ServiceRecord(customer_id,'Outside',['External windows','Skylights'],fee='600',hours='4'))
    dialog=JobDialog(db,context.settings,customer_id=customer_id);qtbot.addWidget(dialog)
    widgets=dialog.form.widgets;widgets['scheduled_date'].setText('unfinished')
    dialog.service.setCurrentIndex(dialog.service.findData(one))
    assert widgets['job_type'].selected_values()==['Internal windows','Screens']
    dialog.service.setCurrentIndex(dialog.service.findData(other))
    assert widgets['job_type'].selected_values()==['External windows','Skylights']
    assert widgets['scheduled_date'].text()=='unfinished'
    widgets['job_type'].checkboxes['Screens'].setChecked(True)
    widgets['scheduled_date'].setText('12/10/2026');dialog.save()
    assert db.get_job(dialog.saved_id)['job_type']==['External windows','Screens','Skylights']
    assert db.get_service(other)['job_type']==['External windows','Skylights']


def test_old_job_retains_multiple_saved_choices_after_profile_change(context,customer_id,qtbot):
    db=context.db;sid=db.create_service(ServiceRecord(customer_id,'Inside',['Internal windows','Screens']))
    jid=db.create_job(db.new_job_for_customer(customer_id,service_id=sid))
    saved=db.get_service(sid)
    db.update_service(sid,ServiceRecord(**{**{f.name:saved[f.name] for f in fields(ServiceRecord)},'job_type':['Skylights']}))
    context.settings.job_type_options.remove('Screens')
    dialog=JobDialog(db,context.settings,job_id=jid);qtbot.addWidget(dialog)
    assert dialog.form.widgets['job_type'].selected_values()==['Internal windows','Screens']
    dialog.form.widgets['notes'].setPlainText('Keep historic types');dialog.save()
    assert db.get_job(jid)['job_type']==['Internal windows','Screens']


def test_job_types_display_and_csv_as_readable_choices(window,context,customer_id,qtbot,tmp_path,monkeypatch,today):
    db=context.db
    sid=db.create_service(ServiceRecord(customer_id,'Inside',['Internal windows','Screens'],fee='500',hours='3'))
    jid=db.create_job(db.new_job_for_customer(customer_id,today.isoformat(),service_id=sid))
    # Custom visits without a named service also render their list on Home.
    custom=db.create_job(JobRecord(customer_id,scheduled_date=today.isoformat(),job_type=['External windows','Skylights']))
    window.refresh_all();select_customer(window,customer_id)
    headers=[window.history.horizontalHeaderItem(i).text() for i in range(window.history.columnCount())]
    assert window.history.item(0,headers.index('Nature of job')).text()=='Internal windows, Screens'
    tree=window.jobs_page.tree
    heads=[tree.headerItem().text(i) for i in range(tree.columnCount())]
    assert window.jobs_page.items[jid].text(heads.index('Nature of job'))=='Internal windows, Screens'
    assert window.home.visits_table.item(1,3).text()=='External windows, Skylights'
    path=tmp_path/'jobs.csv'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),'CSV files (*.csv)'))
    window.export_jobs()
    with path.open(encoding='utf-8-sig',newline='') as handle:rows=list(csv.DictReader(handle))
    assert rows[0]['Nature of job']=='Internal windows, Screens'
    assert rows[0]['Charge / fee (AUD)']=='$500.00' and rows[0]['Number of hours']=='3.00'
    assert rows[1]['Nature of job']=='External windows, Skylights'


@pytest.mark.parametrize('width',[520,650])
def test_job_type_grid_wraps_without_inner_scroll_and_keeps_all_choices(context,customer_id,qtbot,width):
    context.settings.job_type_options=[f'Type {i}' for i in range(20)]
    sid=context.db.create_service(ServiceRecord(customer_id,'Long list',['Type 0','Type 19']))
    dialog=ServiceDialog(context.db,context.settings,customer_id,sid);qtbot.addWidget(dialog)
    dialog.resize(width,760);dialog.show();qtbot.wait(20)
    assert len(dialog.job_type.checkboxes)==20
    assert dialog.job_type.selected_values()==['Type 0','Type 19']
    assert not dialog.job_type.findChildren(QScrollArea)
    assert dialog.findChild(QScrollArea).horizontalScrollBar().maximum()==0
    assert dialog.job_type._columns==(1 if width==520 else 2)


def test_empty_job_type_grid_explains_where_to_add_choices(context,customer_id,qtbot):
    context.settings.job_type_options=[]
    dialog=ServiceDialog(context.db,context.settings,customer_id);qtbot.addWidget(dialog)
    assert any('No job types available' in label.text() for label in dialog.job_type.findChildren(QLabel))
    dialog.name.setText('Unspecified visit');dialog.save()
    assert context.db.get_service(dialog.saved_id)['job_type']==[]
