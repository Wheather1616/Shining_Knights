"""Real form interaction, explicit choices and compact directory regression checks."""
import csv
from dataclasses import asdict

import pytest
from PySide6.QtCore import QDate, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QAbstractItemView, QCheckBox, QFileDialog, QScrollArea, QSpinBox

from customer_app.models import CustomerRecord, JobRecord
from customer_app.ui.form_controls import ChoiceGrid, DateInput
from customer_app.ui.forms import CustomerDialog, RecordForm
from tests.ui.test_customer_page import select_customer


def form_for(context, qtbot, **values):
    form = RecordForm(context.settings, 'customers', asdict(CustomerRecord(first_name='Mary', **values)))
    qtbot.addWidget(form)
    form.resize(700, 1200)
    form.show()
    return form


@pytest.mark.parametrize('unit', ['days', 'weeks', 'months', 'years'])
def test_frequency_uses_number_and_period_and_one_off_round_trips(context, qtbot, unit):
    form = form_for(context, qtbot)
    number = form.widgets['frequency_value']
    period = form.widgets['frequency_unit']
    assert isinstance(number, QSpinBox)
    assert number.value() == 0 and not period.isEnabled()
    assert form.values()['frequency_value'] is None and form.values()['frequency_unit'] == ''
    number.setValue(17)
    assert period.isEnabled()
    period.setCurrentIndex(period.findData(unit))
    cid = context.db.create_customer(CustomerRecord(**form.values()))
    assert context.db.get_customer(cid)['frequency_value'] == 17
    assert context.db.get_customer(cid)['frequency_unit'] == unit
    number.setValue(0)
    assert not period.isEnabled()
    context.db.update_customer(cid, CustomerRecord(**form.values()))
    assert context.db.get_customer(cid)['frequency_value'] is None
    assert context.db.get_customer(cid)['frequency_unit'] == ''


@pytest.mark.parametrize('key,typed,expected', [('phone','0457abc516182','0457516182'), ('postcode','02ab34','0234'),
    ('default_fee','150abc.50','150.50'), ('default_hours','1abc.25','1.25')])
def test_numeric_inputs_reject_letters_and_keep_leading_zeroes(context, qtbot, key, typed, expected):
    form = form_for(context, qtbot)
    widget = form.widgets[key]
    qtbot.keyClicks(widget, typed)
    assert widget.text() == expected
    cid = context.db.create_customer(CustomerRecord(**form.values()))
    assert context.db.get_customer(cid)[key] == expected


@pytest.mark.parametrize('field,value,message', [('phone','12345','10 to 15'), ('postcode','123','four digits'),
    ('email','missing-at.example.com','email'), ('email','a@@example.com','email')])
def test_save_checks_phone_postcode_and_email_and_keeps_input(context, qtbot, click, messages, field, value, message):
    dialog = CustomerDialog(context.db, context.settings)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.form.widgets['first_name'].setText('Mary')
    dialog.form.widgets[field].setText(value)
    click(dialog, 'Save')
    assert dialog.isVisible() and dialog.saved_id is None
    assert not context.db.list_customers()
    assert message in messages[-1][2]
    assert dialog.form.widgets[field].text() == value


def send_wheel(widget):
    event = QWheelEvent(QPointF(5,5), QPointF(widget.mapToGlobal(QPoint(5,5))), QPoint(), QPoint(0,120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    from PySide6.QtWidgets import QApplication
    QApplication.sendEvent(widget, event)


@pytest.mark.parametrize('key', ['state','default_payment_type','frequency_unit'])
def test_wheel_does_not_change_dropdown_but_explicit_selection_does(context, qtbot, key):
    form = form_for(context, qtbot)
    form.widgets['frequency_value'].setValue(2)
    widget = form.widgets[key]
    widget.setCurrentIndex(1)
    widget.setFocus()
    before = widget.currentData()
    send_wheel(widget)
    assert widget.currentData() == before
    qtbot.keyClick(widget, Qt.Key.Key_Down)
    assert widget.currentIndex() == 2  # Keyboard accessibility is retained.
    widget.showPopup()
    view = widget.view()
    index = widget.model().index(3, 0)
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.visualRect(index).center())
    assert widget.currentIndex() == 3


def test_wheel_does_not_change_frequency_number(context, qtbot):
    form = form_for(context, qtbot)
    number = form.widgets['frequency_value']
    number.setValue(8)
    number.setFocus()
    send_wheel(number)
    assert number.value() == 8


def test_calendar_opens_selects_real_day_and_can_be_cleared(context, qtbot):
    form = form_for(context, qtbot)
    widget = form.widgets['first_service_date']
    assert isinstance(widget, DateInput)
    assert widget.text() == ''
    qtbot.keyClick(widget, Qt.Key.Key_Down, modifier=Qt.KeyboardModifier.AltModifier)
    qtbot.waitUntil(lambda: widget.popup.isVisible())
    widget.calendar.setCurrentPage(2026, 10)
    view = widget.calendar.findChild(QAbstractItemView)
    matches = [view.model().index(row, column) for row in range(1, view.model().rowCount())
               for column in range(view.model().columnCount()) if str(view.model().index(row,column).data()) == '12']
    assert len(matches) == 1
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.visualRect(matches[0]).center())
    assert widget.text() == '12/10/2026'
    assert form.values()['first_service_date'] == '2026-10-12'
    assert not widget.popup.isVisible()
    widget.clear()
    assert form.values()['first_service_date'] == ''


def test_equipment_grid_shows_every_choice_and_saved_choices_without_inner_scroll(context, qtbot):
    context.settings.equipment_options = [f'Equipment {i}' for i in range(20)]
    form = form_for(context, qtbot, default_equipment=['Retired ladder'])
    grid = form.widgets['default_equipment']
    assert isinstance(grid, ChoiceGrid)
    assert len(grid.checkboxes) == 21
    assert not grid.findChildren(QScrollArea)
    qtbot.mouseClick(grid.checkboxes['Equipment 0'], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(grid.checkboxes['Equipment 19'], Qt.MouseButton.LeftButton)
    assert form.values()['default_equipment'] == ['Equipment 0','Equipment 19','Retired ladder']
    form.resize(480, 1600)
    qtbot.waitUntil(lambda: grid._columns == 1)
    assert all(check.isVisible() for check in grid.checkboxes.values())


def test_empty_equipment_grid_explains_how_to_add_choices(context, qtbot):
    context.settings.equipment_options = []
    form = form_for(context, qtbot)
    grid = form.widgets['default_equipment']
    grid.resize(300, 60)
    qtbot.wait(10)
    assert grid.empty_label.isVisible()
    assert form.values()['default_equipment'] == []


def test_separate_names_create_and_edit_without_changing_linked_job(context, qtbot, click):
    dialog = CustomerDialog(context.db, context.settings)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.form.widgets['first_name'].setText('Mary Jane')
    dialog.form.widgets['last_name'].setText('van Dijk')
    dialog.form.widgets['phone'].setText('0457516182')
    dialog.form.widgets['email'].setText('mary@example.com')
    dialog.form.widgets['default_fee'].setText('150')
    dialog.form.widgets['default_hours'].setText('1.5')
    with qtbot.waitSignal(dialog.accepted):
        click(dialog, 'Save')
    cid = dialog.saved_id
    jid = context.db.create_job(context.db.new_job_for_customer(cid))
    edited = CustomerDialog(context.db, context.settings, cid)
    qtbot.addWidget(edited)
    edited.show()
    assert edited.form.widgets['first_name'].text() == 'Mary Jane'
    assert edited.form.widgets['last_name'].text() == 'van Dijk'
    edited.form.widgets['last_name'].setText('Brown')
    with qtbot.waitSignal(edited.accepted):
        click(edited, 'Save')
    assert context.db.get_customer(cid)['name'] == 'Mary Jane Brown'
    assert context.db.list_customers('Brown')[0]['id'] == cid
    assert context.db.get_job(jid)['customer_id'] == cid
    assert context.db.get_job(jid)['fee'] == '150.00' and context.db.get_job(jid)['hours'] == '1.50'


def test_legacy_name_is_preserved_until_explicitly_split(context, customer_id, qtbot, click):
    dialog = CustomerDialog(context.db, context.settings, customer_id)
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.form.widgets['first_name'].text() == 'Mary Window'
    assert dialog.form.widgets['last_name'].text() == ''
    click(dialog, 'Save')
    assert context.db.get_customer(customer_id)['name'] == 'Mary Window'


def test_fee_and_hours_are_beside_each_other_with_no_automatic_price_calculation(context, qtbot):
    form = form_for(context, qtbot, default_fee='150', default_hours='1.5')
    fee, hours = form.widgets['default_fee'], form.widgets['default_hours']
    assert fee.parentWidget() == hours.parentWidget()
    assert fee.geometry().right() < hours.geometry().left()
    hours.setText('2.25')
    assert form.values()['default_fee'] == '150' and form.values()['default_hours'] == '2.25'


def test_compact_directory_and_details_toggle_keep_selection_and_configured_fields(window, context, customer_id, click):
    window.refresh_all()
    select_customer(window, customer_id)
    page = window.customer_page
    item = window.customer_table.item(0,0)
    assert len(item.text().splitlines()) == 3
    assert 'Phone number' in item.toolTip()
    click(page, 'More detail')
    assert '0412 345 678' in window.customer_table.item(0,0).text()
    assert window.selected_customer == customer_id
    click(page, 'Compact list')
    assert len(window.customer_table.item(0,0).text().splitlines()) == 3
    assert window.selected_customer == customer_id


def test_csv_keeps_combined_name_and_exports_separate_names_and_hours(window, context, tmp_path, monkeypatch):
    cid = context.db.create_customer(CustomerRecord(first_name='Mary', last_name='Brown', default_hours='1.5'))
    context.db.create_job(context.db.new_job_for_customer(cid))
    window.refresh_all()
    path = tmp_path / 'customers.csv'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a,**k: (str(path),'CSV files (*.csv)'))
    window.export_customers()
    with path.open(encoding='utf-8-sig', newline='') as handle:
        row = next(csv.DictReader(handle))
    assert row['Client name'] == 'Mary Brown' and row['First name'] == 'Mary' and row['Last name'] == 'Brown'
    assert row['Number of hours'] == '1.50'
    path = tmp_path / 'jobs.csv'
    window.export_jobs()
    with path.open(encoding='utf-8-sig', newline='') as handle:
        row = next(csv.DictReader(handle))
    assert row['Customer ID'] == str(cid) and row['Number of hours'] == '1.50'


@pytest.mark.parametrize('size', [(1250,820), (900,690)])
def test_customer_layout_has_visible_titles_badges_and_unclipped_summary(window, context, customer_id, qtbot, size):
    context.db.create_job(JobRecord(customer_id, status='Completed', completed_date='2026-10-02', payment_status='Paid'))
    window.refresh_all()
    select_customer(window, customer_id)
    window.resize(*size)
    qtbot.wait(10)
    page = window.customer_page
    assert page.overview_scroll.verticalScrollBar().maximum() == 0
    assert page.job_history_title.width() >= page.job_history_title.fontMetrics().horizontalAdvance('Job history')
    assert page.job_count.width() >= page.job_count.fontMetrics().horizontalAdvance('1 linked job')
    assert page.history.parentWidget().rect().contains(page.history.geometry())
    assert page.edit_job_button.geometry().bottom() < page.history.geometry().top()
    assert page.history.badge_columns
    delegate = page.history.itemDelegate()
    for column in page.history.badge_columns:
        assert page.history.item(0,column).text() in delegate.COLOURS
