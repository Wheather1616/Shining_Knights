"""Jobs workspace regressions against real widgets and an encrypted fixture DB."""
import csv
from datetime import date

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QPalette, QPixmap
from PySide6.QtWidgets import QFileDialog

from customer_app.config import FieldDefinition
from customer_app.models import CustomerRecord, JobRecord
from customer_app.ui import jobs_page
from customer_app.ui.forms import JobDialog
from customer_app.ui.styles.tokens import TOKENS
from tests.ui.test_theme import contrast
from tests.ui.test_workflows import drive_modal


def add_job(context, customer_id, **values):
    return context.db.create_job(JobRecord(customer_id, **values))


def test_empty_jobs_page_has_clear_guidance_and_disabled_actions(window, qtbot):
    window.tabs.setCurrentIndex(2)
    page = window.jobs_page
    assert page.tree.topLevelItemCount() == 0
    assert page.empty.isVisible()
    assert 'No jobs yet' in page.empty.text()
    assert not page.select_all.isEnabled()
    assert not page.export_button.isEnabled()
    assert not page.edit_button.isEnabled()
    assert not page.complete_button.isEnabled()
    assert page.detail_stack.currentWidget() is page.detail_empty
    window.export_selected_jobs()  # No checked records cannot start a file export.


def test_group_dates_use_chosen_date_without_substituting_another(window, context, customer_id, today):
    add_job(context, customer_id, scheduled_date='2026-10-01', completed_date='2026-10-02', status='Completed', fee='0.10')
    second = add_job(context, customer_id, completed_date='2026-09-30', status='Completed', fee='0.20')
    third = add_job(context, customer_id, scheduled_date='2026-10-01', fee=None)
    window.refresh_all()
    page = window.jobs_page
    assert page.groups[('date', '2026-10-01')].childCount() == 2
    assert '1 fee unset' in page.groups[('date', '2026-10-01')].text(0)
    assert 'Unscheduled' in page.groups[('date', '')].text(0)
    assert page.groups[('date', '')].child(0).data(0, Qt.ItemDataRole.UserRole) == second
    page.group_by.setCurrentIndex(page.group_by.findData('completed'))
    assert set(page.groups) == {('completed', '2026-10-02'), ('completed', '2026-09-30'), ('completed', '')}
    assert 'No completion date' in page.groups[('completed', '')].text(0)
    assert page.groups[('completed', '')].child(0).data(0, Qt.ItemDataRole.UserRole) == third
    assert '$0.30' in page.count.text()  # Exact fee addition.


def test_day_checkbox_partial_selection_and_collapse_preserve_export_ids(window, context, customer_id, qtbot):
    ids = [add_job(context, customer_id, scheduled_date='2026-10-05', fee=fee) for fee in ('150', '180')]
    other = add_job(context, customer_id, scheduled_date='2026-10-06', fee='120')
    window.refresh_all(); window.tabs.setCurrentIndex(2)
    page = window.jobs_page
    group = page.groups[('date', '2026-10-05')]
    group.setCheckState(0, Qt.CheckState.Checked)
    assert page.checked_ids == set(ids)
    assert page.select_all.checkState() == Qt.CheckState.PartiallyChecked
    page.items[ids[0]].setCheckState(0, Qt.CheckState.Unchecked)
    assert group.checkState(0) == Qt.CheckState.PartiallyChecked
    page.items[other].setCheckState(0, Qt.CheckState.Checked)
    assert '$300.00' in page.selection_caption.text()
    group.setExpanded(False)
    window.refresh_jobs()
    assert not page.groups[('date', '2026-10-05')].isExpanded()
    assert page.checked_ids == {ids[1], other}
    assert {row['id'] for row in page.selected_records()} == {ids[1], other}
    qtbot.mouseClick(page.select_all, Qt.MouseButton.LeftButton)
    assert page.checked_ids == set(ids + [other])
    assert all(g.checkState(0) == Qt.CheckState.Checked for g in page.groups.values())
    qtbot.mouseClick(page.clear_button, Qt.MouseButton.LeftButton)
    assert not page.checked_ids
    assert page.select_all.checkState() == Qt.CheckState.Unchecked
    assert not page.export_selected_button.isEnabled()


def test_focus_and_export_selection_are_independent_and_refresh_preserves_focus(window, context, customer_id):
    one = add_job(context, customer_id, scheduled_date='2026-10-05')
    two = add_job(context, customer_id, scheduled_date='2026-10-06')
    window.refresh_all()
    page = window.jobs_page
    page.items[one].setCheckState(0, Qt.CheckState.Checked)
    page.tree.setCurrentItem(page.items[two])
    assert page.focused_id == two
    assert page.checked_ids == {one}
    window.refresh_all()
    assert page.focused_id == two and page.checked_ids == {one}
    page.tree.setCurrentItem(page.groups[('date', '2026-10-05')])
    assert page.focused_id is None
    assert not page.edit_button.isEnabled()
    assert page.checked_ids == {one}


def test_search_clears_export_selection_and_stale_details(window, context, customer_id):
    job = add_job(context, customer_id, notes='<b>Plain job notes</b>')
    window.refresh_all()
    page = window.jobs_page
    page.tree.setCurrentItem(page.items[job])
    page.items[job].setCheckState(0, Qt.CheckState.Checked)
    page.search.setText('no matching record')
    assert window.job_rows == []
    assert not page.checked_ids
    assert page.focused_id is None
    assert page.notes.toPlainText() == ''
    assert 'filters changed' in page.selection_caption.text()
    assert 'No jobs match' in page.empty.text()


@pytest.mark.parametrize('option,expected', [
    ('today', {'2026-10-02'}),
    ('week', {'2026-09-28', '2026-10-02', '2026-10-04'}),
    ('next7', {'2026-10-02', '2026-10-04', '2026-10-08'}),
    ('month', {'2026-10-02', '2026-10-04', '2026-10-08', '2026-10-31'}),
    ('all', {'', '2026-09-28', '2026-10-02', '2026-10-04', '2026-10-08', '2026-10-31', '2026-11-01'}),
])
def test_date_presets_have_inclusive_boundaries(window, context, customer_id, today, option, expected):
    for value in ('', '2026-09-28', '2026-10-02', '2026-10-04', '2026-10-08', '2026-10-31', '2026-11-01'):
        add_job(context, customer_id, scheduled_date=value)
    window.refresh_all()
    page = window.jobs_page
    page.date_range.setCurrentIndex(page.date_range.findData(option))
    assert {row['scheduled_date'] for row in window.job_rows} == expected


def test_custom_range_and_completed_date_basis(window, context, customer_id, today):
    job = add_job(context, customer_id, scheduled_date='2026-10-01', completed_date='2026-10-02', status='Completed')
    window.refresh_all(); window.tabs.setCurrentIndex(2)
    page = window.jobs_page
    page.from_date.setDate(QDate(2026, 10, 2)); page.to_date.setDate(QDate(2026, 10, 2))
    page.date_range.setCurrentIndex(page.date_range.findData('custom'))
    assert page.custom_dates.isVisible()
    assert window.job_rows == []
    page.group_by.setCurrentIndex(page.group_by.findData('completed'))
    assert [row['id'] for row in window.job_rows] == [job]
    page.from_date.setDate(QDate(2026, 10, 3))
    assert page.date_error.isVisible()
    assert window.job_rows == []
    page.from_date.setDate(QDate(2026, 10, 2))
    assert not page.date_error.isVisible()
    assert len(window.job_rows) == 1


def test_month_preset_handles_leap_year(window, context, customer_id, monkeypatch):
    class February(date):
        @classmethod
        def today(cls): return cls(2028, 2, 29)
    monkeypatch.setattr(jobs_page, 'date', February)
    wanted = add_job(context, customer_id, scheduled_date='2028-02-29')
    add_job(context, customer_id, scheduled_date='2028-03-01')
    window.refresh_all()
    page = window.jobs_page
    page.date_range.setCurrentIndex(page.date_range.findData('month'))
    assert [row['id'] for row in window.job_rows] == [wanted]


def test_selected_csv_exports_each_checked_job_once_with_links_and_custom_fields(window, context, customer_id, monkeypatch, tmp_path):
    other = context.db.create_customer(CustomerRecord(name='=SUM(A1:A2)', suburb='Bondi'))
    a = add_job(context, customer_id, scheduled_date='2026-10-05', custom_fields={'weather': 'Dry'}, notes='a,b\nsecond line')
    b = add_job(context, customer_id, scheduled_date='2026-10-05')
    c = add_job(context, other, scheduled_date='2026-10-06', fee='120')
    window.refresh_all()
    page = window.jobs_page
    page.groups[('date', '2026-10-05')].setCheckState(0, Qt.CheckState.Checked)
    page.items[b].setCheckState(0, Qt.CheckState.Unchecked)
    page.items[c].setCheckState(0, Qt.CheckState.Checked)
    page.groups[('date', '2026-10-05')].setExpanded(False)
    path = tmp_path / 'selected.csv'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args, **kwargs: (str(path), 'CSV files (*.csv)'))
    page.export_selected_action.trigger()
    with path.open(encoding='utf-8-sig', newline='') as handle: rows = list(csv.DictReader(handle))
    assert [row['ID'] for row in rows] == [str(a), str(c)]
    assert rows[0]['Customer ID'] == str(customer_id)
    assert rows[0]['Weather'] == 'Dry'
    assert rows[0]['Job notes'] == 'a,b\nsecond line'
    assert rows[1]['Customer'] == "'=SUM(A1:A2)"
    assert rows[1]['Charge / fee (AUD)'] == '$120.00'
    page.export_filtered_action.trigger()
    with path.open(encoding='utf-8-sig', newline='') as handle: rows = list(csv.DictReader(handle))
    assert {row['ID'] for row in rows} == {str(a), str(b), str(c)}
    page.search.setText('Bondi')
    assert not page.export_selected_action.isEnabled()
    page.export_filtered_action.trigger()
    with path.open(encoding='utf-8-sig', newline='') as handle: rows = list(csv.DictReader(handle))
    assert [row['ID'] for row in rows] == [str(c)]


def test_duplicate_name_customer_groups_and_inactive_customer_navigation(window, context, customer_id, qtbot):
    other = context.db.create_customer(CustomerRecord(name='Mary Window', suburb='Bondi'))
    first = add_job(context, customer_id)
    second = add_job(context, other)
    context.db.set_customer_active(other, False)
    window.refresh_all(); window.tabs.setCurrentIndex(2)
    page = window.jobs_page
    page.group_by.setCurrentIndex(page.group_by.findData('status'))
    assert page.groups[('status', 'Scheduled')].childCount() == 2
    page.group_by.setCurrentIndex(page.group_by.findData('customer'))
    assert len(page.groups) == 2
    assert page.groups[('customer', customer_id)].child(0).data(0, Qt.ItemDataRole.UserRole) == first
    assert page.groups[('customer', other)].child(0).data(0, Qt.ItemDataRole.UserRole) == second
    page.tree.setCurrentItem(page.items[second])
    qtbot.mouseClick(page.view_customer_button, Qt.MouseButton.LeftButton)
    assert window.tabs.currentIndex() == 1
    assert window.selected_customer == other
    assert window.inactive.isChecked()
    assert 'Bondi' in window.profile.text()


@pytest.mark.parametrize('open_from', ['button', 'row'])
def test_configured_job_labels_fields_and_plain_notes_survive_details_and_edit(window, context, customer_id, qtbot, click, open_from):
    context.settings.job_fields.append(FieldDefinition('site_code', 'Site code', browse_column=True))
    for field in context.settings.job_fields:
        if field.key == 'fee': field.label = 'Agreed price'
    window.apply_settings(context.settings)
    job = add_job(context, customer_id, scheduled_date='2026-10-05', fee='180', notes='<b>Plain text</b>', custom_fields={'site_code': 'Gate 2'})
    window.refresh_all(); window.tabs.setCurrentIndex(2)
    page = window.jobs_page
    page.tree.setCurrentItem(page.items[job])
    headers = [page.tree.headerItem().text(i) for i in range(page.tree.columnCount())]
    assert 'Agreed price' in headers and 'Site code' in headers
    assert page.items[job].text(headers.index('Site code')) == 'Gate 2'
    assert page.notes.toPlainText() == '<b>Plain text</b>'
    assert any('Gate 2' in widget.text() for widget in page.detail_scroll.findChildren(jobs_page.QLabel))
    def edit(dialog):
        assert dialog.job_id == job
        dialog.form.widgets['fee'].setText('190.25')
        click(dialog, 'Save')
    def open_edit():
        if open_from == 'button':
            qtbot.mouseClick(page.edit_button, Qt.MouseButton.LeftButton)
        else:
            rectangle = page.tree.visualRect(page.tree.indexFromItem(page.items[job], 0))
            # QTest's double-click event needs the preceding normal click, and
            # the clicked cell must be visible even with extra browse columns.
            qtbot.mouseClick(page.tree.viewport(), Qt.MouseButton.LeftButton, pos=rectangle.center())
            qtbot.mouseDClick(page.tree.viewport(), Qt.MouseButton.LeftButton, pos=rectangle.center())
    drive_modal(open_edit, JobDialog, edit)
    assert context.db.get_job(job)['fee'] == '190.25'
    assert page.focused_id == job
    assert '$190.25' in page.items[job].text(headers.index('Agreed price'))


@pytest.mark.parametrize('size', [(1250, 820), (900, 690)])
def test_jobs_layout_preserves_rows_actions_and_maroon_dropdown_contrast(window, context, customer_id, qtbot, size):
    job = add_job(context, customer_id, scheduled_date='2026-10-05', equipment=['3m ladder'], fee='150', notes='Long note. ' * 100)
    window.refresh_all(); window.tabs.setCurrentIndex(2); window.resize(*size)
    page = window.jobs_page
    page.tree.setCurrentItem(page.items[job])
    window.grab()  # Paint rows, badge delegate and scrollable long content.
    assert page.tree.viewport().height() >= 100
    assert page.tree.visualItemRect(page.items[job]).height() >= 40
    assert page.list_card.geometry().right() < page.detail_card.geometry().left()
    assert page.complete_button.isVisible()
    assert page.complete_button.geometry().right() <= page.detail_card.width()
    assert page.detail_scroll.verticalScrollBar().maximum() > 0 or page.notes.verticalScrollBar().maximum() > 0
    for combo in (page.status_filter, page.date_range, page.group_by):
        combo.ensurePolished()
        palette = combo.palette()
        assert palette.color(QPalette.ColorRole.Button).name() == TOKENS['bordeaux_mid']
        assert contrast(palette.color(QPalette.ColorRole.ButtonText), palette.color(QPalette.ColorRole.Button)) >= 4.5
        assert combo.geometry().right() <= page.width()
    assert not QPixmap(TOKENS['icon_down_white'][5:-2]).isNull()
    page.date_range.showPopup()
    qtbot.waitUntil(lambda: page.date_range.view().isVisible())
    popup_palette = page.date_range.view().palette()
    assert contrast(popup_palette.color(QPalette.ColorRole.HighlightedText), popup_palette.color(QPalette.ColorRole.Highlight)) >= 4.5
    page.date_range.hidePopup()
