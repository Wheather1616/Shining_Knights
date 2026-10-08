"""Home actions, navigation guards, overflow lists and narrow-window geometry."""
from datetime import date, timedelta

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from customer_app.models import CustomerRecord, JobRecord
from customer_app.ui.field_settings import UnsavedChangesDialog
from customer_app.ui.forms import CustomerDialog, JobDialog
from tests.ui.test_theme import contrast
from tests.ui.test_workflows import drive_modal


def make_due(context, today, name='Due customer', offset=0):
    return context.db.create_customer(CustomerRecord(name=name, suburb='Coogee', first_service_date=(today + timedelta(days=offset)).isoformat(), default_fee='180.00', default_job_type='External windows'))


def test_empty_home_is_calm_and_clickable(window, context, today, qtbot):
    window.refresh_home()
    page = window.home
    assert page.date_label.text() == 'Friday, 2 October 2026'
    assert [card.count.text() for card in (page.today_card, page.next7_card, page.booking_card)] == ['0', '0', '0']
    assert page.visits_empty.isVisible()
    assert not page.visits_table.isVisible()
    assert not page.overdue_notice.isVisible()
    assert not page.booking_list_button.isVisible()
    qtbot.mouseClick(page.booking_card, Qt.MouseButton.LeftButton)
    assert window.tabs.currentIndex() == 0
    assert 'up to date' in page.bookings_scroll.widget().findChildren(type(page.date_label))[0].text()


@pytest.mark.parametrize('which,range_key,expected_offsets', [('today_card','today',{0}), ('next7_card','next7',{0,6})])
def test_summary_links_replace_conflicting_filters(window, context, customer_id, today, qtbot, which, range_key, expected_offsets):
    jobs = {offset: context.db.create_job(JobRecord(customer_id, scheduled_date=(today + timedelta(days=offset)).isoformat())) for offset in (-1, 0, 6, 7)}
    page = window.jobs_page
    page.search.setText('No matching name')
    page.status_filter.setCurrentText('Trash')
    page.group_by.setCurrentIndex(page.group_by.findData('completed'))
    page.date_range.setCurrentIndex(page.date_range.findData('month'))
    window.refresh_home()
    qtbot.mouseClick(getattr(window.home, which), Qt.MouseButton.LeftButton)
    assert window.tabs.currentIndex() == 2
    assert page.search.text() == ''
    assert page.status_filter.currentText() == 'Upcoming'
    assert page.group_by.currentData() == 'date'
    assert page.date_range.currentData() == range_key
    assert set(page.items) == {jobs[offset] for offset in expected_offsets}
    assert window.navigation_buttons[2].isChecked()


def test_visit_opens_correct_id_and_expands_day(window, context, today, qtbot):
    first = context.db.create_customer(CustomerRecord(name='Alex', suburb='Bondi'))
    second = context.db.create_customer(CustomerRecord(name='Alex', suburb='Coogee'))
    jobs = [context.db.create_job(JobRecord(cid, scheduled_date=today.isoformat())) for cid in (first, second)]
    window.refresh_all()
    page = window.jobs_page
    for item in page.groups.values():
        item.setExpanded(False)
    window.job_search.setText('Unrelated')
    item = window.home.visits_table.item(1, 1)
    qtbot.mouseClick(window.home.visits_table.viewport(), Qt.MouseButton.LeftButton,
                     pos=window.home.visits_table.visualItemRect(item).center())
    assert window.tabs.currentIndex() == 2
    assert page.focused_id == jobs[1]
    assert page.items[jobs[1]].parent().isExpanded()
    assert 'Coogee' in page.address.text()
    assert not page.checked_ids


def test_view_all_jobs_includes_records_outside_week(window, context, customer_id, today, click):
    future = context.db.create_job(JobRecord(customer_id, scheduled_date='2026-12-01'))
    window.refresh_all()
    click(window.home, 'View all jobs')
    assert window.tabs.currentIndex() == 2
    assert future in window.jobs_page.items
    assert window.job_filter.currentText() == 'All'
    assert window.jobs_page.date_range.currentData() == 'all'


def test_reminders_can_show_all_and_open_correct_customer(window, context, today, qtbot, click):
    ids = [make_due(context, today, 'Same name', -i) for i in range(7)]
    window.refresh_home()
    home = window.home
    assert home.booking_card.count.text() == '7'
    assert len(home.booking_buttons) == 5
    assert home.booking_list_button.text() == 'View all 7 customers'
    click(home, 'View all 7 customers')
    assert len(home.booking_buttons) == 7
    click(home, 'Show first 5')
    assert len(home.booking_buttons) == 5
    qtbot.mouseClick(home.booking_card, Qt.MouseButton.LeftButton)
    assert len(home.booking_buttons) == 7
    home.bookings_scroll.ensureWidgetVisible(home.customer_buttons[ids[0]])
    qtbot.mouseClick(home.customer_buttons[ids[0]], Qt.MouseButton.LeftButton)
    assert window.tabs.currentIndex() == 1
    assert window.selected_customer == ids[0]


def test_add_job_from_reminder_uses_service_defaults_and_refreshes_home(window, context, today, qtbot, click):
    cid = make_due(context, today)
    window.refresh_home()
    def save(dialog):
        assert dialog.customer.currentData() == cid
        assert dialog.form.widgets['fee'].text() == '180.00'
        assert dialog.form.widgets['job_type'].selected_values() == ['External windows']
        dialog.form.widgets['scheduled_date'].setText(today.isoformat())
        click(dialog, 'Save')
    drive_modal(lambda: qtbot.mouseClick(window.home.booking_buttons[cid], Qt.MouseButton.LeftButton), JobDialog, save)
    assert cid not in window.home.booking_buttons
    assert window.home.today_card.count.text() == '1'
    assert window.home.visits_table.rowCount() == 1


def test_home_add_customer_action(window, monkeypatch, qtbot):
    calls = []
    monkeypatch.setattr(CustomerDialog, 'exec', lambda self: calls.append('customer') or CustomerDialog.DialogCode.Rejected)
    qtbot.mouseClick(window.home.add_customer_button, Qt.MouseButton.LeftButton)
    assert calls == ['customer']


def test_overdue_jobs_notice_links_to_open_past_jobs(window, context, customer_id, today, click):
    old = context.db.create_job(JobRecord(customer_id, scheduled_date='2026-10-01'))
    context.db.create_job(JobRecord(customer_id, scheduled_date=today.isoformat()))
    window.refresh_home()
    assert window.home.overdue_notice.isVisible()
    assert '1 past visit' in window.home.overdue_label.text()
    click(window.home, 'Review jobs')
    assert window.tabs.currentIndex() == 2
    assert set(window.jobs_page.items) == {old}


@pytest.mark.parametrize('choice,index', [('Keep editing',3), ('Discard',0), ('Save',0)])
def test_header_navigation_preserves_unsaved_settings_guard(window, context, qtbot, click, choice, index):
    qtbot.mouseClick(window.navigation_buttons[3], Qt.MouseButton.LeftButton)
    window.configuration.navigation.setCurrentRow(2)
    window.configuration.remember_filters.setChecked(True)
    drive_modal(lambda: qtbot.mouseClick(window.navigation_buttons[0], Qt.MouseButton.LeftButton),
                UnsavedChangesDialog, lambda dialog: click(dialog, choice))
    assert window.tabs.currentIndex() == index
    assert [button.isChecked() for button in window.navigation_buttons] == [i == index for i in range(4)]
    assert context.store.load().remember_jobs_filters is (choice == 'Save')


def test_backups_link_opens_right_settings_section(window, click):
    click(window.home, 'Backups && help')
    assert window.tabs.currentIndex() == 3
    assert window.configuration.navigation.currentRow() == 4
    assert window.navigation_buttons[3].isChecked()


def test_overview_refreshes_when_date_rolls_over(window, context, customer_id, today, monkeypatch):
    context.db.create_job(JobRecord(customer_id, scheduled_date='2026-10-03'))
    window.refresh_home()
    assert window.home.today_card.count.text() == '0'
    from customer_app.ui import main_window
    class Tomorrow(date):
        @classmethod
        def today(cls): return cls(2026, 10, 3)
    monkeypatch.setattr(main_window, 'date', Tomorrow)
    window._check_overview_date()
    assert window.home.date_label.text() == 'Saturday, 3 October 2026'
    assert window.home.today_card.count.text() == '1'
    window.prepare_shutdown()
    assert not window.overview_timer.isActive()


@pytest.mark.parametrize('size', [(1250,820), (900,690)])
def test_home_geometry_and_contrast_at_supported_sizes(window, context, today, qtbot, size):
    for i in range(6):
        cid = make_due(context, today, f'Customer {i}', -1)
        context.db.create_job(JobRecord(cid, scheduled_date=today.isoformat()))
    make_due(context, today, 'A very long customer name with a business & many words', -1)
    window.refresh_all()
    window.resize(*size)
    qtbot.wait(10)
    home = window.home
    assert window.size().toTuple() == size
    assert home.visits_table.rowCount() == 5
    assert 'Showing 5 of 6' in home.visits_hint.text()
    assert home.backup_label.isVisible()
    for card in (home.today_card, home.next7_card, home.booking_card):
        assert card.rect().contains(card.count.geometry())
        assert card.count.fontMetrics().boundingRect(card.count.text()).height() <= card.count.height()
    for button in window.navigation_buttons:
        assert window.app_header.rect().contains(button.geometry())
    active = window.navigation_buttons[0]
    # Qt's palette does not expose :checked QSS colours; inspect the rendered state.
    image = active.grab().toImage()
    background = image.pixelColor(8, image.height() // 2)
    assert background == QColor('#6d0813')
    assert any(image.pixelColor(x, y) == QColor('#ffffff')
               for x in range(12, image.width() - 12) for y in range(8, image.height() - 8))
    assert contrast(QColor('#ffffff'), background) >= 4.5
    assert home.bookings_scroll.width() >= 200
    assert home.visits_card.geometry().right() < home.bookings_card.geometry().left()
