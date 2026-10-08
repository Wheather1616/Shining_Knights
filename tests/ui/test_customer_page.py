"""Customer workspace regressions: IDs, config, actions and readable job geometry."""
import csv
from dataclasses import fields

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox

from customer_app.config import FieldDefinition
from customer_app.models import CustomerRecord, JobRecord
from tests.ui.test_workflows import drive_modal
from customer_app.ui.forms import JobDialog
from tests.ui.test_theme import contrast


def select_customer(window, customer_id):
    window.tabs.setCurrentIndex(1)
    for row in range(window.customer_table.rowCount()):
        if window.customer_table.item(row, 0).data(Qt.ItemDataRole.UserRole) == customer_id:
            window.customer_table.selectRow(row)
            return
    raise AssertionError('Customer was not in the directory')


def test_empty_directory_and_unselected_workspace_disable_actions(window, context, customer_id):
    page = window.customer_page
    assert page.stack.currentIndex() == 0
    assert not page.edit_customer_button.isEnabled()
    assert not page.add_job_button.isEnabled()
    assert not page.edit_job_button.isEnabled()
    assert '0 customers' == page.count.text()
    window.refresh_all()
    assert page.count.text() == '1 customer'
    select_customer(window, customer_id)
    assert page.stack.currentIndex() == 1
    assert page.history_empty.isVisible()
    assert page.add_job_button.isEnabled()
    assert not page.edit_job_button.isEnabled()


def test_same_named_customers_keep_separate_details_jobs_and_selection(window, context, customer_id):
    first = context.db.create_job(JobRecord(customer_id, status='Completed', completed_date='2026-10-01', fee='180'))
    other = context.db.create_customer(CustomerRecord(name='Mary Window', suburb='Randwick', default_fee='25'))
    second = context.db.create_job(JobRecord(other, scheduled_date='2026-10-05', fee='25'))
    window.refresh_all()
    select_customer(window, customer_id)
    assert page_job_ids(window) == {first}
    assert window.customer_page.summary['jobs_completed'].text() == '1'
    select_customer(window, other)
    assert page_job_ids(window) == {second}
    assert 'Randwick' in window.profile.text()
    assert window.customer_page.summary['jobs_completed'].text() == '0'
    window.refresh_all()
    assert window.selected_customer == other
    assert page_job_ids(window) == {second}


def page_job_ids(window):
    return {window.history.item(row, 0).data(Qt.ItemDataRole.UserRole) for row in range(window.history.rowCount())}


def test_search_no_matches_clears_context_and_counts(window, context, customer_id, qtbot):
    context.db.create_job(context.db.new_job_for_customer(customer_id))
    window.refresh_all(); select_customer(window, customer_id)
    qtbot.keyClicks(window.customer_search, 'No such customer')
    assert window.customer_page.count.text() == '0 customers'
    assert window.customer_page.directory_empty.isVisible()
    assert 'No matching' in window.customer_page.directory_empty.text()
    assert window.selected_customer is None
    assert window.history.rowCount() == 0
    assert window.customer_page.job_count.text() == '0 linked jobs'
    assert not window.customer_page.add_job_button.isEnabled()


def test_inactive_customer_cannot_add_job_and_can_be_reactivated(window, context, customer_id, monkeypatch, click):
    context.db.set_customer_active(customer_id, False)
    window.inactive.setChecked(True)
    select_customer(window, customer_id)
    page = window.customer_page
    assert page.status.text() == 'Inactive'
    assert not page.add_job_button.isEnabled()
    page.detail_tabs.setCurrentIndex(2)
    assert page.activation_button.text() == 'Activate customer'
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **kw: QMessageBox.StandardButton.Yes)
    click(window, 'Activate customer')
    assert page.status.text() == 'Active'
    assert page.add_job_button.isEnabled()
    assert page.activation_button.text() == 'Deactivate customer'


def test_tabs_show_notes_all_custom_fields_and_edit_the_selected_linked_job(window, context, customer_id, qtbot, click, today):
    context.settings.customer_fields.append(FieldDefinition('access_flags', 'Access flags', 'multiselect', options=['Dog', 'Gate']))
    context.store.save(context.settings); window.apply_settings(context.settings)
    record = context.db.get_customer(customer_id)
    record = {field.name: record[field.name] for field in fields(CustomerRecord)}
    record['notes'] = '<b>Keep as text</b>\nSecond line'
    record['custom_fields']['access_flags'] = ['Gate']
    context.db.update_customer(customer_id, CustomerRecord(**record))
    job = context.db.create_job(JobRecord(customer_id, fee='180', custom_fields={'weather': 'Dry'}))
    window.refresh_all(); select_customer(window, customer_id)
    page = window.customer_page
    page.detail_tabs.setCurrentIndex(2)
    values = [label.text() for label in page.service_content.findChildren(QLabel)]
    assert 'Gate code' in values and '0042' in values
    assert 'Access flags' in values and 'Gate' in values
    caption = next(label for label in page.service_content.findChildren(QLabel) if label.text() == 'Frequency')
    qtbot.waitUntil(lambda: caption.width() >= caption.fontMetrics().horizontalAdvance('Frequency'))
    page.detail_tabs.setCurrentIndex(3)
    assert page.notes.toPlainText() == '<b>Keep as text</b>\nSecond line'
    page.detail_tabs.setCurrentIndex(0)
    window.history.selectRow(0)
    assert page.edit_job_button.isEnabled()
    def edit(dialog):
        assert dialog.customer.currentData() == customer_id
        dialog.form.widgets['fee'].setText('195.00')
        click(dialog, 'Save')
    drive_modal(lambda: click(window, 'Edit selected job'), JobDialog, edit)
    assert context.db.get_job(job)['fee'] == '195.00'
    assert window.selected_customer == customer_id
    assert not page.edit_job_button.isEnabled()


def test_custom_job_columns_and_labels_survive_the_compact_layout(window, context, customer_id):
    weather = next(field for field in context.settings.job_fields if field.key == 'weather')
    weather.browse_column = True
    fee = next(field for field in context.settings.job_fields if field.key == 'fee')
    fee.label = 'Agreed charge'
    context.db.create_job(JobRecord(customer_id, fee='180', custom_fields={'weather': 'Rain'}))
    window.apply_settings(context.settings); select_customer(window, customer_id)
    headers = [window.history.horizontalHeaderItem(column).text() for column in range(window.history.columnCount())]
    assert 'Agreed charge' in headers and 'Weather' in headers
    assert 'Scheduled' in headers and 'Completed' in headers
    assert 'Payment method' in headers and 'Payment status' in headers
    assert window.history.item(0, headers.index('Agreed charge')).text() == '$180.00'
    assert window.history.item(0, headers.index('Weather')).text() == 'Rain'


@pytest.mark.parametrize('size', [(1250, 820), (900, 690)])
def test_long_details_and_notes_do_not_collapse_job_rows(window, context, customer_id, qtbot, size):
    with context.db.connect() as connection:
        connection.execute('UPDATE customers SET address_line_1=?, email=?, notes=? WHERE id=?',
            ('A long street address ' * 20, 'long-address' * 12 + '@example.com', 'Long note\n' * 200, customer_id))
    context.db.create_job(context.db.new_job_for_customer(customer_id))
    window.refresh_all(); select_customer(window, customer_id)
    window.resize(*size)
    qtbot.waitUntil(lambda: window.history.viewport().height() >= 90)
    assert window.customer_page.overview_scroll.height() <= 260
    assert window.history.rowCount() == 1
    item_rect = window.history.visualItemRect(window.history.item(0, 0))
    assert window.history.viewport().rect().contains(item_rect.topLeft())
    assert item_rect.bottom() < window.history.viewport().height()
    assert window.customer_page.splitter.sizes()[0] >= 230
    assert window.customer_page.add_job_button.geometry().bottom() < window.history.geometry().top()
    assert window.customer_page.edit_job_button.geometry().bottom() < window.history.geometry().top()


def test_primary_job_button_has_readable_fill_and_normal_summary_is_visible(window, context, customer_id, qtbot):
    window.refresh_all(); select_customer(window, customer_id)
    page = window.customer_page
    window.resize(900, 690)
    page.add_job_button.ensurePolished()
    palette = page.add_job_button.palette()
    assert contrast(palette.color(QPalette.ColorRole.ButtonText), palette.color(QPalette.ColorRole.Button)) >= 4.5
    qtbot.waitUntil(lambda: page.overview_scroll.height() >= 210)
    assert page.overview_scroll.verticalScrollBar().maximum() == 0


def test_directory_export_respects_the_active_search(window, context, customer_id, tmp_path, monkeypatch, click):
    context.db.create_customer(CustomerRecord(name='Other Customer', suburb='Randwick'))
    window.refresh_all(); window.tabs.setCurrentIndex(1)
    window.customer_search.setText('Coogee')
    output = tmp_path / 'filtered.csv'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **kw: (str(output), 'CSV files (*.csv)'))
    click(window, 'Export CSV')
    with output.open(encoding='utf-8-sig', newline='') as handle: rows = list(csv.DictReader(handle))
    assert [row['ID'] for row in rows] == [str(customer_id)]
