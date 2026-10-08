"""Settings behaviours exercised through real Qt controls and encrypted fixtures."""
import copy
from dataclasses import asdict
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QMessageBox

from customer_app.backup import DatabaseBackupManager
from customer_app.config import FieldDefinition
from customer_app.models import CustomerRecord
from customer_app.ui.field_settings import FieldDialog, UnsavedChangesDialog, SECTIONS
from customer_app.ui.forms import CustomerDialog, RecordForm
from customer_app.ui.main_window import CustomerMainWindow
from customer_app.ui.restore_dialog import RestoreDialog
from tests.conftest import KEY
from tests.ui.test_workflows import drive_modal
from tests.ui.test_theme import contrast
from PySide6.QtGui import QPalette


def edit_screen(window):
    window.tabs.setCurrentIndex(3)
    page = window.configuration
    page.navigation.setCurrentRow(2)
    return page


def test_sections_dirty_tracking_inline_success_and_reverting_change(window, context, qtbot, click):
    page = edit_screen(window)
    assert window.tabs.tabText(3) == 'Settings'
    assert [page.navigation.item(i).text() for i in range(5)] == SECTIONS
    assert not page.save_button.isEnabled()
    original = page.column_checks['customers']['phone'].isChecked()
    page.column_checks['customers']['phone'].setChecked(not original)
    assert page.is_dirty and page.save_button.isEnabled()
    assert context.store.load().customer_fields[2].browse_column == original
    page.column_checks['customers']['phone'].setChecked(original)
    assert not page.is_dirty and not page.save_button.isEnabled()
    page.column_checks['customers']['phone'].setChecked(not original)
    with qtbot.waitSignal(page.settings_saved): click(page, 'Save changes')
    assert page.save_status.text() == 'Changes saved'
    assert not page.is_dirty and not page.save_button.isEnabled()
    assert context.store.load().customer_fields[2].browse_column != original


@pytest.mark.parametrize('choice,index,saved,dirty', [('Save',1,True,False), ('Discard',1,False,False), ('Keep editing',3,False,True)])
def test_leaving_settings_offers_all_three_decisions(window, context, click, choice, index, saved, dirty):
    page = edit_screen(window)
    page.remember_filters.setChecked(True)
    drive_modal(lambda: window.tabs.setCurrentIndex(1), UnsavedChangesDialog, lambda d: click(d, choice))
    assert window.tabs.currentIndex() == index
    assert context.store.load().remember_jobs_filters is saved
    assert page.is_dirty is dirty


def test_unsaved_window_close_can_be_cancelled_or_saved(window, context, click):
    page = edit_screen(window)
    page.remember_filters.setChecked(True)
    drive_modal(window.close, UnsavedChangesDialog, lambda d: click(d, 'Keep editing'))
    assert window.isVisible() and page.is_dirty
    drive_modal(window.close, UnsavedChangesDialog, lambda d: click(d, 'Save'))
    assert not window.isVisible() and context.store.load().remember_jobs_filters


def test_failed_save_keeps_draft_and_prevents_navigation(window, context, monkeypatch, messages, click):
    page = edit_screen(window)
    before = context.store.settings_path.read_bytes()
    page.remember_filters.setChecked(True)
    def fail(*args): raise OSError('Disk full')
    monkeypatch.setattr(context.store, 'save', fail)
    drive_modal(lambda: window.tabs.setCurrentIndex(0), UnsavedChangesDialog, lambda d: click(d, 'Save'))
    assert window.tabs.currentIndex() == 3 and page.is_dirty
    assert context.store.settings_path.read_bytes() == before
    assert not window.settings.remember_jobs_filters
    assert 'could not be saved' in page.save_status.text()
    assert messages[-1][1] == 'Settings could not be saved'


def test_columns_affect_actual_job_and_customer_lists_and_essentials_stay_visible(window, context, customer_id):
    context.db.create_job(context.db.new_job_for_customer(customer_id))
    window.refresh_all()
    page = edit_screen(window)
    for entity, keys in [('customers', ['name']), ('jobs', ['scheduled_date','status','payment_status'])]:
        for key in keys:
            assert page.column_checks[entity][key].isChecked()
            assert not page.column_checks[entity][key].isEnabled()
    window.customer_page.toggle_directory_details()
    page.column_checks['customers']['phone'].setChecked(False)
    page.column_checks['jobs']['fee'].setChecked(False)
    page.save()
    headers = [window.jobs_tree.headerItem().text(i) for i in range(window.jobs_tree.columnCount())]
    assert 'Fee (AUD)' not in headers and 'Customer / suburb' in headers and 'Status' in headers
    assert '0412 345 678' not in window.customer_table.item(0,0).text()
    page.column_checks['customers']['phone'].setChecked(True)
    page.save()
    assert '0412 345 678' in window.customer_table.item(0,0).text()


def test_default_payment_applies_only_to_new_customers_and_their_jobs(window, context, customer_id, qtbot):
    window.tabs.setCurrentIndex(3)
    page = window.configuration
    page.navigation.setCurrentRow(1)
    page.default_payment.setCurrentIndex(page.default_payment.findData('Card'))
    page.save()
    fresh = CustomerDialog(context.db, window.settings); qtbot.addWidget(fresh)
    existing = CustomerDialog(context.db, window.settings, customer_id); qtbot.addWidget(existing)
    assert fresh.form.widgets['default_payment_type'].currentData() == 'Card'
    assert existing.form.widgets['default_payment_type'].currentData() == 'Bank transfer'
    fresh.form.widgets['first_name'].setText('New customer'); fresh.save()
    assert context.db.new_job_for_customer(fresh.saved_id).payment_type == 'Card'


def test_stop_using_preserves_existing_values_and_use_again_restores_choice(window, context, customer_id, monkeypatch, qtbot):
    job_id = context.db.create_job(context.db.new_job_for_customer(customer_id))
    window.tabs.setCurrentIndex(3); page = window.configuration
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **kw: QMessageBox.StandardButton.Yes)
    page.toggle_choice('equipment_options', '3m ladder')
    page.toggle_choice('job_type_options', 'External windows')
    page.save()
    assert context.db.get_customer(customer_id)['default_equipment'] == ['3m ladder']
    assert context.db.get_job(job_id)['job_type'] == ['External windows']
    edited = CustomerDialog(context.db, window.settings, customer_id); qtbot.addWidget(edited)
    assert edited.form.widgets['default_job_type'].selected_values() == ['External windows']
    edited.save()
    fresh = context.db.new_job_for_customer(customer_id)
    assert fresh.equipment == [] and fresh.job_type == []
    context.db.create_job(fresh)
    page.toggle_choice('equipment_options', '3m ladder'); page.save()
    assert '3m ladder' in context.db.new_job_for_customer(customer_id).equipment


def test_edit_choices_rejects_duplicates_and_rename_keeps_history(window, context, customer_id, monkeypatch, messages):
    page = window.configuration
    monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **kw: ('Cash', True))
    before = copy.deepcopy(page.settings)
    page.edit_choice('payment_type_options')
    assert page.settings == before and messages[-1][1] == 'Check the name'
    monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **kw: ('Transfer', True))
    page.edit_choice('payment_type_options', 'Bank transfer'); page.save()
    assert 'Transfer' in context.store.load().payment_type_options
    assert context.db.get_customer(customer_id)['default_payment_type'] == 'Bank transfer'


def test_add_question_hides_keys_avoids_collisions_and_targets_job_details(window, context, click, qtbot):
    window.tabs.setCurrentIndex(3); page = window.configuration; page.navigation.setCurrentRow(3)
    def fill(dialog):
        assert not hasattr(dialog, 'key')
        dialog.entity.setCurrentIndex(dialog.entity.findData('jobs'))
        dialog.label.setText('Weather')
        dialog.kind.setCurrentIndex(dialog.kind.findData('dropdown'))
        dialog.options.setPlainText('Clear\nWet')
        dialog.browse.setChecked(True)
        click(dialog, 'Add question')
    drive_modal(lambda: click(page, 'Add a question'), FieldDialog, fill)
    page.save()
    field = next(f for f in window.settings.job_fields if f.key == 'weather_2')
    assert field.label == 'Weather' and field.options == ['Clear','Wet'] and field.browse_column
    assert all(f.key != 'weather_2' for f in window.settings.customer_fields)


@pytest.mark.parametrize('name,choices,error', [('', 'A', 'name'), ('Test','', 'choice'), ('Test','A\na', 'choice')])
def test_question_dialog_validates_before_closing(window, qtbot, name, choices, error):
    dialog = FieldDialog(parent=window); qtbot.addWidget(dialog)
    dialog.label.setText(name); dialog.kind.setCurrentIndex(dialog.kind.findData('dropdown'))
    dialog.options.setPlainText(choices)
    dialog._accept_valid()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert error in dialog.error.text()


def test_edit_question_keeps_type_and_hidden_answers(window, context, customer_id, click, qtbot):
    page = window.configuration
    field = next(f for f in page.settings.customer_fields if f.key == 'gate_code')
    def edit(dialog):
        assert not dialog.kind.isEnabled() and not dialog.entity.isEnabled()
        dialog.enabled.setChecked(False)
        assert not dialog.required.isChecked() and not dialog.required.isEnabled()
        click(dialog, 'Save question')
    drive_modal(lambda: page.edit_field('customers', field), FieldDialog, edit)
    page.save()
    form = RecordForm(window.settings,'customers',context.db.get_customer(customer_id)); qtbot.addWidget(form)
    assert 'gate_code' not in form.widgets
    context.db.update_customer(customer_id,CustomerRecord(**form.values()))
    assert context.db.get_customer(customer_id)['custom_fields']['gate_code'] == '0042'


def test_remember_filters_survives_reopening_without_persisting_search(window, context, qtbot):
    page = edit_screen(window)
    page.remember_filters.setChecked(True); page.save()
    window.tabs.setCurrentIndex(2)
    window.jobs_page.status_filter.setCurrentText('Completed')
    window.jobs_page.date_range.setCurrentIndex(window.jobs_page.date_range.findData('month'))
    window.group_by.setCurrentIndex(window.group_by.findData('customer'))
    window.job_search.setText('Private customer search')
    assert 'Private customer search' not in context.store.settings_path.read_text()
    reopened = CustomerMainWindow(db=context.db,settings_store=context.store,enable_backups=False); qtbot.addWidget(reopened)
    assert reopened.job_filter.currentText() == 'Completed'
    assert reopened.jobs_page.date_range.currentData() == 'month'
    assert reopened.group_by.currentData() == 'customer' and reopened.job_search.text() == ''
    page = edit_screen(window)
    page.remember_filters.setChecked(False)
    page.default_group.setCurrentIndex(page.default_group.findData('status')); page.save()
    assert context.store.load().jobs_filters == {}
    assert window.job_filter.currentText() == 'All' and window.group_by.currentData() == 'status'


def test_filter_updates_do_not_overwrite_pending_settings_draft(window, context):
    page = edit_screen(window); page.remember_filters.setChecked(True); page.save()
    page.default_payment.setCurrentIndex(page.default_payment.findData('Cash'))
    window.job_filter.setCurrentText('Upcoming')
    assert page.is_dirty and page.settings.default_payment_method == 'Cash'
    page.save()
    assert context.store.load().default_payment_method == 'Cash'
    assert context.store.load().jobs_filters['status'] == 'Upcoming'


@pytest.mark.parametrize('size',[(1250,820),(900,690)])
def test_settings_sections_scroll_and_footer_remains_visible(window, qtbot, size):
    window.resize(*size); window.tabs.setCurrentIndex(3); page = window.configuration
    for index in range(5):
        page.navigation.setCurrentRow(index)
        qtbot.waitUntil(lambda: page.save_button.isVisible())
        assert page.save_button.geometry().bottom() <= page.height()
        scroll = page.pages.currentWidget()
        assert scroll.viewport().width() >= 500
        assert scroll.horizontalScrollBar().maximum() == 0
        assert page.navigation.geometry().right() < page.pages.geometry().left()
    page.navigation.setCurrentRow(1)
    palette = page.default_payment.palette()
    assert contrast(palette.color(QPalette.ColorRole.Text),palette.color(QPalette.ColorRole.Base)) >= 4.5
    assert page.default_payment.property('role') == 'settingsChoice'


def test_backup_status_manual_backup_and_open_folder(window, context, tmp_path, monkeypatch):
    from PySide6.QtGui import QDesktopServices
    window.backup_manager = DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    page = window.configuration; page._rebuild(); page.back_up_now()
    assert window.backup_manager.latest_backup().is_file()
    assert 'Last successful backup' in page.backup_status.text()
    opened=[]
    monkeypatch.setattr(QDesktopServices,'openUrl',lambda url: opened.append(url.toLocalFile()) or True)
    page.open_backup_folder()
    assert opened == [str(window.backup_manager.backup_dir)]


def test_restore_review_needs_final_confirmation_and_cancel_keeps_current_data(window, context, customer_id, tmp_path, monkeypatch, click, qtbot):
    window.backup_manager = DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    backup = window.backup_manager.create_backup()
    context.db.create_customer(CustomerRecord(name='Later customer'))
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**kw:(str(backup),'Customer backups (*.db)'))
    drive_modal(window.restore_database_backup,RestoreDialog,lambda d: click(d,'Cancel'))
    assert len(context.db.list_customers()) == 2
    def confirm(dialog):
        assert dialog.step == 2
        click(dialog,'Continue')
        assert dialog.step == 3 and dialog.result() != QDialog.DialogCode.Accepted
        click(dialog,'Restore backup')
    drive_modal(window.restore_database_backup,RestoreDialog,confirm)
    assert len(context.db.list_customers()) == 1
    assert 'Backup restored' in window.configuration.backup_status.text()
    assert len(window.backup_manager._backup_files()) == 2


def test_invalid_restore_is_rejected_without_changing_records(window, context, customer_id, tmp_path, monkeypatch, messages):
    window.backup_manager = DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    bad = tmp_path/'bad.db'; bad.write_bytes(b'not a backup')
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**kw:(str(bad),''))
    window.restore_database_backup()
    assert context.db.get_customer(customer_id)['name'] == 'Mary Window'
    assert messages[-1][1] == 'Backup could not be opened'


def test_builtin_label_editor_and_help_use_plain_language(window, click, qtbot):
    from PySide6.QtWidgets import QComboBox, QLineEdit, QLabel
    page = edit_screen(window)
    def rename(dialog):
        editor=dialog.findChild(QLineEdit)
        editor.setText('Customer name')
        click(dialog,'Save')
    drive_modal(lambda:page.edit_label('customers'),QDialog,rename)
    page.save()
    assert window.customer_table.horizontalHeaderItem(0).text() == 'Customer name'
    def help_view(dialog):
        text=' '.join(w.text() for w in dialog.findChildren(QLabel))
        assert 'Service setup' in text and 'safety copy' in text
        assert 'SQLCipher' not in text
        click(dialog,'Close')
    drive_modal(page.open_help,QDialog,help_view)


def test_cancelled_choice_and_backup_errors_keep_records(window, context, customer_id, monkeypatch, messages):
    page=window.configuration
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**kw:('',False))
    page.edit_choice('equipment_options')
    assert not page.is_dirty
    class FailedBackup:
        def latest_backup(self): return None
        def create_backup(self): raise OSError('No space')
    window.backup_manager=FailedBackup()
    window.manual_backup()
    assert messages[-1][1] == 'Backup failed'
    assert context.db.get_customer(customer_id)['name'] == 'Mary Window'


def test_restore_failure_restarts_timer_and_retains_current_records(window, context, customer_id, tmp_path, monkeypatch, messages, click):
    from customer_app import recovery
    window.backup_manager=DatabaseBackupManager(context.db.db_path,tmp_path/'backups',KEY,settings_store=context.store)
    backup=window.backup_manager.create_backup()
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**kw:(str(backup),''))
    def fail(*a,**kw): raise OSError('Disk full')
    monkeypatch.setattr(recovery,'restore_backup',fail)
    def confirm(dialog):
        click(dialog,'Continue');click(dialog,'Restore backup')
    drive_modal(window.restore_database_backup,RestoreDialog,confirm)
    assert window.backup_timer.isActive()
    assert messages[-1][1] == 'Restore could not be completed'
    assert context.db.get_customer(customer_id)['name'] == 'Mary Window'
