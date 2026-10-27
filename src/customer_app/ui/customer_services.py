"""Named customer services: compact editor, service list and read-only preview."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QVBoxLayout,
    QWidget, QGridLayout, QLayout)

from ..models import ServiceRecord
from .form_controls import ChoiceGrid, WorkTypeGrid, GroupedWorkTypeGrid, NumericInput
from .form_sections import SectionCard, SelectionDisclosure


class ServiceDialog(QDialog):
    def __init__(self, db, settings, customer_id, service_id=None, parent=None):
        super().__init__(parent)
        self.db, self.customer_id, self.service_id = db, customer_id, service_id
        self.saved_id = None
        self.setWindowTitle('Edit service' if service_id else 'Add service')
        self.setObjectName('RecordDialog')
        self.resize(740, 770)
        self.setMinimumSize(570, 540)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)
        heading = QLabel(self.windowTitle())
        heading.setObjectName('PageTitle')
        outer.addWidget(heading)
        helper = QLabel('Save a service for this customer. Each job can have its own adjustments.')
        helper.setObjectName('FormHelper')
        helper.setWordWrap(True)
        outer.addWidget(helper)
        values = db.get_service(service_id) if service_id else {}
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(5, 6, 5, 12)
        layout.setSpacing(12)

        details = SectionCard('Service details', 'Define what work this service includes.', '✦')
        self.name = QLineEdit(values.get('name', ''))
        self.name.setMaxLength(120)
        self.name.setPlaceholderText('e.g. Indoor windows or Whole house')
        self.name.setAccessibleName('Service name')
        details.add_field('Service name *', self.name)
        self.job_type = GroupedWorkTypeGrid(settings.job_type_options, values.get('job_type', []),
                                     values.get('job_type_sides', {}),
                                     empty_text='No job types available. Add them in Settings.')
        self.job_type.setAccessibleName('Nature of job')
        details.add_widget(SelectionDisclosure('Nature of job', self.job_type,
                                               expanded=len(settings.job_type_options) <= 6))
        details.add_hint('Choose Inside, Outside or Both for the relevant selected items.')
        layout.addWidget(details)

        equipment = SectionCard('Equipment required', 'Tools needed to complete this service.',
                                '⚙', expanded=False, collapsible=True)
        self.equipment = ChoiceGrid(settings.equipment_options, values.get('equipment', []))
        equipment.add_widget(self.equipment)
        layout.addWidget(equipment)

        pricing = SectionCard('Pricing & availability', 'Default amounts for this service.', '$')
        self.fee = NumericInput(r'[0-9]{0,9}(\.[0-9]{0,2})?', values.get('fee'))
        self.hours = NumericInput(r'[0-9]{0,4}(\.[0-9]{0,2})?', values.get('hours'))
        self.fee.setAccessibleName('Total fee (AUD)')
        self.hours.setAccessibleName('Number of hours')
        self.hours.setPlaceholderText('e.g. 1.5')
        pricing.add_pair(('Total fee (AUD)', self.fee), ('Number of hours', self.hours))
        pricing.add_hint('Hours are an estimate and do not multiply the fee. Archive or restore services from the Services tab.')
        layout.addWidget(pricing)

        notes_section = SectionCard('Service notes', 'Reference details specific to this service.',
                                    '✎', expanded=bool(values.get('notes')), collapsible=True)
        self.notes = QPlainTextEdit(values.get('notes', ''))
        self.notes.setMinimumHeight(95)
        self.notes.setMaximumHeight(125)
        self.notes.setPlaceholderText('Equipment instructions, access requirements, special requests…')
        self.notes.setAccessibleName('Service notes')
        notes_section.add_widget(self.notes)
        layout.addWidget(notes_section)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName('RecordScroll')
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty('role', 'primary')
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

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
    """A list for selection with a useful service-details preview below."""
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.customer_id = None
        self.records = []
        self.setObjectName('CustomerDetailPage')
        # Let the full Services tab scroll. Otherwise the fixed-height table
        # squeezes the service preview/chips into unreadable slivers.
        host_layout = QVBoxLayout(self)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)
        self.page_scroll = QScrollArea(self)
        self.page_scroll.setObjectName('CustomerServicesScroll')
        self.page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName('CustomerServicesScrollContent')
        outer = QVBoxLayout(self.scroll_content)
        outer.setContentsMargins(12, 10, 12, 20)
        outer.setSpacing(12)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.page_scroll.setWidget(self.scroll_content)
        host_layout.addWidget(self.page_scroll, 1)
        heading = QHBoxLayout()
        title = QLabel('Customer services')
        title.setObjectName('CustomerJobHeading')
        heading.addWidget(title, 1)
        self.archived = QCheckBox('Show archived')
        self.archived.setAccessibleName('Show archived services')
        self.archived.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.archived.toggled.connect(self.refresh)
        heading.addWidget(self.archived)
        self.add_button = owner._button('+  Add service', self.add_service)
        self.add_button.setProperty('role', 'primary')
        self.add_button.setObjectName('CustomerAddJobButton')
        heading.addWidget(self.add_button)
        outer.addLayout(heading)
        hint = QLabel('Choose a service to view its defaults, equipment and saved notes.')
        hint.setWordWrap(True)
        hint.setObjectName('FormHelper')
        outer.addWidget(hint)
        self.message = hint
        self.table = QTableWidget(0, 4)
        self.table.setObjectName('CustomerServicesTable')
        self.table.setHorizontalHeaderLabels(['Service', 'Fee (AUD)', 'Hours', 'Availability'])
        owner._setup_table(self.table)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(95)
        self.table.setMaximumHeight(300)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setAccessibleName('Services for the selected customer')
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_service())
        outer.addWidget(self.table)

        preview = QFrame()
        self.preview = preview
        preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        preview.setObjectName('CustomerServicePreview')
        preview_box = QVBoxLayout(preview)
        preview_box.setContentsMargins(17, 16, 17, 16)
        preview_box.setSpacing(13)
        preview_box.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        title_row = QHBoxLayout()
        self.preview_title = QLabel('Select a service')
        self.preview_title.setObjectName('ServicePreviewTitle')
        self.preview_title.setMinimumHeight(29)
        title_row.addWidget(self.preview_title, 1)
        self.preview_badge = QLabel('')
        self.preview_badge.setObjectName('ServicePreviewBadge')
        self.preview_badge.setMinimumHeight(24)
        title_row.addWidget(self.preview_badge)
        preview_box.addLayout(title_row)
        self.preview_scope_label = QLabel('SERVICE SCOPE')
        self.preview_scope_label.setObjectName('ServicePreviewCaption')
        preview_box.addWidget(self.preview_scope_label)
        self.preview_scope_host = QWidget()
        self.preview_scope_host.setObjectName('ServicePreviewChips')
        self.preview_scope_grid = QGridLayout(self.preview_scope_host)
        self.preview_scope_grid.setContentsMargins(0, 0, 0, 0)
        self.preview_scope_grid.setHorizontalSpacing(7)
        self.preview_scope_grid.setVerticalSpacing(7)
        self.preview_scope_grid.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        preview_box.addWidget(self.preview_scope_host)
        self.preview_equipment_label = QLabel('EQUIPMENT')
        self.preview_equipment_label.setObjectName('ServicePreviewCaption')
        preview_box.addWidget(self.preview_equipment_label)
        self.preview_equipment_host = QWidget()
        self.preview_equipment_host.setObjectName('ServicePreviewChips')
        self.preview_equipment_grid = QGridLayout(self.preview_equipment_host)
        self.preview_equipment_grid.setContentsMargins(0, 0, 0, 0)
        self.preview_equipment_grid.setHorizontalSpacing(7)
        self.preview_equipment_grid.setVerticalSpacing(7)
        self.preview_equipment_grid.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        preview_box.addWidget(self.preview_equipment_host)
        self.preview_notes_frame = QFrame()
        self.preview_notes_frame.setObjectName('ServicePreviewNotesCard')
        notes_box = QVBoxLayout(self.preview_notes_frame)
        notes_box.setContentsMargins(13, 10, 13, 10)
        notes_box.setSpacing(6)
        notes_box.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        notes_heading = QLabel('SERVICE NOTES')
        notes_heading.setObjectName('ServicePreviewCaption')
        notes_box.addWidget(notes_heading)
        self.preview_notes = QLabel('')
        self.preview_notes.setObjectName('ServicePreviewNotes')
        self.preview_notes.setWordWrap(True)
        self.preview_notes.setTextFormat(Qt.TextFormat.PlainText)
        notes_box.addWidget(self.preview_notes)
        preview_box.addWidget(self.preview_notes_frame)
        actions = QHBoxLayout()
        actions.setSpacing(9)
        self.edit_button = owner._button('Edit service', self.edit_service)
        self.usual_button = owner._button('Make usual', self.make_usual)
        self.archive_button = owner._button('Archive service', self.archive_service)
        for button in (self.edit_button, self.usual_button, self.archive_button):
            actions.addWidget(button)
        actions.addStretch()
        preview_box.addLayout(actions)
        outer.addWidget(preview)
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
        self.table.setFixedHeight(min(300, 43 + max(1, len(self.records)) * 50))
        if not self.table.selectedItems() and self.records:
            default_row = next((idx for idx, r in enumerate(self.records) if r['is_default']), 0)
            self.table.selectRow(default_row)
        self.add_button.setEnabled(bool(self.customer_id))
        self.update_actions()

    def update_actions(self):
        service = self.selected_service()
        self.edit_button.setEnabled(bool(service))
        self.usual_button.setEnabled(bool(service and service['active'] and not service['is_default']))
        self.archive_button.setEnabled(bool(service and not service['is_default']))
        self.archive_button.setText('Archive service' if not service or service['active'] else 'Restore service')
        self.archive_button.setToolTip('Choose another usual service first.' if service and service['is_default'] else 'Existing jobs keep their saved details.')
        if service:
            self.preview_title.setText(service['name'])
            self.preview_badge.setText('USUAL' if service['is_default'] else
                                       'ARCHIVED' if not service['active'] else 'AVAILABLE')
            self.preview_badge.setProperty('tone', 'coral' if not service['active'] else 'teal')
            self.preview_badge.style().unpolish(self.preview_badge)
            self.preview_badge.style().polish(self.preview_badge)
            types = service.get('job_type') or []
            sides = service.get('job_type_sides') or {}
            scope = [name + (f' · {sides[name].title()}' if sides.get(name) else '') for name in types]
            self._set_chip_grid(self.preview_scope_grid, scope, 'teal')
            self._set_chip_grid(self.preview_equipment_grid, service.get('equipment') or [], 'maroon')
            self.preview_notes.setText(service.get('notes') or 'No service notes saved.')
            self.preview_notes.setProperty('empty', not bool(service.get('notes')))
            self.preview_notes.style().unpolish(self.preview_notes)
            self.preview_notes.style().polish(self.preview_notes)
        else:
            self.preview_title.setText('Select a service')
            self.preview_badge.clear()
            self._set_chip_grid(self.preview_scope_grid, [], 'teal')
            self._set_chip_grid(self.preview_equipment_grid, [], 'maroon')
            self.preview_notes.setText('Choose a service to view its saved notes.')

        # Request a viewport height reflow after the preview's rows change.
        self.preview.updateGeometry()
        self.scroll_content.updateGeometry()

    @staticmethod
    def _set_chip_grid(grid, values, tone):
        """Rebuild read-only scope/equipment chips for the current selection."""
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        values = list(values)
        if not values:
            empty = QLabel('Not configured')
            empty.setObjectName('ServicePreviewEmpty')
            empty.setMinimumHeight(22)
            grid.addWidget(empty, 0, 0)
            grid.invalidate()
            grid.parentWidget().updateGeometry()
            return
        for index, item in enumerate(values):
            chip = QLabel(str(item))
            chip.setObjectName('ServicePreviewChip')
            chip.setProperty('tone', tone)
            chip.setTextFormat(Qt.TextFormat.PlainText)
            chip.setWordWrap(True)
            chip.setMinimumHeight(32)
            chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            grid.addWidget(chip, index // 2, index % 2)
        for column in range(2):
            grid.setColumnStretch(column, 1)
        grid.invalidate()
        grid.parentWidget().updateGeometry()

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
