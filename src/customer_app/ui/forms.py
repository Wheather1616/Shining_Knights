"""Configuration-driven forms shared by customer and job dialogs."""
from __future__ import annotations
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractSpinBox, QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QMessageBox, QScrollArea, QVBoxLayout, QWidget)

from ..config import CORE_FIELDS
from .form_controls import ChoiceGrid, ClickComboBox, DateInput, IntervalSpinBox, NumericInput
from ..models import CustomerRecord, JobRecord, ValidationError, job_types

class RecordForm(QWidget):
    def __init__(self, settings, entity: str, values: dict[str, Any], parent=None):
        super().__init__(parent)
        self.setObjectName('RecordForm')
        self.entity = entity
        self.definitions = settings.fields_for(entity)
        self.widgets = {}
        self.original_custom = dict(values.get('custom_fields') or {})
        self.layout_form = QFormLayout(self)
        self.layout_form.setContentsMargins(18, 18, 18, 18)
        self.layout_form.setHorizontalSpacing(16)
        self.layout_form.setVerticalSpacing(12)
        self.layout_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.layout_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for f in self.definitions:
            if not f.enabled or (entity == 'customers' and f.key == 'name') or (entity == 'jobs' and f.key == 'service_name'):
                continue
            value = values.get(f.key) if f.key in CORE_FIELDS[entity] else self.original_custom.get(f.key)
            if entity == 'customers' and f.key == 'frequency_value':
                w = IntervalSpinBox()
                w.setRange(0, 3650)
                w.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                w.setValue(value or 0)
                w.setAccessibleName('Service frequency number. Zero means one-off.')
            elif f.field_type == 'boolean':
                w = QCheckBox()
                w.setChecked(bool(value))
            elif f.field_type == 'dropdown':
                w = ClickComboBox()
                if f.key == 'frequency_unit':
                    for caption, unit in [('Weeks', 'weeks'), ('Days', 'days'), ('Months', 'months'), ('Years', 'years')]:
                        w.addItem(caption, unit)
                    w.setCurrentIndex(max(0, w.findData(value or 'weeks')))
                else:
                    w.addItem('Choose…', '')
                    for option in f.options:
                        w.addItem(option, option)
                    if value and value not in f.options:
                        w.addItem(str(value) + ' (saved choice)', value)
                    w.setCurrentIndex(max(0, w.findData(value or '')))
            elif f.field_type == 'multiselect':
                if f.key in ('default_job_type','job_type'):
                    w = ChoiceGrid(f.options,job_types(value),empty_text='No job types available. Add them in Settings.')
                else:
                    w = ChoiceGrid(f.options, value or [])
            elif f.field_type == 'textarea':
                from PySide6.QtWidgets import QPlainTextEdit
                w = QPlainTextEdit()
                w.setMaximumHeight(100)
                w.setPlainText(str(value or ''))
            elif f.field_type == 'date':
                w = DateInput(value or '')
            elif f.field_type == 'currency':
                w = NumericInput(r'[0-9]{0,9}(\.[0-9]{0,2})?', value)
                w.setPlaceholderText('e.g. 180.00')
            elif f.key in ('default_hours', 'hours'):
                w = NumericInput(r'[0-9]{0,4}(\.[0-9]{0,2})?', value)
                w.setPlaceholderText('e.g. 1.5')
            elif f.key in ('phone', 'postcode') and entity == 'customers':
                import re
                w = NumericInput(r'[0-9]{0,15}' if f.key == 'phone' else r'[0-9]{0,4}', re.sub(r'[^0-9]', '', str(value or '')))
                w.setPlaceholderText('10–15 digits' if f.key == 'phone' else '4 digits')
            else:
                w = QLineEdit('' if value is None else str(value))
            w.setObjectName(f.key)
            w.setAccessibleName(f.label)
            self.widgets[f.key] = w
        if entity == 'customers':
            legacy_name = not values.get('first_name') and not values.get('last_name') and bool(values.get('name'))
            if legacy_name:
                self.widgets['first_name'].setText(values['name'])
            self._customer_rows(legacy_name)
            self.widgets['frequency_value'].valueChanged.connect(self._frequency_changed)
            self._frequency_changed(self.widgets['frequency_value'].value())
        else:
            self._job_rows()

    def _section(self, text):
        heading = QLabel(text)
        heading.setObjectName('FormSectionTitle')
        self.layout_form.addRow(heading)

    def _pair(self, keys):
        from PySide6.QtWidgets import QGridLayout
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(4)
        for column, key in enumerate(keys):
            f = next(f for f in self.definitions if f.key == key)
            caption = QLabel(f.label + (' *' if key == 'first_name' else ''))
            caption.setObjectName('FormHelper')
            caption.setTextFormat(Qt.TextFormat.PlainText)
            caption.setWordWrap(True)
            caption.setBuddy(self.widgets[key])
            layout.addWidget(caption, 0, column)
            layout.addWidget(self.widgets[key], 1, column)
            layout.setColumnStretch(column, 1)
        return container

    def _row(self, key):
        f = next(f for f in self.definitions if f.key == key)
        if f.enabled:
            self.layout_form.addRow(f.label + (' *' if f.required else ''), self.widgets[key])

    def _customer_rows(self, legacy_name):
        from PySide6.QtWidgets import QHBoxLayout
        self._section('Contact details')
        self.layout_form.addRow('Customer name', self._pair(('first_name', 'last_name')))
        if legacy_name:
            hint = QLabel('Existing full name kept above. Separate first and last names if needed.')
            hint.setObjectName('FormHelper')
            hint.setWordWrap(True)
            self.layout_form.addRow(hint)
        for key in ('business_name', 'phone', 'email'):
            self._row(key)
        self._section('Service address')
        for key in ('address_line_1', 'address_line_2', 'suburb', 'state', 'postcode'):
            self._row(key)
        self._section('Service setup')
        interval = QWidget()
        row = QHBoxLayout(interval)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.widgets['frequency_value'], 1)
        row.addWidget(self.widgets['frequency_unit'], 1)
        self.layout_form.addRow('Service frequency', interval)
        self.frequency_hint = QLabel()
        self.frequency_hint.setObjectName('FormHelper')
        self.layout_form.addRow('', self.frequency_hint)
        self._row('first_service_date')
        self._section('Usual service defaults')
        hint = QLabel('These are the defaults for the usual service. Add other named services in the customer’s Services tab after saving.')
        hint.setObjectName('FormHelper'); hint.setWordWrap(True); self.layout_form.addRow(hint)
        for key in ('default_job_type', 'default_equipment'):
            self._row(key)
        self.layout_form.addRow('Service charge', self._pair(('default_fee', 'default_hours')))
        hint = QLabel('Fee is the total charge. Hours are optional and do not change the fee.')
        hint.setObjectName('FormHelper')
        hint.setWordWrap(True)
        self.layout_form.addRow('', hint)
        self._row('default_payment_type')
        self._section('Notes & extra information')
        self._row('notes')
        self._row('active')
        for f in self.definitions:
            if f.key not in CORE_FIELDS['customers'] and f.enabled:
                self._row(f.key)

    def _job_rows(self):
        for f in self.definitions:
            if not f.enabled or f.key in ('hours','service_name'):
                continue
            if f.key == 'fee':
                self.layout_form.addRow('Service charge', self._pair(('fee', 'hours')))
            else:
                self._row(f.key)

    def _frequency_changed(self, value):
        self.widgets['frequency_unit'].setEnabled(value > 0)
        self.frequency_hint.setText('0 means one-off / as needed.' if value == 0 else 'Repeat after this many days, weeks, months or years.')

    def values(self) -> dict[str, Any]:
        result = {'custom_fields': dict(self.original_custom)}
        for f in self.definitions:
            if not f.enabled or (self.entity == 'customers' and f.key == 'name') or (self.entity == 'jobs' and f.key == 'service_name'):
                continue
            w = self.widgets[f.key]
            if self.entity == 'customers' and f.key == 'frequency_value':
                value = w.value() or None
            elif f.field_type == 'boolean':
                value = w.isChecked()
            elif f.field_type == 'dropdown':
                value = w.currentData()
            elif f.field_type == 'multiselect':
                value = w.selected_values()
            elif f.field_type == 'textarea':
                value = w.toPlainText().strip()
            else:
                value = w.text().strip()
                if value and f.field_type == 'date':
                    parsed = None
                    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                        try:
                            parsed = datetime.strptime(value, fmt).date().isoformat()
                            break
                        except ValueError:
                            continue
                    if parsed is None:
                        raise ValidationError(f'{f.label}: use dd/mm/yyyy or YYYY-MM-DD.')
                    value = parsed
            if f.key in CORE_FIELDS[self.entity]:
                result[f.key] = value
            else:
                result['custom_fields'][f.key] = value
        if self.entity == 'customers':
            if not result['first_name']:
                raise ValidationError('First name is required.')
            result['name'] = ' '.join(filter(None, (result['first_name'], result['last_name'])))
            if result['frequency_value'] is None:
                result['frequency_unit'] = ''
        return result

class CustomerDialog(QDialog):
    def __init__(self, db, settings, customer_id=None, parent=None):
        super().__init__(parent)
        self.db, self.customer_id = db, customer_id
        self.saved_id = None
        self.setWindowTitle('Edit customer' if customer_id else 'Add customer')
        self.resize(760,780)
        self.setMinimumSize(560, 620)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20,18,20,18); outer.setSpacing(14)
        title = QLabel(self.windowTitle()); title.setObjectName('PageTitle'); outer.addWidget(title)
        helper = QLabel('Fields marked * are required. Dates can be left blank.'); helper.setObjectName('FormHelper'); helper.setWordWrap(True); outer.addWidget(helper)
        c = db.get_customer(customer_id) if customer_id else asdict(CustomerRecord())
        if customer_id is None:
            c['default_payment_type'] = settings.default_payment_method
        self.form = RecordForm(settings,'customers',c)
        scroll = QScrollArea(); scroll.setObjectName('RecordScroll')
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.form)
        outer.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty('role','primary')
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def save(self):
        try:
            record = CustomerRecord(**self.form.values())
            if self.customer_id:
                self.db.update_customer(self.customer_id,record)
                self.saved_id = self.customer_id
            else: self.saved_id = self.db.create_customer(record)
        except Exception as exc:
            QMessageBox.warning(self,'Customer could not be saved',str(exc)); return
        self.accept()

class JobDialog(QDialog):
    def __init__(self, db, settings, customer_id=None, job_id=None, parent=None):
        super().__init__(parent)
        self.db, self.settings, self.job_id = db, settings, job_id
        self.saved_id = None
        self.setWindowTitle('Edit job' if job_id else 'Add job')
        self.resize(610,730)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(20,18,20,18); self.outer.setSpacing(14)
        title = QLabel(self.windowTitle()); title.setObjectName('PageTitle'); self.outer.addWidget(title)
        self.customer = ClickComboBox()
        self.outer.addWidget(QLabel('Customer'))
        self.outer.addWidget(self.customer)
        customers = db.list_customers(include_inactive=bool(job_id))
        for c in customers: self.customer.addItem(c['name'] + (' (inactive)' if not c['active'] else ''),c['id'])
        if job_id:
            values = db.get_job(job_id)
            self.customer.setCurrentIndex(self.customer.findData(values['customer_id']))
            self.customer.setEnabled(False)
        else:
            if customer_id is not None: self.customer.setCurrentIndex(self.customer.findData(customer_id))
            selected = self.customer.currentData()
            values = asdict(db.new_job_for_customer(selected)) if selected is not None else asdict(JobRecord(0))
        self.service = ClickComboBox()
        self.service.setAccessibleName('Customer service')
        self.outer.addWidget(QLabel('Service'))
        self.outer.addWidget(self.service)
        self.service_hint = QLabel('Choosing a service fills its fee, hours and equipment. Adjust them below for this visit.')
        if job_id:
            self.service_hint.setText('This job keeps its saved details. Choosing another service replaces its fee, hours and equipment.')
        self.service_hint.setObjectName('FormHelper'); self.service_hint.setWordWrap(True); self.outer.addWidget(self.service_hint)
        self._load_services(values)
        self.service.currentIndexChanged.connect(self._service_changed)
        self.scroll = QScrollArea(); self.scroll.setObjectName('RecordScroll')
        self.scroll.setWidgetResizable(True)
        self.outer.addWidget(self.scroll)
        self._set_form(values)
        self.customer.currentIndexChanged.connect(self._customer_changed)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty('role','primary')
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        self.outer.addWidget(buttons)

    def _set_form(self, values):
        self.form = RecordForm(self.settings,'jobs',values)
        self.scroll.setWidget(self.form)
        self.form.widgets['status'].currentIndexChanged.connect(self._status_changed)

    def _load_services(self, values):
        self.service.blockSignals(True)
        self.service.clear()
        self.service.addItem('Custom visit / no saved service', None)
        selected = values.get('service_id')
        for record in self.db.list_services(self.customer.currentData(),include_archived=bool(self.job_id)):
            if not record['active'] and record['id'] != selected:
                continue
            text = record['name'] + (' · Usual' if record['is_default'] else '') + (' (archived)' if not record['active'] else '')
            if self.job_id and record['id']==selected and values.get('service_name') and values['service_name'] != record['name']:
                text = values['service_name'] + ' (saved name)' + (' (archived)' if not record['active'] else '')
            self.service.addItem(text, record['id'])
            self.service.setItemData(self.service.count()-1,record['name'],Qt.ItemDataRole.ToolTipRole)
        self.service.setCurrentIndex(max(0,self.service.findData(selected)))
        self.service.blockSignals(False)
        self._selected_service_id = selected
        self._service_name = values.get('service_name','')
        customer = self.db.get_customer(self.customer.currentData()) if self.customer.currentData() else None
        self.service.setEnabled(bool(customer and customer['active']))
        original = self.db.get_service(selected) if selected else None
        self._profile_notes = original['notes'] if original else ''

    def _service_changed(self):
        # Retain dates, status, payment choices and custom answers while changing
        # only the visit defaults. Existing jobs are never refreshed on opening.
        selected = self.service.currentData()
        if selected is None:
            self._selected_service_id = None
            self._service_name = ''
            return
        try:
            values = asdict(self.db.new_job_for_customer(self.customer.currentData(),service_id=selected))
        except ValidationError as exc:
            QMessageBox.warning(self,'Service could not be selected',str(exc))
            self.service.blockSignals(True)
            self.service.setCurrentIndex(max(0,self.service.findData(self._selected_service_id)))
            self.service.blockSignals(False)
            return
        self._selected_service_id = selected
        # Update only the service controls, preserving even unfinished date or
        # custom-field input. No whole-form validation is needed for selection.
        for option,checkbox in self.form.widgets['job_type'].checkboxes.items():
            checkbox.setChecked(option in values['job_type'])
        for option,checkbox in self.form.widgets['equipment'].checkboxes.items():
            checkbox.setChecked(option in values['equipment'])
        for key in ('fee','hours'):
            self.form.widgets[key].setText(values[key] or '')
        notes = self.form.widgets['notes']
        if not notes.toPlainText().strip() or notes.toPlainText().strip() == self._profile_notes:
            notes.setPlainText(values['notes'])
        self._profile_notes = values['notes']
        self._service_name = values['service_name']

    def _customer_changed(self):
        if self.job_id: return
        if self.customer.currentData() is not None:
            values = asdict(self.db.new_job_for_customer(self.customer.currentData()))
            self._load_services(values)
            self._set_form(values)

    def _status_changed(self):
        status = self.form.widgets['status'].currentData()
        completed = self.form.widgets['completed_date']
        if status == 'Completed' and not completed.text(): completed.setText(date.today().strftime('%d/%m/%Y'))
        elif status != 'Completed': completed.clear()

    def save(self):
        try:
            selected = self.customer.currentData()
            if selected is None: raise ValidationError('Add an active customer before creating a job.')
            record = JobRecord(customer_id=selected, service_id=self.service.currentData(), service_name=self._service_name, **self.form.values())
            if self.job_id:
                self.db.update_job(self.job_id,record)
                self.saved_id = self.job_id
            else: self.saved_id = self.db.create_job(record)
        except Exception as exc:
            QMessageBox.warning(self,'Job could not be saved',str(exc)); return
        self.accept()
