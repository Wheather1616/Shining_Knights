"""Editable lookup lists and per-entity field configuration."""
from __future__ import annotations
import copy
import re

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QTabWidget, QTableWidget, QVBoxLayout, QWidget, QHeaderView)

from ..config import CORE_FIELDS, FIELD_TYPES, FieldDefinition

class FieldDialog(QDialog):
    def __init__(self, entity, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add custom ' + entity.rstrip('s') + ' field')
        self.resize(440,360)
        form = QFormLayout(self)
        self.label = QLineEdit()
        self.key = QLineEdit()
        self.key.setPlaceholderText('e.g. gate_code')
        self.kind = QComboBox()
        self.kind.addItems(FIELD_TYPES)
        self.options = QPlainTextEdit()
        self.options.setPlaceholderText('For dropdown / multiselect: one choice per line')
        self.required = QCheckBox()
        form.addRow('Label',self.label); form.addRow('Stable field key',self.key)
        form.addRow('Type',self.kind); form.addRow('Choices',self.options); form.addRow('Required',self.required)
        self.label.textEdited.connect(lambda t:self.key.setText(re.sub(r'[^a-z0-9]+','_',t.lower()).strip('_')))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def definition(self):
        return FieldDefinition(self.key.text().strip(),self.label.text().strip(),self.kind.currentText(),self.required.isChecked(),False,
            [v.strip() for v in self.options.toPlainText().splitlines() if v.strip()])

class FieldSettingsPage(QWidget):
    settings_saved = Signal(object)

    def __init__(self, settings, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.settings = copy.deepcopy(settings)
        layout = QVBoxLayout(self)
        explanation = QLabel('Configure equipment, services, payment methods and fields. Core field types stay fixed.\nDisable custom fields to hide them while preserving saved values. Custom field keys and types stay fixed after creation.')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        lookups = QWidget(); l = QFormLayout(lookups)
        self.lookups = {}
        for attr,label in [('equipment_options','Equipment'),('job_type_options','Nature of job'),('payment_type_options','Payment methods')]:
            editor = QPlainTextEdit('\n'.join(getattr(self.settings,attr)))
            editor.setPlaceholderText('One option per line')
            l.addRow(label,editor)
            self.lookups[attr] = editor
        self.tabs.addTab(lookups,'Choices')
        self.tables = {}
        for entity in ('customers','jobs'):
            page = QWidget(); p = QVBoxLayout(page)
            table = QTableWidget()
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels(['Key','Label','Type','Required','List column','Enabled','Custom choices'])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setStretchLastSection(True)
            p.addWidget(table)
            add = QPushButton('Add custom field')
            add.clicked.connect(lambda checked=False,e=entity:self.add_field(e))
            p.addWidget(add)
            self.tables[entity] = table
            self.tabs.addTab(page,entity.title())
            self._fill(entity)
        row = QHBoxLayout()
        self.save_button = QPushButton('Save configuration')
        self.save_button.clicked.connect(self.save)
        row.addStretch(); row.addWidget(self.save_button)
        layout.addLayout(row)

    def _fields(self, entity):
        return self.settings.customer_fields if entity == 'customers' else self.settings.job_fields

    def _fill(self, entity):
        table = self.tables[entity]
        fields = self._fields(entity)
        table.setRowCount(len(fields))
        for row,f in enumerate(fields):
            core = f.key in CORE_FIELDS[entity]
            key = QLineEdit(f.key); key.setReadOnly(True)
            label = QLineEdit(f.label)
            kind = QLineEdit(f.field_type); kind.setReadOnly(True)
            required = QCheckBox(); required.setChecked(f.required)
            if f.key in ('name','status','payment_status'): required.setEnabled(False)
            browse = QCheckBox(); browse.setChecked(f.browse_column)
            enabled = QCheckBox(); enabled.setChecked(f.enabled); enabled.setEnabled(not core)
            choices = QPlainTextEdit('\n'.join(f.options))
            choices.setMaximumHeight(65)
            choices.setEnabled(not core and f.field_type in ('dropdown','multiselect'))
            for col,w in enumerate((key,label,kind,required,browse,enabled,choices)):
                table.setCellWidget(row,col,w)
            table.setRowHeight(row,68 if choices.isEnabled() else 40)

    def _read_tables(self, candidate):
        for entity,table in self.tables.items():
            fields = candidate.customer_fields if entity == 'customers' else candidate.job_fields
            for row,f in enumerate(fields):
                f.label = table.cellWidget(row,1).text().strip()
                f.required = table.cellWidget(row,3).isChecked()
                f.browse_column = table.cellWidget(row,4).isChecked()
                f.enabled = table.cellWidget(row,5).isChecked()
                if f.key not in CORE_FIELDS[entity] and f.field_type in ('dropdown','multiselect'):
                    f.options = [v.strip() for v in table.cellWidget(row,6).toPlainText().splitlines() if v.strip()]
        for attr,w in self.lookups.items():
            setattr(candidate,attr,[v.strip() for v in w.toPlainText().splitlines() if v.strip()])

    def add_field(self, entity):
        d = FieldDialog(entity,self)
        if d.exec() != QDialog.DialogCode.Accepted: return
        candidate = copy.deepcopy(self.settings)
        self._read_tables(candidate)
        fields = candidate.customer_fields if entity == 'customers' else candidate.job_fields
        fields.append(d.definition())
        try: candidate.validate()
        except ValueError as exc: QMessageBox.warning(self,'Invalid field',str(exc)); return
        self.settings = candidate
        self._fill(entity)

    def save(self):
        candidate = copy.deepcopy(self.settings)
        try:
            self._read_tables(candidate)
            candidate.validate()
            self.store.save(candidate)
        except Exception as exc:
            QMessageBox.warning(self,'Configuration could not be saved',str(exc)); return
        self.settings = candidate
        self.settings_saved.emit(candidate)
        QMessageBox.information(self,'Configuration saved','New forms and list columns now use this configuration. Existing job values are preserved.')
