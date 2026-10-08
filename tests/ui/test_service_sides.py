"""Conditional side controls, persistence, booking overrides and readable exports."""
import csv
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QScrollArea
from customer_app.models import ServiceRecord, JobRecord
from customer_app.ui.customer_services import ServiceDialog
from customer_app.ui.forms import JobDialog, CustomerDialog
from tests.ui.test_customer_page import select_customer


def test_ticking_reveals_three_exclusive_choices_beneath_each_type(context,customer_id,qtbot):
    dialog=ServiceDialog(context.db,context.settings,customer_id);qtbot.addWidget(dialog);dialog.show()
    grid=dialog.job_type
    assert grid.side_frames['Screens'].isHidden()
    qtbot.mouseClick(grid.checkboxes['Screens'],Qt.MouseButton.LeftButton)
    assert not grid.side_frames['Screens'].isHidden()
    buttons=grid.side_buttons['Screens']
    assert [b.text() for b in buttons.values()]==['Inside','Outside','Both']
    qtbot.mouseClick(buttons['inside'],Qt.MouseButton.LeftButton)
    qtbot.mouseClick(buttons['outside'],Qt.MouseButton.LeftButton)
    assert grid.selected_sides()=={'Screens':'outside'}
    assert not buttons['inside'].isChecked()
    grid.checkboxes['Skylights'].setChecked(True)
    grid.side_buttons['Skylights']['both'].click()
    assert grid.selected_sides()=={'Screens':'outside','Skylights':'both'}
    grid.checkboxes['Screens'].setChecked(False)
    assert grid.side_frames['Screens'].isHidden()
    assert grid.selected_sides()=={'Skylights':'both'}
    grid.checkboxes['Screens'].setChecked(True)
    assert grid.selected_sides()['Screens']=='outside'
    qtbot.wait(10)
    frame=grid.side_frames['Screens'];checkbox=grid.checkboxes['Screens']
    assert frame.mapTo(grid,frame.rect().topLeft()).y()>checkbox.mapTo(grid,checkbox.rect().bottomLeft()).y()


def test_keyboard_side_choice_does_not_submit_editor(context,customer_id,qtbot):
    dialog=ServiceDialog(context.db,context.settings,customer_id);qtbot.addWidget(dialog);dialog.show()
    dialog.job_type.checkboxes['Screens'].setChecked(True)
    button=dialog.job_type.side_buttons['Screens']['both'];button.setFocus()
    qtbot.keyClick(button,Qt.Key.Key_Space)
    assert dialog.job_type.selected_sides()=={'Screens':'both'}
    assert dialog.saved_id is None and dialog.isVisible()


def test_save_reopen_and_untick_remove_only_that_types_scope(context,customer_id,qtbot):
    db=context.db;dialog=ServiceDialog(db,context.settings,customer_id);qtbot.addWidget(dialog)
    dialog.name.setText('Windows and screens');dialog.fee.setText('500');dialog.hours.setText('3')
    grid=dialog.job_type
    for name,side in [('Internal windows','inside'),('Screens','both')]:
        grid.checkboxes[name].setChecked(True);grid.side_buttons[name][side].click()
    dialog.save();sid=dialog.saved_id
    saved=db.get_service(sid)
    assert saved['job_type_sides']=={'Internal windows':'inside','Screens':'both'}
    assert (saved['fee'],saved['hours'])==('500.00','3.00')
    edit=ServiceDialog(db,context.settings,customer_id,sid);qtbot.addWidget(edit)
    assert edit.job_type.selected_sides()==saved['job_type_sides']
    edit.job_type.checkboxes['Internal windows'].setChecked(False);edit.save()
    assert db.get_service(sid)['job_type_sides']=={'Screens':'both'}


def test_previous_services_open_and_save_without_assigning_a_scope(context,customer_id,qtbot):
    db=context.db;sid=db.list_services(customer_id)[0]['id']
    dialog=ServiceDialog(db,context.settings,customer_id,sid);qtbot.addWidget(dialog)
    assert dialog.job_type.selected_sides()=={}
    assert not dialog.job_type.side_frames['External windows'].isHidden()
    assert not any(b.isChecked() for b in dialog.job_type.side_buttons['External windows'].values())
    dialog.save();assert db.get_service(sid)['job_type_sides']=={}


def test_customer_defaults_and_usual_service_share_scopes(context,customer_id,qtbot):
    dialog=CustomerDialog(context.db,context.settings,customer_id);qtbot.addWidget(dialog)
    grid=dialog.form.widgets['default_job_type'];grid.side_buttons['External windows']['outside'].click()
    dialog.save()
    assert context.db.get_customer(customer_id)['default_job_type_sides']=={'External windows':'outside'}
    assert context.db.list_services(customer_id)[0]['job_type_sides']=={'External windows':'outside'}


def test_switching_services_replaces_scope_and_keeps_unfinished_visit_input(context,customer_id,qtbot):
    db=context.db
    one=db.create_service(ServiceRecord(customer_id,'Inside',['Screens'],job_type_sides={'Screens':'inside'}))
    two=db.create_service(ServiceRecord(customer_id,'Both',['Screens'],job_type_sides={'Screens':'both'}))
    empty=db.create_service(ServiceRecord(customer_id,'Unconfirmed',['Screens']))
    dialog=JobDialog(db,context.settings,customer_id=customer_id);qtbot.addWidget(dialog)
    widgets=dialog.form.widgets;widgets['scheduled_date'].setText('unfinished')
    widgets['weather'].setCurrentIndex(widgets['weather'].findData('Dry'))
    for sid,expected in [(one,{'Screens':'inside'}),(two,{'Screens':'both'}),(empty,{})]:
        dialog.service.setCurrentIndex(dialog.service.findData(sid))
        assert widgets['job_type'].selected_sides()==expected
        assert widgets['scheduled_date'].text()=='unfinished'
        assert widgets['weather'].currentData()=='Dry'
    widgets['job_type'].side_buttons['Screens']['outside'].click()
    widgets['scheduled_date'].setText('12/10/2026');dialog.save()
    assert db.get_job(dialog.saved_id)['job_type_sides']=={'Screens':'outside'}
    assert db.get_service(empty)['job_type_sides']=={}
    reopened=JobDialog(db,context.settings,job_id=dialog.saved_id);qtbot.addWidget(reopened)
    assert reopened.form.widgets['job_type'].selected_sides()=={'Screens':'outside'}


@pytest.mark.parametrize('width',[520,650])
def test_selected_side_controls_fit_narrow_and_wide_forms(context,customer_id,qtbot,width):
    types=context.settings.job_type_options
    sid=context.db.create_service(ServiceRecord(customer_id,'All types',types,job_type_sides={t:'both' for t in types}))
    dialog=ServiceDialog(context.db,context.settings,customer_id,sid);qtbot.addWidget(dialog)
    dialog.resize(width,760);dialog.show();qtbot.wait(20)
    scroll=dialog.findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum()==0
    assert not dialog.job_type.findChildren(QScrollArea)
    for frame in dialog.job_type.side_frames.values():
        assert not frame.isHidden()
    for buttons in dialog.job_type.side_buttons.values():
        for button in buttons.values():
            assert button.width()>=button.fontMetrics().horizontalAdvance(button.text())+4
    assert dialog.job_type.selected_sides()=={t:'both' for t in types}


def test_side_choices_visible_in_history_jobs_home_and_csv(window,context,customer_id,qtbot,tmp_path,monkeypatch,today):
    db=context.db
    sid=db.create_service(ServiceRecord(customer_id,'Windows',['Screens'],job_type_sides={'Screens':'both'}))
    jid=db.create_job(db.new_job_for_customer(customer_id,today.isoformat(),service_id=sid))
    db.create_job(JobRecord(customer_id,scheduled_date=today.isoformat(),job_type=['Skylights'],job_type_sides={'Skylights':'outside'}))
    window.refresh_all();select_customer(window,customer_id)
    headers=[window.history.horizontalHeaderItem(i).text() for i in range(window.history.columnCount())]
    assert window.history.item(0,headers.index('Nature of job')).text()=='Screens (Both)'
    heads=[window.jobs_page.tree.headerItem().text(i) for i in range(window.jobs_page.tree.columnCount())]
    assert window.jobs_page.items[jid].text(heads.index('Nature of job'))=='Screens (Both)'
    assert window.home.visits_table.item(1,3).text()=='Skylights (Outside)'
    path=tmp_path/'jobs.csv';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),'CSV files (*.csv)'))
    window.export_jobs()
    with path.open(encoding='utf-8-sig',newline='') as handle:rows=list(csv.DictReader(handle))
    assert rows[0]['Nature of job']=='Screens (Both)'
    assert rows[1]['Nature of job']=='Skylights (Outside)'
