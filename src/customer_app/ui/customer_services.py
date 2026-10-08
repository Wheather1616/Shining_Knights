"""Named customer services and a plain-language reusable service editor."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QVBoxLayout, QWidget)

from ..models import ServiceRecord
from .form_controls import ChoiceGrid, WorkTypeGrid, NumericInput


class ServiceDialog(QDialog):
    def __init__(self, db, settings, customer_id, service_id=None, parent=None):
        super().__init__(parent)
        self.db, self.customer_id, self.service_id = db, customer_id, service_id
        self.saved_id = None
        self.setWindowTitle('Edit service' if service_id else 'Add service')
        self.resize(650, 620)
        self.setMinimumSize(520, 480)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        title = QLabel(self.windowTitle()); title.setObjectName('PageTitle'); outer.addWidget(title)
        helper = QLabel('Save a service for this customer. You can adjust its details for each job.')
        helper.setObjectName('FormHelper'); helper.setWordWrap(True); outer.addWidget(helper)
        values = db.get_service(service_id) if service_id else {}
        content = QWidget(); layout = QFormLayout(content)
        layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(14)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.name = QLineEdit(values.get('name', '')); self.name.setMaxLength(120)
        self.name.setPlaceholderText('e.g. Indoor windows or Whole house')
        self.name.setAccessibleName('Service name')
        layout.addRow('Service name *', self.name)
        self.job_type = WorkTypeGrid(settings.job_type_options,values.get('job_type',[]),values.get('job_type_sides',{}),
            empty_text='No job types available. Add them in Settings.')
        self.job_type.setAccessibleName('Nature of job')
        layout.addRow('Nature of job', self.job_type)
        scope_hint = QLabel('Tick each type of work, then choose Inside, Outside or Both. Previous choices can stay unset until confirmed.')
        scope_hint.setWordWrap(True); scope_hint.setObjectName('FormHelper')
        layout.addRow('', scope_hint)
        pair = QWidget(); charges = QHBoxLayout(pair); charges.setContentsMargins(0,0,0,0)
        self.fee = NumericInput(r'[0-9]{0,9}(\.[0-9]{0,2})?', values.get('fee'))
        self.hours = NumericInput(r'[0-9]{0,4}(\.[0-9]{0,2})?', values.get('hours'))
        for caption, widget in [('Total fee (AUD)', self.fee), ('Number of hours', self.hours)]:
            column = QVBoxLayout(); column.addWidget(QLabel(caption)); column.addWidget(widget); charges.addLayout(column)
            widget.setAccessibleName(caption)
        layout.addRow('Service charge', pair)
        hint = QLabel('Hours are an estimate. They do not multiply the total fee.'); hint.setWordWrap(True); hint.setObjectName('FormHelper')
        layout.addRow('', hint)
        self.equipment = ChoiceGrid(settings.equipment_options, values.get('equipment', []))
        layout.addRow('Equipment required', self.equipment)
        self.notes = QPlainTextEdit(values.get('notes','')); self.notes.setMaximumHeight(100)
        self.notes.setAccessibleName('Service notes'); layout.addRow('Service notes', self.notes)
        scroll = QScrollArea(); scroll.setObjectName('RecordScroll'); scroll.setWidgetResizable(True); scroll.setWidget(content); outer.addWidget(scroll, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty('role', 'primary')
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject); outer.addWidget(buttons)

    def save(self):
        try:
            record = ServiceRecord(self.customer_id, name=self.name.text().strip(),
                job_type=self.job_type.selected_values(), job_type_sides=self.job_type.selected_sides(), equipment=self.equipment.selected_values(),
                fee=self.fee.text().strip(), hours=self.hours.text().strip(), notes=self.notes.toPlainText().strip())
            if self.service_id:
                self.db.update_service(self.service_id, record); self.saved_id = self.service_id
            else:
                self.saved_id = self.db.create_service(record)
        except Exception as exc:
            QMessageBox.warning(self, 'Service could not be saved', str(exc)); return
        self.accept()


class CustomerServices(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner; self.customer_id = None; self.records = []
        self.setObjectName('CustomerDetailPage')
        outer = QVBoxLayout(self); outer.setContentsMargins(12,10,12,10); outer.setSpacing(8)
        heading = QHBoxLayout()
        title = QLabel('Services'); title.setObjectName('SectionTitle'); heading.addWidget(title,1)
        self.archived = QCheckBox('Show archived'); self.archived.setAccessibleName('Show archived services')
        self.archived.setSizePolicy(QSizePolicy.Policy.Maximum,QSizePolicy.Policy.Preferred)
        self.archived.toggled.connect(self.refresh); heading.addWidget(self.archived)
        self.add_button = owner._button('Add service', self.add_service); heading.addWidget(self.add_button)
        outer.addLayout(heading)
        hint = QLabel('Each service has its own charge, hours and equipment.')
        hint.setWordWrap(True); hint.setObjectName('FormHelper'); outer.addWidget(hint)
        self.message = hint
        self.table = QTableWidget(0,4); self.table.setObjectName('CustomerJobHistory')
        self.table.setHorizontalHeaderLabels(['Service', 'Fee (AUD)', 'Hours', 'Availability'])
        owner._setup_table(self.table); self.table.setShowGrid(False); self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1,2,3): self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(96)
        self.table.verticalHeader().setDefaultSectionSize(48); self.table.setAccessibleName('Services for the selected customer')
        self.table.itemSelectionChanged.connect(self.update_actions); self.table.cellDoubleClicked.connect(lambda *_:self.edit_service())
        outer.addWidget(self.table,1)
        actions = QHBoxLayout(); actions.setSpacing(8)
        self.edit_button = owner._button('Edit service', self.edit_service)
        self.usual_button = owner._button('Make usual', self.make_usual)
        self.archive_button = owner._button('Archive service', self.archive_service)
        for button in (self.edit_button,self.usual_button,self.archive_button):actions.addWidget(button)
        actions.addStretch(); outer.addLayout(actions)
        self.set_customer(None)

    def selected_service(self):
        items = self.table.selectedItems()
        sid = items[0].data(Qt.ItemDataRole.UserRole) if items else None
        return next((r for r in self.records if r['id']==sid),None)

    def set_customer(self, customer_id):
        if self.customer_id != customer_id: self.message.setText('Each service has its own charge, hours and equipment.')
        self.customer_id = customer_id; self.refresh()

    def refresh(self, *_):
        selected = self.selected_service(); sid = selected['id'] if selected else None
        self.records = self.owner.db.list_services(self.customer_id,include_archived=self.archived.isChecked()) if self.customer_id else []
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.setRowCount(len(self.records))
        for row, service in enumerate(self.records):
            values = [service['name']+(' · Usual' if service['is_default'] else ''),
                '$'+service['fee'] if service['fee'] is not None else 'Not set', service['hours'] if service['hours'] is not None else 'Not set',
                'Available' if service['active'] else 'Archived']
            for col,value in enumerate(values):
                item = QTableWidgetItem(value); item.setData(Qt.ItemDataRole.UserRole,service['id']); item.setToolTip(value); self.table.setItem(row,col,item)
            if service['id']==sid: self.table.selectRow(row)
        self.table.blockSignals(False)
        self.add_button.setEnabled(bool(self.customer_id)); self.update_actions()

    def update_actions(self):
        service = self.selected_service()
        self.edit_button.setEnabled(bool(service))
        self.usual_button.setEnabled(bool(service and service['active'] and not service['is_default']))
        self.archive_button.setEnabled(bool(service and not service['is_default']))
        self.archive_button.setText('Archive service' if not service or service['active'] else 'Restore service')
        self.archive_button.setToolTip('Choose another usual service first.' if service and service['is_default'] else 'Existing jobs keep their saved details.')

    def edit_service(self):
        service = self.selected_service()
        if service: self._dialog(service['id'])

    def add_service(self):
        if self.customer_id: self._dialog()

    def _dialog(self, service_id=None):
        dialog = ServiceDialog(self.owner.db,self.owner.settings,self.customer_id,service_id,self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.owner.refresh_all()
            self.message.setText('Service saved. Job history is unchanged.')
            for row,record in enumerate(self.records):
                if record['id']==dialog.saved_id:self.table.selectRow(row)

    def make_usual(self):
        service = self.selected_service()
        if service:self._perform(lambda:self.owner.db.set_usual_service(service['id']), 'Usual service updated for new jobs.')

    def archive_service(self):
        service = self.selected_service()
        if service:self._perform(lambda:self.owner.db.set_service_active(service['id'],not service['active']), 'Service archived. Existing jobs are unchanged.' if service['active'] else 'Service restored.')

    def _perform(self, action, message):
        try:action()
        except Exception as exc:QMessageBox.warning(self,'Service could not be updated',str(exc)); return
        self.owner.refresh_all(); self.message.setText(message)
