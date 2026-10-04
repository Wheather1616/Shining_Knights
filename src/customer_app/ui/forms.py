"""Configuration-driven forms shared by customer and job dialogs."""
from __future__ import annotations
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QScrollArea, QVBoxLayout, QWidget)

from ..config import CORE_FIELDS, FREQUENCIES
from ..models import CustomerRecord, JobRecord, ValidationError

class RecordForm(QWidget):
    def __init__(self, settings, entity: str, values: dict[str, Any], parent=None):
        super().__init__(parent)
        self.setObjectName('RecordForm')
        self.entity = entity
        self.definitions = settings.fields_for(entity)
        self.widgets = {}
        self.original_custom = dict(values.get('custom_fields') or {})
        self.layout_form = QFormLayout(self)
        self.layout_form.setContentsMargins(18,18,18,18)
        self.layout_form.setHorizontalSpacing(16)
        self.layout_form.setVerticalSpacing(12)
        self.layout_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.layout_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        if entity == 'customers':
            self.frequency = QComboBox()
            self.frequency.addItems([*FREQUENCIES,'Other interval'])
            current = (values.get('frequency_value'),values.get('frequency_unit') or '')
            label = next((label for label,pair in FREQUENCIES.items() if pair == current),'Other interval')
            self.frequency.setCurrentText(label)
            self.layout_form.addRow('Service frequency',self.frequency)
        for f in self.definitions:
            if not f.enabled: continue
            value = values.get(f.key) if f.key in CORE_FIELDS[entity] else self.original_custom.get(f.key)
            if f.field_type == 'boolean':
                w = QCheckBox()
                w.setChecked(bool(value))
            elif f.field_type == 'dropdown':
                w = QComboBox()
                w.addItem('Choose…','')
                for option in f.options: w.addItem(option,option)
                if value and value not in f.options:
                    w.addItem(str(value) + ' (saved choice)',value)
                w.setCurrentIndex(max(0,w.findData(value or '')))
            elif f.field_type == 'multiselect':
                w = QListWidget()
                w.setMaximumHeight(135)
                for option in dict.fromkeys([*f.options,*(value or [])]):
                    item = QListWidgetItem(option)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Checked if option in (value or []) else Qt.CheckState.Unchecked)
                    w.addItem(item)
            else:
                # Notes use a taller plain-text input without accepting rich text.
                if f.field_type == 'textarea':
                    from PySide6.QtWidgets import QPlainTextEdit
                    w = QPlainTextEdit()
                    w.setMaximumHeight(100)
                    w.setPlainText(str(value or ''))
                else:
                    w = QLineEdit()
                    w.setText('' if value is None else str(value))
                    if f.field_type == 'date':
                        w.setPlaceholderText('dd/mm/yyyy, or leave blank')
                        if value:
                            try: w.setText(date.fromisoformat(value).strftime('%d/%m/%Y'))
                            except ValueError: pass
                    elif f.field_type == 'currency': w.setPlaceholderText('e.g. 180.00')
            w.setObjectName(f.key)
            self.widgets[f.key] = w
            self.layout_form.addRow(f.label + (' *' if f.required else ''), w)
        if entity == 'customers':
            self.frequency.currentTextChanged.connect(self._set_frequency)
            self._set_frequency(self.frequency.currentText(), preserve=True)

    def _set_frequency(self, label, preserve=False):
        custom = label == 'Other interval'
        for key in ('frequency_value','frequency_unit'): self.widgets[key].setEnabled(custom)
        if not custom:
            interval,unit = FREQUENCIES[label]
            self.widgets['frequency_value'].setText('' if interval is None else str(interval))
            self.widgets['frequency_unit'].setCurrentIndex(max(0,self.widgets['frequency_unit'].findData(unit)))

    def values(self) -> dict[str, Any]:
        result = {'custom_fields':dict(self.original_custom)}
        for f in self.definitions:
            if not f.enabled: continue
            w = self.widgets[f.key]
            if f.field_type == 'boolean': value = w.isChecked()
            elif f.field_type == 'dropdown': value = w.currentData()
            elif f.field_type == 'multiselect':
                value = [w.item(i).text() for i in range(w.count()) if w.item(i).checkState() == Qt.CheckState.Checked]
            elif f.field_type == 'textarea': value = w.toPlainText().strip()
            else:
                value = w.text().strip()
                if value and f.field_type == 'date':
                    parsed = None
                    for fmt in ('%d/%m/%Y','%Y-%m-%d'):
                        try: parsed = datetime.strptime(value,fmt).date().isoformat(); break
                        except ValueError: continue
                    if parsed is None: raise ValidationError(f'{f.label}: use dd/mm/yyyy or YYYY-MM-DD.')
                    value = parsed
            if f.key in CORE_FIELDS[self.entity]: result[f.key] = value
            else: result['custom_fields'][f.key] = value
        if self.entity == 'customers' and result.get('frequency_value') == '': result['frequency_value'] = None
        return result

class CustomerDialog(QDialog):
    def __init__(self, db, settings, customer_id=None, parent=None):
        super().__init__(parent)
        self.db, self.customer_id = db, customer_id
        self.saved_id = None
        self.setWindowTitle('Edit customer' if customer_id else 'Add customer')
        self.resize(610,750)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20,18,20,18); outer.setSpacing(14)
        title = QLabel(self.windowTitle()); title.setObjectName('PageTitle'); outer.addWidget(title)
        helper = QLabel('Fields marked * are required. Dates can be left blank.'); helper.setObjectName('FormHelper'); helper.setWordWrap(True); outer.addWidget(helper)
        c = db.get_customer(customer_id) if customer_id else asdict(CustomerRecord())
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
        self.customer = QComboBox()
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

    def _customer_changed(self):
        if self.job_id: return
        if self.customer.currentData() is not None:
            self._set_form(asdict(self.db.new_job_for_customer(self.customer.currentData())))

    def _status_changed(self):
        status = self.form.widgets['status'].currentData()
        completed = self.form.widgets['completed_date']
        if status == 'Completed' and not completed.text(): completed.setText(date.today().strftime('%d/%m/%Y'))
        elif status != 'Completed': completed.clear()

    def save(self):
        try:
            selected = self.customer.currentData()
            if selected is None: raise ValidationError('Add an active customer before creating a job.')
            record = JobRecord(customer_id=selected, **self.form.values())
            if self.job_id:
                self.db.update_job(self.job_id,record)
                self.saved_id = self.job_id
            else: self.saved_id = self.db.create_job(record)
        except Exception as exc:
            QMessageBox.warning(self,'Job could not be saved',str(exc)); return
        self.accept()
