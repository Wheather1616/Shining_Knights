"""Plain-language business settings with a separate, discardable editing draft."""
from __future__ import annotations

import copy
import re
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from ..config import CORE_FIELDS, RESERVED_KEYS, FieldDefinition
from .customer_page import label

ANSWER_TYPES = [('Short answer', 'text'), ('Longer note', 'textarea'), ('Number', 'number'),
                ('Amount', 'currency'), ('Date', 'date'), ('Yes / no', 'boolean'),
                ('Choice from a list', 'dropdown'), ('Several choices', 'multiselect')]
LOOKUPS = {'job_type_options': 'Services', 'equipment_options': 'Equipment',
           'payment_type_options': 'Payment methods'}
PROTECTED_COLUMNS = {'customers': {'name'}, 'jobs': {'scheduled_date', 'status', 'payment_status'}}
SECTIONS = ['Services & equipment', 'Payment methods', 'Screen layout', 'Extra information', 'Backups & help']


def button(text, handler, role='secondary'):
    widget = QPushButton(text)
    widget.setProperty('role', role)
    widget.clicked.connect(handler)
    return widget


def combo():
    widget = QComboBox()
    widget.setProperty('role', 'settingsChoice')
    return widget


def card(title, subtitle=''):
    widget = QWidget()
    widget.setObjectName('SettingsCard')
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)
    layout.addWidget(label(title, 'SectionTitle'))
    if subtitle:
        layout.addWidget(label(subtitle, 'PageHelper'))
    return widget, layout


class FieldDialog(QDialog):
    """Add/edit a question; storage keys are generated and never shown to the user."""
    def __init__(self, entity='customers', parent=None, *, definition=None, existing_keys=()):
        super().__init__(parent)
        self.original = copy.deepcopy(definition)
        self.existing_keys = set(existing_keys) | RESERVED_KEYS | set().union(*CORE_FIELDS.values())
        self.setWindowTitle('Edit question' if definition else 'Add a question')
        self.resize(540, 560)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 20)
        outer.setSpacing(14)
        outer.addWidget(label(self.windowTitle(), 'PageTitle'))
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setSpacing(12)
        self.entity = combo()
        self.entity.addItem('Customer details', 'customers')
        self.entity.addItem('Job details', 'jobs')
        self.entity.setCurrentIndex(self.entity.findData(entity))
        self.entity.setEnabled(definition is None)
        self.label = QLineEdit()
        self.label.setPlaceholderText('e.g. Gate code')
        self.kind = combo()
        for title, value in ANSWER_TYPES:
            self.kind.addItem(title, value)
        self.options = QPlainTextEdit()
        self.options.setPlaceholderText('One choice on each line')
        self.options.setMaximumHeight(120)
        self.required = QCheckBox('Must be filled in')
        self.browse = QCheckBox('Show in the list')
        self.enabled = QCheckBox('Use this question')
        self.enabled.setChecked(True)
        form.addRow('Where should this appear?', self.entity)
        form.addRow('Question name', self.label)
        form.addRow('Answer type', self.kind)
        self.options_label = label('Available choices', 'PageHelper')
        form.addRow(self.options_label, self.options)
        outer.addLayout(form)
        outer.addWidget(self.required)
        outer.addWidget(self.browse)
        if definition:
            self.label.setText(definition.label)
            self.kind.setCurrentIndex(self.kind.findData(definition.field_type))
            self.kind.setEnabled(False)
            self.options.setPlainText('\n'.join(definition.options))
            self.required.setChecked(definition.required)
            self.browse.setChecked(definition.browse_column)
            self.enabled.setChecked(definition.enabled)
            outer.addWidget(self.enabled)
            outer.addWidget(label('The answer type stays fixed to protect saved answers. Turn off Use this question to hide it and keep its history.', 'PageHelper'))
        self.enabled.toggled.connect(self._enabled_changed)
        self._enabled_changed(self.enabled.isChecked())
        self.kind.currentIndexChanged.connect(self._choices_visible)
        self._choices_visible()
        self.error = label('', 'SettingsError')
        outer.addWidget(self.error)
        outer.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Save question' if definition else 'Add question')
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty('role', 'primary')
        buttons.accepted.connect(self._accept_valid)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _choices_visible(self, *_):
        visible = self.kind.currentData() in ('dropdown', 'multiselect')
        self.options.setVisible(visible)
        self.options_label.setVisible(visible)

    def _enabled_changed(self, enabled):
        if not enabled:
            self.required.setChecked(False)
        self.required.setEnabled(enabled)
        self.browse.setEnabled(enabled)

    def definition(self):
        title = self.label.text().strip()
        if self.original:
            key = self.original.key
        else:
            key = re.sub(r'[^a-z0-9]+', '_', title.casefold()).strip('_') or 'question'
            if not key[0].isalpha():
                key = 'question_' + key
            base, count = key, 2
            while key in self.existing_keys:
                key = f'{base}_{count}'
                count += 1
        return FieldDefinition(key, title, self.kind.currentData(), self.required.isChecked(),
                               self.browse.isChecked(),
                               [v.strip() for v in self.options.toPlainText().splitlines() if v.strip()],
                               self.enabled.isChecked())

    def _accept_valid(self):
        definition = self.definition()
        if not definition.label:
            self.error.setText('Give your question a name.')
            return
        if definition.field_type in ('dropdown', 'multiselect'):
            if not definition.options or len({v.casefold() for v in definition.options}) != len(definition.options):
                self.error.setText('Enter at least one choice, with no repeated names.')
                return
        self.accept()


class UnsavedChangesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.choice = 'keep'
        self.setWindowTitle('Save your changes?')
        self.setMinimumWidth(410)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(label('Save your changes?', 'SectionTitle'))
        layout.addWidget(label("You have changes that haven't been saved. Choose what you'd like to do before leaving Settings.", 'PageHelper'))
        for title, choice in [('Save', 'save'), ('Discard', 'discard'), ('Keep editing', 'keep')]:
            layout.addWidget(button(title, lambda checked=False, value=choice: self._choose(value),
                                    'primary' if choice == 'save' else 'secondary'))

    def _choose(self, choice):
        self.choice = choice
        self.accept()


class FieldSettingsPage(QWidget):
    settings_saved = Signal(object)
    customers_requested = Signal()

    def __init__(self, settings, store, parent=None, *, owner=None):
        super().__init__(parent)
        self.owner = owner
        self.store = store
        self.settings = copy.deepcopy(settings)
        self.saved_settings = copy.deepcopy(settings)
        self.setObjectName('SettingsPage')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(label('Settings', 'PageTitle'))
        layout.addWidget(label('Set up the app to suit your business.', 'PageHelper'))
        body = QHBoxLayout()
        body.setSpacing(18)
        self.navigation = QListWidget()
        self.navigation.setObjectName('SettingsNavigation')
        self.navigation.setAccessibleName('Settings sections')
        self.navigation.addItems(SECTIONS)
        self.navigation.setFixedWidth(220)
        body.addWidget(self.navigation)
        self.pages = QStackedWidget()
        body.addWidget(self.pages, 1)
        layout.addLayout(body, 1)
        footer = QHBoxLayout()
        self.save_status = label('No changes to save', 'SettingsSaveStatus')
        footer.addWidget(self.save_status, 1)
        self.save_button = button('Save changes', self.save, 'primary')
        footer.addWidget(self.save_button)
        layout.addLayout(footer)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self._rebuild()
        self.navigation.setCurrentRow(0)
        self._changed()

    def _section(self, title, subtitle):
        scroll = QScrollArea()
        scroll.setObjectName('SettingsScroll')
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName('SettingsContent')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(14)
        layout.addWidget(label(title, 'SectionTitle'))
        layout.addWidget(label(subtitle, 'PageHelper'))
        scroll.setWidget(content)
        self.pages.addWidget(scroll)
        return layout

    def _rebuild(self):
        index = max(0, self.pages.currentIndex())
        while self.pages.count():
            old = self.pages.widget(0)
            self.pages.removeWidget(old)
            old.deleteLater()
        self._services()
        self._payments()
        self._screen_layout()
        self._questions()
        self._backups()
        self.pages.setCurrentIndex(index)

    def _lookup_card(self, attr):
        widget, layout = card(LOOKUPS[attr])
        active = getattr(self.settings, attr)
        inactive = self.settings.inactive_options.get(attr, [])
        if not active:
            layout.addWidget(label('No choices yet. Add one below.', 'PageHelper'))
        for value in [*active, *inactive]:
            row = QHBoxLayout()
            row.addWidget(label(value + (' (not in use)' if value in inactive else ''), 'SettingsRowName'), 1)
            if value in active:
                row.addWidget(button('Edit', lambda checked=False, a=attr, v=value: self.edit_choice(a, v), 'link'))
            row.addWidget(button('Use again' if value in inactive else 'Stop using',
                                 lambda checked=False, a=attr, v=value: self.toggle_choice(a, v), 'link'))
            layout.addLayout(row)
        caption = {'job_type_options': 'Add service', 'equipment_options': 'Add equipment',
                   'payment_type_options': 'Add payment method'}[attr]
        layout.addWidget(button(caption, lambda: self.edit_choice(attr)))
        return widget

    def _services(self):
        layout = self._section('Services & equipment', 'Choose the services you offer and the equipment you use.')
        # Stacked cards remain readable at the application's minimum window width.
        self.service_grid = QGridLayout()
        self.service_grid.setSpacing(14)
        self.service_cards = [self._lookup_card('job_type_options'), self._lookup_card('equipment_options')]
        self.service_grid.addWidget(self.service_cards[0], 0, 0)
        self.service_grid.addWidget(self.service_cards[1], 1, 0)
        layout.addLayout(self.service_grid)
        self._arrange_services()
        widget, hint = card('Customer service setup', 'Set visit frequency, standard charges and usual equipment on each customer’s page.')
        hint.addWidget(button('Go to Customers', self.customers_requested.emit, 'accent'))
        layout.addWidget(widget)
        layout.addStretch()

    def _arrange_services(self):
        if not hasattr(self, 'service_grid'): return
        side_by_side = self.width() >= 1120
        for widget in self.service_cards:
            self.service_grid.removeWidget(widget)
        self.service_grid.addWidget(self.service_cards[0], 0, 0)
        self.service_grid.addWidget(self.service_cards[1], 0 if side_by_side else 1, 1 if side_by_side else 0)
        self.service_grid.setColumnStretch(0, 1)
        self.service_grid.setColumnStretch(1, 1 if side_by_side else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_services()

    def _payments(self):
        layout = self._section('Payment methods', 'Choose how customers can pay.')
        layout.addWidget(self._lookup_card('payment_type_options'))
        widget, inner = card('Default for new customers', 'You can change this in each customer’s Service setup. Existing customers keep their own payment method.')
        self.default_payment = combo()
        self.default_payment.addItem('No default', '')
        for value in self.settings.payment_type_options:
            self.default_payment.addItem(value, value)
        self.default_payment.setCurrentIndex(max(0, self.default_payment.findData(self.settings.default_payment_method)))
        self.default_payment.currentIndexChanged.connect(lambda: self._set('default_payment_method', self.default_payment.currentData()))
        inner.addWidget(self.default_payment)
        layout.addWidget(widget)
        layout.addStretch()

    def _screen_layout(self):
        layout = self._section('Screen layout', 'Choose the details shown in your customer and job lists.')
        self.column_checks = {}
        self.column_previews = {}
        for entity, title in [('customers', 'Customers'), ('jobs', 'Jobs')]:
            widget, inner = card(title, 'Essential details stay visible so records are easy to identify.' + (' Customer names are always shown for jobs.' if entity == 'jobs' else ''))
            self.column_checks[entity] = {}
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(10)
            inner.addLayout(grid)
            position = 0
            for field in self._fields(entity):
                if not field.enabled:
                    continue
                check = QCheckBox(field.label)
                check.setChecked(field.browse_column or field.key in PROTECTED_COLUMNS[entity])
                if field.key in PROTECTED_COLUMNS[entity]:
                    check.setEnabled(False)
                    check.setToolTip('This detail stays visible to help identify the record.')
                self.column_checks[entity][field.key] = check
                check.toggled.connect(lambda enabled, f=field, e=entity: self._column_changed(e, f, enabled))
                grid.addWidget(check, position // 2, position % 2)
                position += 1
            inner.addWidget(button('Edit a label…', lambda checked=False, e=entity: self.edit_label(e), 'link'))
            preview = label('', 'SettingsPreview')
            self.column_previews[entity] = preview
            inner.addWidget(preview)
            self._preview(entity)
            layout.addWidget(widget)
        widget, inner = card('Jobs preferences')
        self.remember_filters = QCheckBox('Remember my last filters')
        self.remember_filters.setChecked(self.settings.remember_jobs_filters)
        self.remember_filters.toggled.connect(lambda value: self._set('remember_jobs_filters', value))
        inner.addWidget(self.remember_filters)
        inner.addWidget(label('Remembers status, date range and grouping. Search text is not saved.', 'PageHelper'))
        inner.addWidget(label('Start by grouping jobs by', 'PageHelper'))
        self.default_group = combo()
        for caption, value in [('Scheduled day', 'date'), ('Completed day', 'completed'), ('Customer', 'customer'), ('Status', 'status')]:
            self.default_group.addItem(caption, value)
        self.default_group.setCurrentIndex(self.default_group.findData(self.settings.jobs_default_group))
        self.default_group.currentIndexChanged.connect(lambda: self._set('jobs_default_group', self.default_group.currentData()))
        inner.addWidget(self.default_group)
        inner.addWidget(label('The starting group is used when filters are not remembered.', 'PageHelper'))
        layout.addWidget(widget)
        layout.addStretch()

    def _preview(self, entity):
        fields = [f.label for f in self._fields(entity) if f.enabled and (f.browse_column or f.key in PROTECTED_COLUMNS[entity])]
        if entity == 'jobs':
            fields.insert(0, 'Customer')
        self.column_previews[entity].setText('List preview: ' + '  ·  '.join(fields))

    def _column_changed(self, entity, field, enabled):
        field.browse_column = enabled
        self._preview(entity)
        self._changed()

    def _questions(self):
        layout = self._section('Extra information', 'Add a question to customer or job details. Saved answers are kept when you stop using a question.')
        layout.addWidget(button('Add a question', self.add_field, 'primary'))
        for entity, title in [('customers', 'Customer questions'), ('jobs', 'Job questions')]:
            widget, inner = card(title)
            fields = [f for f in self._fields(entity) if f.key not in CORE_FIELDS[entity]]
            if not fields:
                inner.addWidget(label('No extra questions yet.', 'PageHelper'))
            for field in fields:
                row = QHBoxLayout()
                type_name = dict((value, title) for title, value in ANSWER_TYPES)[field.field_type]
                row.addWidget(label(field.label + ' · ' + type_name + ('' if field.enabled else ' · Not in use'), 'SettingsRowName'), 1)
                row.addWidget(button('Edit', lambda checked=False, e=entity, f=field: self.edit_field(e, f), 'link'))
                inner.addLayout(row)
            layout.addWidget(widget)
        layout.addWidget(label('Core details are protected. Their answer types cannot be changed or switched off.', 'SettingsPreview'))
        layout.addStretch()

    def _backups(self):
        layout = self._section('Backups & help', 'Keep a spare copy of your records.')
        widget, inner = card('Your backups')
        self.backup_status = label('', 'SettingsPreview')
        inner.addWidget(self.backup_status)
        available = bool(self.owner and self.owner.backup_manager)
        self.backup_button = button('Back up now', self.back_up_now, 'primary')
        self.backup_button.setEnabled(available)
        inner.addWidget(self.backup_button)
        open_button = button('Open backup folder', self.open_backup_folder)
        open_button.setEnabled(available)
        inner.addWidget(open_button)
        inner.addWidget(label('Backups are also made automatically while the app is open. Keep a copy on another drive for protection if this computer fails.', 'PageHelper'))
        layout.addWidget(widget)
        widget, inner = card('Restore a backup', 'Recover your records from a saved copy. You will review the backup date and what will change before restoring.')
        restore_button = button('Choose a backup…', self.restore_backup)
        restore_button.setEnabled(available)
        inner.addWidget(restore_button)
        layout.addWidget(widget)
        widget, inner = card('Need a hand?')
        inner.addWidget(label('Customers: keep contact details and Service setup together.\nJobs: plan visits, track payment and select jobs or whole days for CSV export.\nSettings: save your changes before leaving.\nBackups: check the date carefully before restoring an older copy.', 'PageHelper'))
        inner.addWidget(button('Open help', self.open_help, 'accent'))
        layout.addWidget(widget)
        self.refresh_backup_status()
        layout.addStretch()

    def open_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Using ShiningKnights')
        dialog.setMinimumWidth(510)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(label('Using ShiningKnights', 'PageTitle'))
        for title, text in [
            ('Customers', 'Keep contact details here. Use Service setup for visit frequency, standard charges and usual equipment.'),
            ('Jobs', 'Use the filters to find visits. Tick individual jobs or an entire day, then use Export CSV.'),
            ('Settings', 'Save changes when you finish. Stop using a choice or question to hide it without deleting saved history.'),
            ('Backups', 'Use Back up now for a spare copy. Copy the whole backup folder to another drive to keep records and settings together. These backups are restored by this app on this computer.'),
            ('Restoring', 'Choose a backup and check its date. Restoring replaces current records. A safety copy is created first; you can choose that copy if you need to undo a restore.')]:
            layout.addWidget(label(title, 'SectionTitle'))
            layout.addWidget(label(text, 'PageHelper'))
        layout.addWidget(button('Close', dialog.accept))
        dialog.exec()

    def _fields(self, entity):
        return self.settings.customer_fields if entity == 'customers' else self.settings.job_fields

    def _set(self, attr, value):
        setattr(self.settings, attr, value)
        if attr == 'remember_jobs_filters' and not value:
            self.settings.jobs_filters = {}
        self._changed()

    @property
    def is_dirty(self):
        return self.settings.to_dict() != self.saved_settings.to_dict()

    def _changed(self):
        dirty = self.is_dirty
        self.save_button.setEnabled(dirty)
        self.save_status.setText('Unsaved changes' if dirty else 'No changes to save')

    def edit_choice(self, attr, old=None):
        value, accepted = QInputDialog.getText(self, 'Edit choice' if old else 'Add choice', 'Name', text=old or '')
        if not accepted:
            return
        value = value.strip()
        all_choices = getattr(self.settings, attr) + self.settings.inactive_options.get(attr, [])
        if not value or any(v.casefold() == value.casefold() and v != old for v in all_choices):
            QMessageBox.warning(self, 'Check the name', 'Enter a name that is not already in the list.')
            return
        choices = getattr(self.settings, attr)
        if old:
            choices[choices.index(old)] = value
            if attr == 'payment_type_options' and self.settings.default_payment_method == old:
                self.settings.default_payment_method = value
        else:
            choices.append(value)
        self._rebuild()
        self._changed()

    def toggle_choice(self, attr, value):
        active = getattr(self.settings, attr)
        inactive = self.settings.inactive_options.setdefault(attr, [])
        if value in active:
            if QMessageBox.question(self, 'Stop using this choice?', 'It will no longer appear as a new choice. Existing customers and job history keep their saved values. Update any affected customer Service setup before creating their next job.') != QMessageBox.StandardButton.Yes:
                return
            active.remove(value)
            inactive.append(value)
            if attr == 'payment_type_options' and self.settings.default_payment_method == value:
                self.settings.default_payment_method = ''
        else:
            inactive.remove(value)
            active.append(value)
        if not inactive:
            self.settings.inactive_options.pop(attr, None)
        self._rebuild()
        self._changed()

    def edit_label(self, entity):
        dialog = QDialog(self)
        dialog.setWindowTitle('Edit a label')
        dialog.setMinimumWidth(440)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)
        layout.addWidget(label('Edit a label', 'SectionTitle'))
        layout.addWidget(label('Choose a detail, then enter the label you want to see.', 'PageHelper'))
        selector = combo()
        fields = self._fields(entity)
        for field in fields: selector.addItem(field.label)
        editor = QLineEdit(fields[0].label)
        selector.currentIndexChanged.connect(lambda index: editor.setText(fields[index].label))
        layout.addWidget(selector)
        layout.addWidget(editor)
        error = label('', 'SettingsError')
        layout.addWidget(error)
        def accept():
            if not editor.text().strip(): error.setText('Enter a label for this detail.')
            else: dialog.accept()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            fields[selector.currentIndex()].label = editor.text().strip()
            self._rebuild()
            self._changed()

    def add_field(self, *_):
        self._field_dialog('customers')

    def edit_field(self, entity, field):
        self._field_dialog(entity, field)

    def _field_dialog(self, entity, field=None):
        dialog = FieldDialog(entity, self, definition=field, existing_keys=[f.key for f in self._fields(entity)])
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        entity = dialog.entity.currentData()
        fields = self._fields(entity)
        definition = dialog.definition()
        # Recompute keys for the selected entity after the dialog's location changes.
        if field is None:
            dialog.existing_keys.update(f.key for f in fields)
            definition = dialog.definition()
            fields.append(definition)
        else:
            fields[fields.index(field)] = definition
        self._rebuild()
        self._changed()

    def save(self):
        if not self.is_dirty:
            return True
        candidate = copy.deepcopy(self.settings)
        # These identifying columns cannot be hidden via the user-facing editor.
        for entity in ('customers', 'jobs'):
            fields = candidate.customer_fields if entity == 'customers' else candidate.job_fields
            for field in fields:
                if field.key in PROTECTED_COLUMNS[entity]:
                    field.browse_column = True
        try:
            candidate.validate()
            self.store.save(candidate)
        except Exception:
            self.save_status.setText('Changes could not be saved. Please try again.')
            QMessageBox.warning(self, 'Settings could not be saved', 'Your previous settings have been kept. Check the choices and labels, then try again.')
            return False
        self.settings = copy.deepcopy(candidate)
        self.saved_settings = copy.deepcopy(candidate)
        self.settings_saved.emit(candidate)
        self._rebuild()
        self.save_button.setEnabled(False)
        self.save_status.setText('Changes saved')
        return True

    def discard(self):
        self.settings = copy.deepcopy(self.saved_settings)
        self._rebuild()
        self._changed()

    def confirm_leave(self):
        if not self.is_dirty:
            return True
        dialog = UnsavedChangesDialog(self)
        dialog.exec()
        if dialog.choice == 'save':
            return self.save()
        if dialog.choice == 'discard':
            self.discard()
            return True
        return False

    def sync_runtime_filters(self, filters):
        # Runtime filter changes do not count as edits in the Settings form.
        if self.settings.remember_jobs_filters:
            self.settings.jobs_filters = copy.deepcopy(filters)
        self.saved_settings.jobs_filters = copy.deepcopy(filters)

    def reset_settings(self, settings):
        self.settings = copy.deepcopy(settings)
        self.saved_settings = copy.deepcopy(settings)
        self._rebuild()
        self._changed()

    def refresh_backup_status(self, message=None):
        if message:
            self.backup_status.setText(message)
            return
        manager = self.owner.backup_manager if self.owner else None
        try:
            latest = manager.latest_backup() if manager else None
            if latest:
                timestamp = datetime.fromtimestamp(latest.stat().st_mtime).strftime('%d %B %Y, %I:%M %p')
                self.backup_status.setText('Last successful backup: ' + timestamp)
            else:
                self.backup_status.setText('No backup yet.' if manager else 'Backups are unavailable in this session.')
        except OSError:
            self.backup_status.setText('The backup folder could not be read. Please try again.')

    def back_up_now(self):
        if self.confirm_leave():
            self.owner.manual_backup()

    def open_backup_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        if self.owner and self.owner.backup_manager:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.owner.backup_manager.backup_dir))):
                self.refresh_backup_status('The backup folder could not be opened.')

    def restore_backup(self):
        if self.confirm_leave() and self.owner:
            self.owner.restore_database_backup()
