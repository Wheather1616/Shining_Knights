"""Day-grouped jobs, independent export selection and a linked-job workspace."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from PySide6.QtCore import QDate, QSignalBlocker, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateEdit,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QScrollArea,
    QSizePolicy, QSplitter, QStackedWidget, QStyle, QStyledItemDelegate,
    QStyleOptionViewItem, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..config import JOB_FIELDS, JOB_STATUSES
from .customer_page import label


def fees_text(records):
    total = sum((Decimal(str(job['fee'])) for job in records if job['fee'] is not None), Decimal(0))
    missing = sum(job['fee'] is None for job in records)
    return f'${total:,.2f}' + (f' · {missing} fee unset' if missing else '')


class JobDelegate(QStyledItemDelegate):
    """Readable multiline records and compact, text-labelled status badges."""
    COLOURS = {
        'Scheduled': ('#eef8fa', '#176478'), 'In progress': ('#faf2fb', '#793572'),
        'Completed': ('#eef9f1', '#2d7650'), 'Cancelled': ('#f8f3ef', '#6b6267'),
        'Paid': ('#eef9f1', '#2d7650'), 'Unpaid': ('#fff2ef', '#8d332c'),
        'Invoiced': ('#eef8fa', '#176478'), 'Part-paid': ('#faf2fb', '#793572'),
    }

    def paint(self, painter, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if index.parent().isValid() and index.column() in self.parent().badge_columns and text in self.COLOURS:
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            opt.text = ''
            style = opt.widget.style()
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
            background, foreground = self.COLOURS[text]
            rectangle = option.rect.adjusted(8, 12, -8, -12)
            rectangle.setWidth(min(rectangle.width(), option.fontMetrics.horizontalAdvance(text) + 18))
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(background))
            painter.drawRoundedRect(rectangle, 7, 7)
            painter.setPen(QPen(QColor(foreground)))
            painter.drawText(rectangle, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()
        else:
            super().paint(painter, option, index)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), 50 if index.parent().isValid() else 44)


class JobsPage(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setObjectName('JobsPage')
        self.rows = []
        self.checked_ids = set()
        self.items = {}
        self.groups = {}
        self.grouping = None
        self.focused_id = None
        self._updating = False
        self._selection_cleared = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(label('Jobs', 'PageTitle'))
        titles.addWidget(label('Plan your days and manage service jobs.', 'PageHelper'))
        heading.addLayout(titles, 1)
        self.export_button = owner._button('Export CSV', lambda: None)
        self.export_menu = QMenu(self.export_button)
        self.export_menu.setObjectName('JobsMenu')
        self.export_selected_action = self.export_menu.addAction('Export selected jobs', owner.export_selected_jobs)
        self.export_filtered_action = self.export_menu.addAction('Export all filtered jobs', owner.export_jobs)
        self.export_button.setMenu(self.export_menu)
        heading.addWidget(self.export_button)
        heading.addWidget(owner._button('Add job', owner.add_job))
        layout.addLayout(heading)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search jobs or customers…')
        self.search.setAccessibleName('Search jobs')
        filters.addWidget(self.search, 1)
        self.status_filter = self._combo('Filter jobs by status')
        self.status_filter.addItems(['All', 'Upcoming', 'Overdue', *JOB_STATUSES, 'Trash'])
        self.status_filter.setMinimumWidth(135)
        filters.addWidget(self.status_filter)
        self.date_range = self._combo('Filter jobs by date range')
        for caption, value in [('All dates', 'all'), ('Today', 'today'), ('This week', 'week'),
                ('Next 7 days', 'next7'), ('This month', 'month'), ('Custom range', 'custom')]:
            self.date_range.addItem(caption, value)
        filters.addWidget(self.date_range)
        self.group_by = self._combo('Group jobs')
        for caption, value in [('Scheduled day', 'date'), ('Completed day', 'completed'),
                ('Customer', 'customer'), ('Status', 'status')]:
            self.group_by.addItem(caption, value)
        filters.addWidget(self.group_by)
        layout.addLayout(filters)
        self.custom_dates = QWidget()
        custom = QHBoxLayout(self.custom_dates)
        custom.setContentsMargins(0, 0, 0, 0)
        self.from_date = QDateEdit(QDate.currentDate())
        self.to_date = QDateEdit(QDate.currentDate().addDays(6))
        for widget, caption in ((self.from_date, 'From date'), (self.to_date, 'To date')):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat('dd/MM/yyyy')
            widget.setAccessibleName(caption)
            custom.addWidget(label(caption, 'PageHelper'))
            custom.addWidget(widget)
        custom.addStretch()
        layout.addWidget(self.custom_dates)
        self.custom_dates.hide()
        self.date_error = label('The From date must be on or before the To date.', 'JobsError')
        layout.addWidget(self.date_error)
        self.date_error.hide()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(8)
        self.list_card = QWidget()
        self.list_card.setObjectName('JobsListCard')
        self.list_card.setMinimumWidth(350)
        left = QVBoxLayout(self.list_card)
        left.setContentsMargins(12, 12, 12, 12)
        left.setSpacing(10)
        toolbar = QHBoxLayout()
        self.select_all = QCheckBox('Select all filtered')
        self.select_all.setTristate(True)
        self.select_all.setAccessibleName('Select all filtered jobs for export')
        toolbar.addWidget(self.select_all)
        toolbar.addStretch()
        self.expand_button = owner._button('Expand all', lambda: self.tree.expandAll())
        self.collapse_button = owner._button('Collapse all', lambda: self.tree.collapseAll())
        self.expand_button.setProperty('role', 'link')
        self.collapse_button.setProperty('role', 'link')
        toolbar.addWidget(self.expand_button)
        toolbar.addWidget(self.collapse_button)
        left.addLayout(toolbar)
        self.count = label('0 jobs', 'PageHelper')
        left.addWidget(self.count)
        self.empty = label('No jobs yet. Use Add job to get started.', 'CustomerEmpty')
        left.addWidget(self.empty)
        self.tree = QTreeWidget()
        self.tree.setObjectName('JobsTree')
        self.tree.setAccessibleName('Jobs grouped for viewing and CSV selection')
        self.tree.badge_columns = set()
        self.tree.setItemDelegate(JobDelegate(self.tree))
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setUniformRowHeights(False)
        self.tree.setAlternatingRowColors(False)
        self.tree.setMinimumHeight(150)
        self.tree.header().setStretchLastSection(True)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tree.itemChanged.connect(self._check_changed)
        self.tree.currentItemChanged.connect(self._focus_changed)
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        left.addWidget(self.tree, 1)
        footer = QHBoxLayout()
        self.selection_caption = label('No jobs selected for export.', 'JobsSelection')
        footer.addWidget(self.selection_caption, 1)
        self.clear_button = owner._button('Clear selection', self.clear_export_selection)
        self.clear_button.setProperty('role', 'link')
        footer.addWidget(self.clear_button)
        self.export_selected_button = owner._button('Export selected (0)', owner.export_selected_jobs)
        self.export_selected_button.setProperty('role', 'accent')
        footer.addWidget(self.export_selected_button)
        left.addLayout(footer)
        self.splitter.addWidget(self.list_card)

        self.detail_card = QWidget()
        self.detail_card.setObjectName('JobDetailCard')
        self.detail_card.setMinimumWidth(270)
        right = QVBoxLayout(self.detail_card)
        right.setContentsMargins(14, 14, 14, 14)
        right.setSpacing(12)
        self.detail_stack = QStackedWidget()
        self.detail_empty = label('Select a job to see its details.\n\nUse checkboxes to choose jobs for export.', 'CustomerEmpty')
        self.detail_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_stack.addWidget(self.detail_empty)
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail_scroll.setObjectName('JobDetailScroll')
        content = QWidget()
        content.setObjectName('JobDetailContent')
        details = QVBoxLayout(content)
        details.setContentsMargins(0, 0, 4, 0)
        details.setSpacing(12)
        detail_heading = QHBoxLayout()
        self.job_id = label('', 'PageHelper')
        detail_heading.addWidget(self.job_id, 1)
        self.job_status = label('', 'JobStatus')
        self.job_status.setWordWrap(False)
        self.job_status.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        detail_heading.addWidget(self.job_status)
        details.addLayout(detail_heading)
        self.customer_name = label('', 'JobCustomerName')
        details.addWidget(self.customer_name)
        self.view_customer_button = owner._button('View customer', self.view_customer)
        self.view_customer_button.setProperty('role', 'link')
        details.addWidget(self.view_customer_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.address = label()
        self.contact = label()
        details.addWidget(label('Service address', 'CustomerCaption'))
        details.addWidget(self.address)
        details.addWidget(label('Contact', 'CustomerCaption'))
        details.addWidget(self.contact)
        self.fields = QFormLayout()
        self.fields.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.fields.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.fields.setVerticalSpacing(10)
        details.addLayout(self.fields)
        self.notes_heading = label('Notes', 'CustomerCaption')
        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setAcceptRichText(False)
        self.notes.setMinimumHeight(85)
        self.notes.setMaximumHeight(130)
        details.addWidget(self.notes_heading)
        details.addWidget(self.notes)
        details.addStretch()
        self.detail_scroll.setWidget(content)
        self.detail_stack.addWidget(self.detail_scroll)
        right.addWidget(self.detail_stack, 1)
        actions = QHBoxLayout()
        self.edit_button = owner._button('Edit job', owner.edit_job)
        self.complete_button = owner._button('Mark completed', owner.mark_completed)
        self.restore_button = owner._button('Restore job', owner.restore_job)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.complete_button)
        actions.addWidget(self.restore_button)
        right.addLayout(actions)
        self.more_button = owner._button('More', lambda: None)
        self.more_button.setProperty('role', 'jobMenu')
        self.more_menu = QMenu(self.more_button)
        self.more_menu.setObjectName('JobsMenu')
        self.trash_action = self.more_menu.addAction('Move to Trash', owner.trash_job)
        self.more_button.setMenu(self.more_menu)
        right.addWidget(self.more_button, 0, Qt.AlignmentFlag.AlignRight)
        self.splitter.addWidget(self.detail_card)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([850, 320])
        layout.addWidget(self.splitter, 1)

        self.search.textChanged.connect(self._filters_changed)
        for combo in (self.status_filter, self.date_range, self.group_by):
            combo.currentIndexChanged.connect(self._filters_changed)
        self.from_date.dateChanged.connect(self._filters_changed)
        self.to_date.dateChanged.connect(self._filters_changed)
        self.select_all.checkStateChanged.connect(self._select_all_changed)
        self.clear_detail()
        self._update_export_selection()

    @staticmethod
    def _combo(accessible_name):
        combo = QComboBox()
        combo.setProperty('role', 'jobFilter')
        combo.setAccessibleName(accessible_name)
        combo.setMinimumContentsLength(10)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        return combo

    def _filters_changed(self, *_):
        self.custom_dates.setVisible(self.date_range.currentData() == 'custom')
        self._selection_cleared = bool(self.checked_ids)
        self.checked_ids.clear()
        self.owner.refresh_jobs()
        self.owner.remember_job_filters()

    def preference_filters(self):
        return {'status': self.status_filter.currentText(), 'range': self.date_range.currentData(),
                'group': self.group_by.currentData(), 'from': self.from_date.date().toString('yyyy-MM-dd'),
                'to': self.to_date.date().toString('yyyy-MM-dd')}

    def load_preferences(self):
        settings = self.owner.settings
        filters = settings.jobs_filters if settings.remember_jobs_filters else {}
        widgets = (self.status_filter, self.date_range, self.group_by, self.from_date, self.to_date)
        blockers = [QSignalBlocker(widget) for widget in widgets]
        self.status_filter.setCurrentText(filters.get('status', 'All'))
        self.date_range.setCurrentIndex(max(0, self.date_range.findData(filters.get('range', 'all'))))
        self.group_by.setCurrentIndex(max(0, self.group_by.findData(filters.get('group', settings.jobs_default_group))))
        for widget, key in ((self.from_date, 'from'), (self.to_date, 'to')):
            value = QDate.fromString(filters.get(key, ''), 'yyyy-MM-dd')
            if value.isValid(): widget.setDate(value)
        self.custom_dates.setVisible(self.date_range.currentData() == 'custom')
        del blockers

    def date_field(self):
        return 'completed_date' if self.group_by.currentData() == 'completed' else 'scheduled_date'

    def filter_dates(self, jobs):
        choice = self.date_range.currentData()
        self.date_error.hide()
        if choice == 'all':
            return jobs
        today = date.today()
        if choice == 'custom':
            start, end = self.from_date.date().toPython(), self.to_date.date().toPython()
            if start > end:
                self.date_error.show()
                return []
        elif choice == 'today':
            start = end = today
        elif choice == 'week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif choice == 'next7':
            start, end = today, today + timedelta(days=6)
        else:
            start = today.replace(day=1)
            end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        key = self.date_field()
        return [job for job in jobs if job[key] and start.isoformat() <= job[key] <= end.isoformat()]

    def _bucket(self, job):
        key = self.group_by.currentData()
        if key == 'customer':
            return ('customer', job['customer_id']), job['customer_name']
        if key == 'status':
            return ('status', job['status']), job['status']
        value = job[self.date_field()]
        day = date.fromisoformat(value) if value else None
        caption = (day.strftime('%A') + f', {day.day} ' + day.strftime('%B %Y')) if day else ('No completion date' if key == 'completed' else 'Unscheduled')
        return (key, value), caption

    def set_jobs(self, jobs):
        previous = self.focused_id
        collapsed = {bucket for bucket, item in self.groups.items() if not item.isExpanded()}
        same_grouping = self.grouping == self.group_by.currentData()
        self.grouping = self.group_by.currentData()
        self.rows = jobs
        self.checked_ids.intersection_update(job['id'] for job in jobs)
        self._updating = True
        with QSignalBlocker(self.tree):
            self.tree.clear()
            self.items = {}
            self.groups = {}
            configured = self.owner._columns('jobs')
            # Operational summaries remain readable; configured browse fields follow.
            essential = ['service_name', 'status', 'fee', 'payment_status']
            fields = self.owner.settings.fields_for('jobs')
            columns = [field for key in essential for field in configured if field.key == key]
            columns += [field for field in configured if field.key not in essential]
            defaults = {field.key: field.label for field in JOB_FIELDS}
            concise = {'service_name': 'Service', 'job_type': 'Nature of job', 'status': 'Status', 'fee': 'Fee (AUD)',
                       'payment_status': 'Payment', 'scheduled_date': 'Scheduled',
                       'completed_date': 'Completed', 'payment_type': 'Method'}
            headers = [concise.get(field.key, field.label) if field.label == defaults.get(field.key) else field.label for field in columns]
            self.tree.setColumnCount(1 + len(columns))
            self.tree.setHeaderLabels(['Customer / suburb', *headers])
            self.tree.badge_columns = {index + 1 for index, field in enumerate(columns) if field.key in ('status', 'payment_status')}
            buckets = {}
            for job in jobs:
                bucket, caption = self._bucket(job)
                buckets.setdefault(bucket, (caption, []))[1].append(job)
            for bucket in sorted(buckets, key=lambda b: (b[1] == '', (buckets[b][0] if b[0] == 'customer' else str(b[1])).casefold(), str(b[1]))):
                caption, records = buckets[bucket]
                jobs_caption = f'{len(records)} job' + ('' if len(records) == 1 else 's')
                group = QTreeWidgetItem([f'{caption}   ·   {jobs_caption}   ·   Fees {fees_text(records)}'])
                group.setData(0, Qt.ItemDataRole.UserRole + 1, bucket)
                group.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
                group.setCheckState(0, Qt.CheckState.Unchecked)
                group.setBackground(0, QColor('#f8f3ef'))
                font = self.tree.font()
                font.setBold(True)
                group.setFont(0, font)
                self.tree.addTopLevelItem(group)
                group.setFirstColumnSpanned(True)
                self.groups[bucket] = group
                for job in records:
                    customer = job['customer_name'] + ('\n' + job['suburb'] if job['suburb'] else '')
                    item = QTreeWidgetItem([customer, *[self.owner._field_value(job, field, 'jobs') for field in columns]])
                    item.setData(0, Qt.ItemDataRole.UserRole, job['id'])
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.CheckState.Checked if job['id'] in self.checked_ids else Qt.CheckState.Unchecked)
                    for index in range(item.columnCount()):
                        item.setToolTip(index, item.text(index))
                    for index, field in enumerate(columns, 1):
                        if field.field_type == 'currency':
                            item.setTextAlignment(index, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    group.addChild(item)
                    self.items[job['id']] = item
                group.setExpanded(not (same_grouping and bucket in collapsed))
            self.tree.setColumnWidth(0, 210)
            for index, field in enumerate(columns, 1):
                self.tree.setColumnWidth(index, 155 if field.key == 'job_type' else 110)
            if previous in self.items:
                self.tree.setCurrentItem(self.items[previous])
        self._updating = False
        count = len(jobs)
        group_kind = 'days' if self.grouping in ('date', 'completed') else 'groups'
        self.count.setText(f'{count} job' + ('' if count == 1 else 's') + f' · {len(self.groups)} {group_kind} · Fees {fees_text(jobs)}')
        self.empty.setVisible(not jobs)
        self.empty.setText('No jobs match these filters.' if self.search.text() or self.status_filter.currentText() != 'All' or self.date_range.currentData() != 'all' else 'No jobs yet. Use Add job to get started.')
        self._focus_changed(self.tree.currentItem(), None)
        self._update_export_selection()

    def _check_changed(self, item, column):
        if self._updating or column != 0:
            return
        with QSignalBlocker(self.tree):
            if item.parent() is None:
                state = Qt.CheckState.Checked if item.checkState(0) == Qt.CheckState.Checked else Qt.CheckState.Unchecked
                for index in range(item.childCount()):
                    item.child(index).setCheckState(0, state)
        self.checked_ids = {job_id for job_id, row in self.items.items() if row.checkState(0) == Qt.CheckState.Checked}
        self._selection_cleared = False
        self._update_export_selection()

    def _select_all_changed(self, state):
        checked = state != Qt.CheckState.Unchecked
        with QSignalBlocker(self.tree):
            for item in self.items.values():
                item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.checked_ids = set(self.items) if checked else set()
        self._selection_cleared = False
        self._update_export_selection()

    def clear_export_selection(self):
        self.checked_ids.clear()
        with QSignalBlocker(self.tree):
            for item in self.items.values():
                item.setCheckState(0, Qt.CheckState.Unchecked)
        self._selection_cleared = False
        self._update_export_selection()

    def selected_records(self):
        return [job for job in self.rows if job['id'] in self.checked_ids]

    def _update_export_selection(self):
        with QSignalBlocker(self.tree), QSignalBlocker(self.select_all):
            for group in self.groups.values():
                count = sum(group.child(index).checkState(0) == Qt.CheckState.Checked for index in range(group.childCount()))
                group.setCheckState(0, Qt.CheckState.Unchecked if not count else Qt.CheckState.Checked if count == group.childCount() else Qt.CheckState.PartiallyChecked)
            count = len(self.checked_ids)
            self.select_all.setCheckState(Qt.CheckState.Unchecked if not count else Qt.CheckState.Checked if count == len(self.items) else Qt.CheckState.PartiallyChecked)
        records = self.selected_records()
        days = {job[self.date_field()] for job in records if job[self.date_field()]}
        if records:
            missing_dates = sum(not job[self.date_field()] for job in records)
            caption = f'{count} job' + ('' if count == 1 else 's') + ' selected'
            if days:
                caption += f' · {len(days)} day' + ('' if len(days) == 1 else 's')
            if missing_dates:
                caption += f' · {missing_dates} undated'
            self.selection_caption.setText(caption + f'\nSelected fees: {fees_text(records)}')
        else:
            self.selection_caption.setText('Selection cleared because filters changed.' if self._selection_cleared else 'No jobs selected for export.')
        self.export_selected_button.setText(f'Export selected ({count})')
        self.export_selected_button.setEnabled(bool(count))
        self.clear_button.setEnabled(bool(count))
        self.select_all.setEnabled(bool(self.items))
        self.export_selected_action.setText(f'Export selected jobs ({count})')
        self.export_selected_action.setEnabled(bool(count))
        self.export_filtered_action.setText(f'Export all filtered jobs ({len(self.rows)})')
        self.export_filtered_action.setEnabled(bool(self.rows))
        self.export_button.setEnabled(bool(self.rows))

    def _double_clicked(self, item, _column):
        if item.parent() is not None:
            self.owner.edit_job()

    def _focus_changed(self, item, _previous):
        job_id = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        job = next((row for row in self.rows if row['id'] == job_id), None)
        if job is None:
            self.clear_detail()
            return
        self.focused_id = job_id
        customer = self.owner.db.get_customer(job['customer_id'])
        self.detail_stack.setCurrentWidget(self.detail_scroll)
        self.job_id.setText(f'Selected job #{job_id}')
        self.job_status.setText('In Trash' if job['deleted_at'] else job['status'])
        self.customer_name.setText(job['customer_name'])
        self.address.setText('\n'.join(filter(None, [customer['address_line_1'], customer['address_line_2'],
            ' '.join(filter(None, [customer['suburb'], customer['state'], customer['postcode']]))])) or 'No address recorded')
        self.contact.setText('\n'.join(filter(None, [customer['phone'], customer['email']])) or 'No contact details recorded')
        while self.fields.rowCount():
            self.fields.removeRow(0)
        for field in self.owner.settings.fields_for('jobs'):
            if field.enabled and field.key != 'notes':
                caption = label(field.label, 'CustomerCaption')
                caption.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
                value = self.owner._field_value(job, field, 'jobs')
                self.fields.addRow(caption, label(value or 'Not recorded'))
        notes_field = next(field for field in self.owner.settings.fields_for('jobs') if field.key == 'notes')
        self.notes_heading.setText(notes_field.label)
        self.notes_heading.setVisible(notes_field.enabled)
        self.notes.setVisible(notes_field.enabled)
        self.notes.setPlainText(job['notes'] or 'No job notes recorded.')
        self.detail_scroll.verticalScrollBar().setValue(0)
        deleted = bool(job['deleted_at'])
        self.edit_button.setEnabled(not deleted)
        self.complete_button.setVisible(not deleted)
        self.complete_button.setEnabled(not deleted and job['status'] in ('Scheduled', 'In progress'))
        self.restore_button.setVisible(deleted)
        self.restore_button.setEnabled(deleted)
        self.more_button.setVisible(not deleted)
        self.trash_action.setEnabled(not deleted)
        self.view_customer_button.setEnabled(True)

    def clear_detail(self):
        self.focused_id = None
        self.detail_stack.setCurrentWidget(self.detail_empty)
        self.customer_name.clear()
        self.address.clear()
        self.contact.clear()
        self.notes.clear()
        self.edit_button.setEnabled(False)
        self.complete_button.setVisible(True)
        self.complete_button.setEnabled(False)
        self.restore_button.hide()
        self.more_button.hide()
        self.view_customer_button.setEnabled(False)

    def view_customer(self):
        job = next((row for row in self.rows if row['id'] == self.focused_id), None)
        if job is None:
            return
        customer = self.owner.db.get_customer(job['customer_id'])
        self.owner.customer_search.clear()
        self.owner.inactive.setChecked(not customer['active'])
        self.owner.selected_customer = job['customer_id']
        self.owner.refresh_customers()
        self.owner.tabs.setCurrentIndex(1)
