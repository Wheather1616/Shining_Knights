"""Customer directory and a bounded profile above independently scrolling jobs."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QFrame
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QScrollArea, QSizePolicy, QSplitter,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from ..config import CORE_FIELDS


def label(text='', name='CustomerValue'):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    widget.setMinimumWidth(0)
    widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


class DirectoryDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        lines = str(index.data(Qt.ItemDataRole.DisplayRole)).split('\n')
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = option.rect.adjusted(1, 4, -1, -4)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(option.rect, QColor('#fffdfb'))
        painter.setPen(QColor('#c6e5eb' if selected else '#e5dad3'))
        painter.setBrush(QColor('#eef8fa' if selected else '#f8f3ef' if hovered else '#fffdfb'))
        painter.drawRoundedRect(rect, 10, 10)
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QColor('#258ea6'))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 9, 9)
        text_rect = rect.adjusted(12, 10, -12, -10)
        y = text_rect.top()
        for i, text in enumerate(lines):
            font = QFont(option.font)
            if i == 0:
                font.setWeight(QFont.Weight.DemiBold)
                font.setPixelSize(15)
            metrics = QFontMetrics(font)
            painter.setFont(font)
            painter.setPen(QColor('#302a30' if i == 0 else '#6b6267'))
            painter.drawText(text_rect.left(), y + metrics.ascent(), metrics.elidedText(text, Qt.TextElideMode.ElideRight, text_rect.width()))
            y += metrics.height() + 2
        painter.restore()


class HistoryDelegate(QStyledItemDelegate):
    COLOURS = {'Scheduled': ('#eef8fa', '#176478'), 'In progress': ('#faf2fb', '#793572'),
               'Completed': ('#eef9f1', '#2d7650'), 'Cancelled': ('#f8f3ef', '#6b6267'),
               'Paid': ('#eef9f1', '#2d7650'), 'Unpaid': ('#fff2ef', '#8d332c'),
               'Invoiced': ('#eef8fa', '#176478'), 'Part-paid': ('#faf2fb', '#793572')}

    def paint(self, painter, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if index.column() not in self.parent().badge_columns or text not in self.COLOURS:
            return super().paint(painter, option, index)
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        styled.text = ''
        styled.widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, styled.widget)
        background, foreground = self.COLOURS[text]
        rect = option.rect.adjusted(8, 11, -8, -11)
        rect.setWidth(min(rect.width(), option.fontMetrics.horizontalAdvance(text) + 16))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(rect, 7, 7)
        painter.setPen(QColor(foreground))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class CustomerPage(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setObjectName('CustomersPage')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(16)
        heading = QHBoxLayout()
        heading.addWidget(label('Customers', 'CustomersTitle'), 1)
        heading.addWidget(owner._button('Export CSV', owner.export_customers))
        heading.addWidget(owner._button('Add customer', owner.add_customer))
        layout.addLayout(heading)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName('CustomerSplitter')
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(12)
        directory = QWidget()
        directory.setObjectName('CustomerDirectory')
        directory.setMinimumWidth(230)
        directory.setMaximumWidth(420)
        left = QVBoxLayout(directory)
        left.setContentsMargins(18, 18, 18, 18)
        left.setSpacing(10)
        left.addWidget(label('Find a customer', 'CustomerCaption'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Name, suburb, phone…')
        self.search.setAccessibleName('Search customers')
        self.search.textChanged.connect(owner.refresh_customers)
        left.addWidget(self.search)
        self.inactive = QCheckBox('Include inactive')
        self.inactive.toggled.connect(owner.refresh_customers)
        left.addWidget(self.inactive)
        self.count = label('0 customers', 'CustomerCaption')
        directory_heading = QHBoxLayout()
        directory_heading.addWidget(self.count, 1)
        self.details_button = owner._button('More detail', self.toggle_directory_details)
        self.details_button.setProperty('role', 'link')
        directory_heading.addWidget(self.details_button)
        self.show_directory_details = False
        left.addLayout(directory_heading)
        self.directory_empty = label('No customers yet. Use Add customer to get started.', 'CustomerEmpty')
        left.addWidget(self.directory_empty)
        self.customer_table = QTableWidget(0, 1)
        self.customer_table.setObjectName('CustomerDirectoryTable')
        owner._setup_table(self.customer_table)
        self.customer_table.setItemDelegate(DirectoryDelegate(self.customer_table))
        self.customer_table.horizontalHeader().hide()
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.customer_table.setShowGrid(False)
        self.customer_table.setAlternatingRowColors(False)
        self.customer_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.customer_table.setAccessibleName('Customer directory')
        self.customer_table.itemSelectionChanged.connect(owner.show_selected_customer)
        self.customer_table.cellDoubleClicked.connect(lambda *_: owner.edit_customer())
        left.addWidget(self.customer_table, 1)
        self.splitter.addWidget(directory)

        self.stack = QStackedWidget()
        self.stack.setMinimumWidth(0)
        self.empty = label('Select a customer to see their details and linked jobs.', 'CustomerEmpty')
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.empty)
        self.workspace = QWidget()
        right = QVBoxLayout(self.workspace)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        self.overview_scroll = QScrollArea()
        self.overview_scroll.setObjectName('CustomerOverviewScroll')
        self.overview_scroll.setWidgetResizable(True)
        self.overview_scroll.setMinimumHeight(226)
        self.overview_scroll.setMaximumHeight(260)
        self.overview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        overview = QWidget()
        overview.setObjectName('CustomerProfileCard')
        card = QVBoxLayout(overview)
        card.setContentsMargins(18, 16, 18, 16)
        card.setSpacing(14)
        title = QHBoxLayout()
        self.name = label('', 'CustomerName')
        self.status = label('', 'CustomerStatus')
        self.status.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.status.setWordWrap(False)
        self.edit_customer_button = owner._button('Edit customer', owner.edit_customer)
        title.addWidget(self.name, 1)
        title.addWidget(self.status)
        title.addWidget(self.edit_customer_button)
        card.addLayout(title)
        contact = QGridLayout()
        contact.setHorizontalSpacing(24)
        contact.setVerticalSpacing(4)
        contact.addWidget(label('Service address', 'CustomerCaption'), 0, 0)
        contact.addWidget(label('Contact', 'CustomerCaption'), 0, 1)
        self.profile = label()  # Address, kept accessible independently of the name.
        self.contact = label()
        contact.addWidget(self.profile, 1, 0)
        contact.addWidget(self.contact, 1, 1)
        contact.setColumnStretch(0, 1)
        contact.setColumnStretch(1, 1)
        card.addLayout(contact)
        divider = QFrame()
        self.profile_divider = divider
        divider.setObjectName('CustomerDivider')
        divider.setFixedHeight(1)
        card.addWidget(divider)
        self.summary_panel = QWidget()
        summary = QGridLayout(self.summary_panel)
        summary.setContentsMargins(0, 0, 0, 0)
        summary.setHorizontalSpacing(20)
        self.summary = {}
        for column, (key, caption) in enumerate((('jobs_completed', 'Completed jobs'),
                ('last_job', 'Last completed'), ('next_due', 'Next due'))):
            summary.addWidget(label(caption, 'CustomerCaption'), 0, column)
            value = label('', 'CustomerMetric')
            summary.addWidget(value, 1, column)
            summary.setColumnStretch(column, 1)
            self.summary[key] = value
        card.addWidget(self.summary_panel)
        self.overview_scroll.setWidget(overview)
        right.addWidget(self.overview_scroll)

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setObjectName('CustomerDetailTabs')
        self.detail_tabs.setMinimumWidth(0)
        jobs = QWidget()
        jobs.setObjectName('CustomerDetailPage')
        job_layout = QVBoxLayout(jobs)
        job_layout.setContentsMargins(12, 10, 12, 10)
        job_layout.setSpacing(8)
        job_heading = QHBoxLayout()
        captions = QHBoxLayout()
        captions.setSpacing(12)
        self.job_history_title = label('Job history', 'SectionTitle')
        self.job_history_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.job_history_title.setWordWrap(False)
        captions.addWidget(self.job_history_title)
        self.job_count = label('0 linked jobs', 'CustomerCaption')
        self.job_count.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.job_count.setWordWrap(False)
        captions.addWidget(self.job_count)
        captions.addStretch()
        job_heading.addLayout(captions, 1)
        self.edit_job_button = owner._button('Edit selected job', self.edit_selected_job)
        job_heading.addWidget(self.edit_job_button)
        self.add_job_button = owner._button('Add job', lambda: owner.add_job(owner.selected_customer))
        job_heading.addWidget(self.add_job_button)
        job_layout.addLayout(job_heading)
        self.history_empty = label('No jobs yet. Add a job for this customer.', 'CustomerEmpty')
        job_layout.addWidget(self.history_empty)
        self.history = QTableWidget()
        self.history.setObjectName('CustomerJobHistory')
        owner._setup_table(self.history)
        self.history.badge_columns = set()
        self.history.setItemDelegate(HistoryDelegate(self.history))
        self.history.setAlternatingRowColors(False)
        self.history.verticalHeader().setDefaultSectionSize(48)
        self.history.setMinimumHeight(138)
        self.history.setMinimumWidth(0)
        self.history.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.history.setShowGrid(False)
        self.history.cellDoubleClicked.connect(owner.edit_history_job)
        self.history.itemSelectionChanged.connect(self.update_job_action)
        job_layout.addWidget(self.history, 1)
        self.detail_tabs.addTab(jobs, 'Jobs')
        from .customer_services import CustomerServices
        self.services = CustomerServices(owner)
        self.detail_tabs.addTab(self.services, 'Services')

        service = QWidget()
        service.setObjectName('CustomerDetailPage')
        service_layout = QVBoxLayout(service)
        service_layout.setContentsMargins(16, 14, 16, 14)
        service_scroll = QScrollArea()
        service_scroll.setObjectName('CustomerServiceScroll')
        service_scroll.setWidgetResizable(True)
        self.service_content = QWidget()
        self.service_form = QFormLayout(self.service_content)
        self.service_form.setContentsMargins(0, 0, 12, 12)
        self.service_form.setSpacing(14)
        self.service_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.service_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        service_scroll.setWidget(self.service_content)
        service_layout.addWidget(service_scroll, 1)
        activation = QHBoxLayout()
        activation.addStretch()
        self.activation_button = owner._button('Deactivate customer', owner.toggle_customer)
        activation.addWidget(self.activation_button)
        service_layout.addLayout(activation)
        self.detail_tabs.addTab(service, 'Service setup')
        self.notes = QTextEdit()
        self.notes.setObjectName('CustomerNotes')
        self.notes.setReadOnly(True)
        self.notes.setAccessibleName('Customer notes; edit through Edit customer')
        self.detail_tabs.addTab(self.notes, 'Notes')
        self.detail_tabs.currentChanged.connect(self._detail_tab_changed)
        details_card = QWidget()
        details_card.setObjectName('CustomerDetailsCard')
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(12, 8, 12, 6)
        details_layout.addWidget(self.detail_tabs)
        right.addWidget(details_card, 1)
        self.stack.addWidget(self.workspace)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([290, 900])
        layout.addWidget(self.splitter, 1)
        self.clear_customer()

    def _detail_tab_changed(self, index):
        # Give services room on a small screen while keeping the customer's
        # name, contact and address visible. Job metrics return on other tabs.
        compact = self.detail_tabs.widget(index) is self.services
        self.summary_panel.setVisible(not compact)
        self.profile_divider.setVisible(not compact)
        self.overview_scroll.setMinimumHeight(164 if compact else 226)
        self.overview_scroll.setMaximumHeight(190 if compact else 260)

    def set_customers(self, records, summaries, selected):
        table = self.customer_table
        table.blockSignals(True)
        table.clearSelection()
        table.setRowCount(len(records))
        name_field = next(f for f in self.owner.settings.customer_fields if f.key == 'name')
        table.setHorizontalHeaderLabels([name_field.label])
        selected_row = None
        for row, customer in enumerate(records):
            place = customer['suburb'] or 'Address not set'
            lines = [customer['name'] + (' · Inactive' if not customer['active'] else ''),
                     f"{place} · {self.owner.frequency_text(customer)}",
                     'Next due: ' + self.date_text(summaries[customer['id']]['next_due'])]
            browse_fields = self.owner._columns('customers')
            for field in browse_fields:
                if self.show_directory_details and field.key not in ('name', 'first_name', 'last_name', 'suburb'):
                    value = self.owner._field_value(customer, field, 'customers')
                    if value: lines.append(f'{field.label}: {value}')
            item = QTableWidgetItem('\n'.join(lines))
            item.setData(Qt.ItemDataRole.UserRole, customer['id'])
            item.setToolTip('\n'.join(f'{f.label}: {self.owner._field_value(customer, f, "customers")}'
                                    for f in browse_fields))
            table.setItem(row, 0, item)
            table.setRowHeight(row, (table.fontMetrics().height() + 2) * len(lines) + 30)
            if customer['id'] == selected: selected_row = row
        if selected_row is not None: table.selectRow(selected_row)
        table.blockSignals(False)
        count = len(records)
        self.count.setText(f'{count} customer' + ('' if count == 1 else 's'))
        self.directory_empty.setVisible(not records)
        searching = bool(self.search.text().strip())
        self.directory_empty.setText('No matching customers. Try another search or include inactive customers.'
                                     if searching or self.inactive.isChecked() else
                                     'No active customers. Add a customer or include inactive customers.')

    def toggle_directory_details(self):
        self.show_directory_details = not self.show_directory_details
        self.details_button.setText('Compact list' if self.show_directory_details else 'More detail')
        self.owner.refresh_customers()

    def date_text(self, value):
        from .main_window import display
        return display(value, 'date') or 'Not set'

    def clear_customer(self):
        self.stack.setCurrentIndex(0)
        self.services.set_customer(None)
        self.profile.setText('Select a customer to see their service history.')
        self.name.clear()
        self.contact.clear()
        self.status.clear()
        for value in self.summary.values(): value.clear()
        self.job_count.setText('0 linked jobs')
        self.notes.clear()
        while self.service_form.rowCount(): self.service_form.removeRow(0)
        self.history.clearSelection()
        self.history.setRowCount(0)
        for button in (self.edit_customer_button, self.add_job_button,
                       self.activation_button, self.edit_job_button): button.setEnabled(False)

    def show_customer(self, customer, summary, jobs):
        from .main_window import display
        self.stack.setCurrentIndex(1)
        self.services.set_customer(customer['id'])
        self.name.setText(customer['name'])
        self.name.setToolTip(customer['name'])
        self.status.setText('Active' if customer['active'] else 'Inactive')
        self.status.setProperty('active', customer['active'])
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        enabled = {field.key for field in self.owner.settings.customer_fields if field.enabled}
        street = ', '.join(customer[key] for key in ('address_line_1', 'address_line_2') if key in enabled and customer[key])
        locality = ' '.join(customer[key] for key in ('suburb', 'state', 'postcode') if key in enabled and customer[key])
        self.profile.setText('\n'.join(part for part in (street, locality) if part) or 'Address not set')
        self.contact.setText('\n'.join(customer[key] for key in ('phone', 'email') if key in enabled and customer[key]) or 'Contact not set')
        self.summary['jobs_completed'].setText(str(summary['jobs_completed']))
        self.summary['last_job'].setText(self.date_text(summary['last_job']))
        self.summary['next_due'].setText(self.date_text(summary['next_due']))
        self.notes.setPlainText(customer['notes'] if 'notes' in enabled else '')
        self.notes.setPlaceholderText('No customer notes.' if 'notes' in enabled else 'Customer notes are disabled in Field settings.')
        while self.service_form.rowCount(): self.service_form.removeRow(0)
        for caption, value in (('Frequency', self.owner.frequency_text(customer)),
                               ('Next scheduled', self.date_text(summary['next_scheduled']))):
            self.add_service_row(caption, value)
        # Include every enabled field outside the compact overview and Notes.
        overview_keys = {'name', 'first_name', 'last_name', 'phone', 'email', 'address_line_1', 'address_line_2',
                         'suburb', 'state', 'postcode', 'frequency_value', 'frequency_unit', 'notes', 'active'}
        for field in self.owner.settings.customer_fields:
            if field.enabled and field.key not in overview_keys:
                value = self.owner._field_value(customer, field, 'customers')
                self.add_service_row(field.label, value or 'Not set')
        self.activation_button.setText('Deactivate customer' if customer['active'] else 'Activate customer')
        self.edit_customer_button.setEnabled(True)
        self.activation_button.setEnabled(True)
        self.add_job_button.setEnabled(customer['active'])
        self.job_count.setText(f'{len(jobs)} linked job' + ('' if len(jobs) == 1 else 's'))
        self.owner._fill_table(self.history, jobs, 'jobs')
        self.history.badge_columns = {index for index, field in enumerate(self.owner._columns('jobs'))
                                      if field.key in ('status', 'payment_status')}
        self.history.clearSelection()
        self.history_empty.setVisible(not jobs)
        self.update_job_action()

    def update_job_action(self):
        self.edit_job_button.setEnabled(bool(self.history.selectedItems()))

    def add_service_row(self, caption, value):
        caption_widget = label(caption, 'CustomerCaption')
        # QFormLayout needs a real label size hint to reserve its label column.
        caption_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.service_form.addRow(caption_widget, label(value))

    def edit_selected_job(self):
        items = self.history.selectedItems()
        if items: self.owner._edit_job_id(items[0].data(Qt.ItemDataRole.UserRole))
