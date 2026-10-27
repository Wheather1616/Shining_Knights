"""Configuration-driven forms shared by customer and job dialogs."""
from __future__ import annotations
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractSpinBox, QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QMessageBox, QScrollArea, QVBoxLayout, QHBoxLayout, QWidget, QFrame, QLayout, QSizePolicy)

from ..config import CORE_FIELDS
from .form_controls import ChoiceGrid, WorkTypeGrid, ClickComboBox, DateInput, IntervalSpinBox, NumericInput, SearchCustomerCombo, GroupedWorkTypeGrid
from .form_sections import SectionCard, SelectionDisclosure
from ..models import CustomerRecord, JobRecord, ValidationError, job_types

class RecordForm(QWidget):
    """Keep original field widgets/data contract; only restructure presentation."""
    def __init__(self, settings, entity: str, values: dict[str, Any], parent=None):
        super().__init__(parent)
        self.setObjectName('RecordForm')
        self.entity = entity
        self.definitions = settings.fields_for(entity)
        self.widgets = {}
        self.original_custom = dict(values.get('custom_fields') or {})
        self.sections = {}
        self._definitions = {f.key: f for f in self.definitions}
        self.layout_cards = QVBoxLayout(self)
        self.layout_cards.setContentsMargins(4, 4, 4, 10)
        self.layout_cards.setSpacing(12)
        # Keep the scroll widget's minimum height in sync with every accordion.
        self.layout_cards.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
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
                if f.key in ('default_job_type', 'job_type'):
                    w = GroupedWorkTypeGrid(f.options, job_types(value), values.get(f.key + '_sides', {}),
                                     empty_text='No job types available. Add them in Settings.')
                else:
                    w = ChoiceGrid(f.options, value or [])
            elif f.field_type == 'textarea':
                from PySide6.QtWidgets import QPlainTextEdit
                w = QPlainTextEdit()
                w.setMaximumHeight(110)
                w.setPlaceholderText('Add useful information or access instructions…')
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
                w = NumericInput(r'[0-9]{0,15}' if f.key == 'phone' else r'[0-9]{0,4}',
                                 re.sub(r'[^0-9]', '', str(value or '')))
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
        self.layout_cards.addStretch()

    def _section(self, key, title, subtitle='', symbol='✦', *, expanded=True, collapsible=False):
        card = SectionCard(title, subtitle, symbol, expanded=expanded, collapsible=collapsible)
        self.sections[key] = card
        self.layout_cards.addWidget(card)
        return card

    def _caption(self, key):
        definition = self._definitions[key]
        return definition.label + (' *' if definition.required or key == 'first_name' else '')

    def _row(self, card, key):
        if key in self.widgets and self._definitions[key].enabled:
            card.add_field(self._caption(key), self.widgets[key])

    def _pair(self, card, *keys):
        valid = [key for key in keys if key in self.widgets and self._definitions[key].enabled]
        if len(valid) == 1:
            self._row(card, valid[0])
        elif valid:
            card.add_pair(*[(self._caption(key), self.widgets[key]) for key in valid])

    def _choices(self, card, key, title, *, expanded=False):
        if key in self.widgets and self._definitions[key].enabled:
            disclosure = SelectionDisclosure(title, self.widgets[key], expanded=expanded)
            card.add_widget(disclosure)

    def _customer_rows(self, legacy_name):
        contact = self._section('contact', 'Contact details', 'Who we are working with and how to reach them.', '♙')
        self._pair(contact, 'first_name', 'last_name')
        if legacy_name:
            contact.add_hint('Existing full name retained. You can separate first and last names above.')
        self._row(contact, 'business_name')
        self._pair(contact, 'phone', 'email')

        address = self._section('address', 'Service address', 'Where the work will be carried out.', '⌖')
        self._pair(address, 'address_line_1', 'address_line_2')
        self._pair(address, 'suburb', 'state', 'postcode')

        rhythm = self._section('rhythm', 'Service rhythm', 'Set the recurrence for future bookings.', '▦')
        frequency = QWidget()
        frequency.setObjectName('FormFieldRow')
        row = QHBoxLayout(frequency)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self.widgets['frequency_value'], 1)
        row.addWidget(self.widgets['frequency_unit'], 2)
        rhythm.add_field('Service frequency', frequency)
        self.frequency_hint = QLabel()
        self.frequency_hint.setObjectName('FormFieldHint')
        self.frequency_hint.setWordWrap(True)
        rhythm.add_widget(self.frequency_hint)
        self._row(rhythm, 'first_service_date')

        defaults = self._section('defaults', 'Usual service defaults',
                                 'Saved defaults for new visits. Edit named services in the Services tab.',
                                 '⚙', expanded=False, collapsible=True)
        self._choices(defaults, 'default_job_type', 'Nature of job', expanded=False)
        self._choices(defaults, 'default_equipment', 'Equipment required', expanded=False)
        self._pair(defaults, 'default_fee', 'default_hours')
        self._row(defaults, 'default_payment_type')
        defaults.add_hint('Fee is the total charge. Hours are optional and do not change the fee.')

        extra = self._section('extra', 'Notes & extra information', 'Optional details and custom fields.',
                              '✎', expanded=False, collapsible=True)
        self._row(extra, 'notes')
        self._row(extra, 'active')
        for f in self.definitions:
            if f.key not in CORE_FIELDS['customers'] and f.enabled:
                self._row(extra, f.key)

    def _job_rows(self):
        overview = self._section('overview', 'Job overview', 'Schedule and track this visit.', '▦')
        self._pair(overview, 'scheduled_date', 'completed_date')
        self._row(overview, 'status')
        details = self._section('details', 'Service details', 'What work is included in this visit.', '✦')
        self._choices(details, 'job_type', 'Nature of job', expanded=False)
        self._choices(details, 'equipment', 'Equipment required', expanded=False)
        pricing = self._section('pricing', 'Pricing & payment', 'Set the charge and payment details.', '$')
        self._pair(pricing, 'fee', 'hours')
        self._pair(pricing, 'payment_type', 'payment_status')
        pricing.add_hint('Hours are optional; they do not change the total fee.')
        notes = self._section('notes', 'Notes', 'Access details and any special instructions.', '✎',
                              expanded=False, collapsible=True)
        self._row(notes, 'notes')
        # Preserve user-configured fields without guessing at their meaning.
        more = [f.key for f in self.definitions if f.enabled and f.key not in CORE_FIELDS['jobs']]
        additional = [key for key in self.widgets if key not in (
            'scheduled_date', 'completed_date', 'status', 'job_type', 'equipment', 'fee',
            'hours', 'payment_type', 'payment_status', 'notes')]
        if additional:
            other = self._section('other', 'Additional job details', 'Configured fields.', '⋯',
                                  expanded=False, collapsible=True)
            for key in additional:
                self._row(other, key)

    def _frequency_changed(self, value):
        self.widgets['frequency_unit'].setEnabled(value > 0)
        self.frequency_hint.setText('0 means one-off / as needed.' if value == 0
                                    else 'Repeat after this many days, weeks, months or years.')

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
                if f.key in ('default_job_type', 'job_type'):
                    result[f.key + '_sides'] = w.selected_sides()
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
        self.setObjectName('RecordDialog')
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
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(self.form)
        outer.addWidget(scroll, 1)
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
    """Job editor with a single scroll region and an explicit customer picker."""
    def __init__(self, db, settings, customer_id=None, job_id=None, parent=None):
        super().__init__(parent)
        self.db, self.settings, self.job_id = db, settings, job_id
        self.saved_id = None
        self.setWindowTitle('Edit job' if job_id else 'Add job')
        self.setObjectName('RecordDialog')
        self.resize(800, 800)
        self.setMinimumSize(610, 550)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(20, 18, 20, 14)
        self.outer.setSpacing(10)
        title = QLabel(self.windowTitle())
        title.setObjectName('PageTitle')
        self.outer.addWidget(title)

        # One scroll area for the entire form, rather than fixed sections above
        # a second tiny viewport. The Save/Cancel bar alone stays in place.
        self.scroll = QScrollArea()
        self.scroll.setObjectName('RecordScroll')
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName('JobFormScrollContent')
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(4, 6, 8, 12)
        self.content_layout.setSpacing(12)
        self.content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.scroll.setWidget(self.scroll_content)
        self.outer.addWidget(self.scroll, 1)

        customers = db.list_customers(include_inactive=bool(job_id))
        self.customer_records = {c['id']: c for c in customers}
        customer_card = SectionCard('Customer', 'Find an existing customer by name, suburb or phone.', '♙', tone='coral')
        self.customer = SearchCustomerCombo()
        self.customer.setAccessibleName('Search for customer')
        for c in customers:
            parts = [c['name'], c.get('suburb') or '', c.get('phone') or '']
            caption = '  ·  '.join(v for v in parts if v)
            if not c['active']:
                caption += ' (inactive)'
            self.customer.addItem(caption, c['id'])
        customer_card.add_field('Customer *', self.customer)
        self.customer_preview = QLabel('Select a customer to see their location and contact details.')
        self.customer_preview.setObjectName('FormLookupPreview')
        self.customer_preview.setWordWrap(True)
        customer_card.add_widget(self.customer_preview)
        self.content_layout.addWidget(customer_card)

        if job_id:
            values = db.get_job(job_id)
            self.customer.select_customer(values['customer_id'])
            self.customer.setEnabled(False)
        else:
            self.customer.select_customer(customer_id)
            selected = self.customer.valid_customer_id()
            values = (asdict(db.new_job_for_customer(selected)) if selected is not None
                      else asdict(JobRecord(0)))
        self._update_customer_preview()
        service_card = SectionCard('Saved service', 'Choose a service to load its normal charge, hours and equipment.', '✦', tone='teal')
        self.service = ClickComboBox()
        self.service.setAccessibleName('Customer service')
        service_card.add_field('Service', self.service)
        self.service_hint = QLabel('Choosing a saved service fills its fee, hours and equipment. You can adjust them below.')
        if job_id:
            self.service_hint.setText('This job keeps its saved details. Choosing another service replaces its defaults.')
        self.service_hint.setObjectName('FormFieldHint')
        self.service_hint.setWordWrap(True)
        service_card.add_widget(self.service_hint)
        self.content_layout.addWidget(service_card)
        self._load_services(values)
        self.service.currentIndexChanged.connect(self._service_changed)
        self._set_form(values)
        # Confirmation is explicit; typing a partial customer name does not
        # silently change or overwrite unfinished job values.
        self.customer.selectionConfirmed.connect(self._customer_changed)
        self.customer.selectionCleared.connect(self._customer_search_cleared)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty('role', 'primary')
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        self.outer.addWidget(buttons)

    def _set_form(self, values):
        old = getattr(self, 'form', None)
        if old is not None:
            self.content_layout.removeWidget(old)
            old.hide()
            old.deleteLater()
        self.form = RecordForm(self.settings, 'jobs', values)
        self.content_layout.addWidget(self.form)
        self.form.widgets['status'].currentIndexChanged.connect(self._status_changed)
        self.scroll_content.updateGeometry()

    def _load_services(self, values):
        self.service.blockSignals(True)
        self.service.clear()
        self.service.addItem('Custom visit / no saved service', None)
        selected = values.get('service_id')
        cid = self.customer.valid_customer_id()
        records = self.db.list_services(cid, include_archived=bool(self.job_id)) if cid is not None else []
        for record in records:
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
        cid = self.customer.valid_customer_id()
        customer = self.db.get_customer(cid) if cid is not None else None
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
            values = asdict(self.db.new_job_for_customer(self.customer.valid_customer_id(), service_id=selected))
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
        self.form.widgets['job_type'].set_sides(values['job_type_sides'])
        for option,checkbox in self.form.widgets['equipment'].checkboxes.items():
            checkbox.setChecked(option in values['equipment'])
        for key in ('fee','hours'):
            self.form.widgets[key].setText(str(values[key]) if values[key] is not None else '')
        notes = self.form.widgets['notes']
        if not notes.toPlainText().strip() or notes.toPlainText().strip() == self._profile_notes:
            notes.setPlainText(values['notes'])
        self._profile_notes = values['notes']
        self._service_name = values['service_name']

    def _customer_changed(self, _confirmed_customer_id=None):
        if self.job_id:
            return
        self._update_customer_preview()
        cid = self.customer.valid_customer_id()
        if cid is not None:
            values = asdict(self.db.new_job_for_customer(cid))
            self._load_services(values)
            self._set_form(values)
            self.scroll_content.updateGeometry()

    def _customer_search_cleared(self):
        # Keep unsaved fields untouched while searching for a different record.
        # A new selection will deliberately load that customer's defaults.
        self.service.setEnabled(False)
        self.customer_preview.setText('Choose a result from the customer list to continue.')

    def _update_customer_preview(self):
        cid = self.customer.valid_customer_id()
        record = self.customer_records.get(cid)
        if record:
            address = ', '.join(str(record.get(key) or '') for key in ('address_line_1', 'suburb')
                                if record.get(key))
            self.customer_preview.setText('⌖  ' + (address or 'Address not set') +
                                          ('     ·     ' + str(record.get('phone')) if record.get('phone') else ''))
        else:
            self.customer_preview.setText('Select a customer to see their location and contact details.')

    def _status_changed(self):
        status = self.form.widgets['status'].currentData()
        completed = self.form.widgets['completed_date']
        if status == 'Completed' and not completed.text(): completed.setText(date.today().strftime('%d/%m/%Y'))
        elif status != 'Completed': completed.clear()

    def save(self):
        try:
            selected = self.customer.valid_customer_id()
            if selected is None: raise ValidationError('Select a customer from the search results before saving.')
            record = JobRecord(customer_id=selected, service_id=self.service.currentData(), service_name=self._service_name, **self.form.values())
            if self.job_id:
                self.db.update_job(self.job_id,record)
                self.saved_id = self.job_id
            else: self.saved_id = self.db.create_job(record)
        except Exception as exc:
            QMessageBox.warning(self,'Job could not be saved',str(exc)); return
        self.accept()
