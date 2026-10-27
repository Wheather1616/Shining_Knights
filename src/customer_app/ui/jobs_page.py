"""Day-grouped jobs, independent export selection and a linked-job workspace."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from PySide6.QtCore import QDate, QSignalBlocker, QSize, Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPalette, QFont, QFontMetrics
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateEdit,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QScrollArea,
    QSizePolicy, QSplitter, QStackedWidget, QStyle, QStyledItemDelegate,
    QButtonGroup, QFrame, QGridLayout, QPushButton,
    QStyleOptionViewItem, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..config import JOB_FIELDS, JOB_STATUSES
from ..models import work_description
from .customer_page import label


def fees_text(records):
    total = sum((Decimal(str(job['fee'])) for job in records if job['fee'] is not None), Decimal(0))
    missing = sum(job['fee'] is None for job in records)
    return f'${total:,.2f}' + (f' · {missing} fee unset' if missing else '')


class JobsFilterCombo(QComboBox):
    """QComboBox API with a fully styled QMenu picker, avoiding macOS popup palette bugs.

    Menus are ordinary QWidget popups with explicit text and highlight colours.
    The selected action is checked. Only a real choice changes currentIndex.
    Existing currentData/currentText/findData signals and caller code are unchanged.
    """

    def showPopup(self):
        menu = QMenu(self)
        menu.setObjectName('JobsFilterPopup')
        menu.setMinimumWidth(max(self.width(), 215))
        menu.setPalette(self._popup_palette())
        menu.setStyleSheet("""
            QMenu#JobsFilterPopup { background: #FFFFFF; color: #302A30;
                border: 1px solid #DCCDC5; padding: 5px; }
            QMenu#JobsFilterPopup::item { background: #FFFFFF; color: #302A30;
                padding: 9px 20px 9px 26px; margin: 2px; border-radius: 6px; }
            QMenu#JobsFilterPopup::item:selected { background: #DFF1F5; color: #176478; }
            QMenu#JobsFilterPopup::item:checked { color: #52050A; font-weight: bold; }
            QMenu#JobsFilterPopup::indicator:checked { width: 13px; height: 13px;
                background: #258EA6; border-radius: 4px; }
        """)
        for index in range(self.count()):
            action = menu.addAction(self.itemText(index))
            action.setCheckable(True)
            action.setChecked(index == self.currentIndex())
            action.setEnabled(self.model().index(index, 0).flags() & Qt.ItemFlag.ItemIsEnabled != 0)
            action.triggered.connect(lambda checked=False, position=index: self.setCurrentIndex(position))
        origin = self.mapToGlobal(self.rect().bottomLeft())
        available = self.screen().availableGeometry()
        menu.adjustSize()
        origin.setX(max(available.left(), min(origin.x(), available.right() - menu.width())))
        if origin.y() + menu.height() > available.bottom():
            origin.setY(self.mapToGlobal(self.rect().topLeft()).y() - menu.height())
        menu.exec(origin)
        self.hidePopup()  # Required when QComboBox.showPopup is reimplemented.
        menu.deleteLater()

    @staticmethod
    def _popup_palette():
        palette = QPalette()
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive,
                      QPalette.ColorGroup.Disabled):
            palette.setColor(group, QPalette.ColorRole.Window, QColor('#FFFFFF'))
            palette.setColor(group, QPalette.ColorRole.Base, QColor('#FFFFFF'))
            palette.setColor(group, QPalette.ColorRole.Text, QColor('#302A30'))
            palette.setColor(group, QPalette.ColorRole.WindowText, QColor('#302A30'))
            palette.setColor(group, QPalette.ColorRole.ButtonText, QColor('#302A30'))
            palette.setColor(group, QPalette.ColorRole.Highlight, QColor('#DFF1F5'))
            palette.setColor(group, QPalette.ColorRole.HighlightedText, QColor('#176478'))
        return palette


class JobLineIcon(QWidget):
    """Simple vector icons drawn directly with Qt. No emoji glyphs or image files."""
    def __init__(self, kind, size=31, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(size, size)
        self.setObjectName('JobLineIcon')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        painter.setBrush(QColor('#EAF7F9' if self.kind in ('address','phone') else '#F9EAE8'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(0, 0, side, side))
        ink = QColor('#176478' if self.kind in ('address','phone') else '#52050A')
        pen = QPen(ink, 1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        center = side / 2
        if self.kind == 'address':
            painter.drawEllipse(QRectF(center-5.2, side*.20, 10.4, 10.4))
            painter.drawLine(int(center-6), int(side*.49), int(center), int(side*.80))
            painter.drawLine(int(center+6), int(side*.49), int(center), int(side*.80))
            painter.drawEllipse(QRectF(center-1.6, side*.31, 3.2, 3.2))
        elif self.kind == 'phone':
            # Handset silhouette built from 3 smooth arcs and a bridging diagonal.
            painter.drawArc(QRectF(side*.25, side*.18, side*.44, side*.62), 135*16, 190*16)
            painter.drawLine(int(side*.25), int(side*.30), int(side*.38), int(side*.43))
            painter.drawLine(int(side*.55), int(side*.61), int(side*.70), int(side*.74))
        elif self.kind == 'calendar':
            painter.drawRoundedRect(QRectF(side*.24, side*.28, side*.52, side*.49), 2.3, 2.3)
            painter.drawLine(int(side*.24), int(side*.43), int(side*.76), int(side*.43))
            painter.drawLine(int(side*.37), int(side*.20), int(side*.37), int(side*.34))
            painter.drawLine(int(side*.63), int(side*.20), int(side*.63), int(side*.34))
            painter.drawPoint(int(side*.40), int(side*.57))
            painter.drawPoint(int(side*.58), int(side*.57))
        elif self.kind == 'service':
            painter.drawRoundedRect(QRectF(side*.22,side*.32,side*.55,side*.38), 2.5,2.5)
            painter.drawLine(int(side*.22), int(side*.45), int(side*.77), int(side*.45))
            painter.drawLine(int(side*.39), int(side*.23), int(side*.39), int(side*.32))
            painter.drawLine(int(side*.61), int(side*.23), int(side*.61), int(side*.32))
        elif self.kind == 'payment':
            painter.drawRoundedRect(QRectF(side*.20,side*.28,side*.60,side*.44), 3,3)
            painter.drawLine(int(side*.20), int(side*.43), int(side*.80), int(side*.43))
            painter.drawLine(int(side*.32), int(side*.59), int(side*.47), int(side*.59))
        else:
            painter.drawEllipse(QRectF(side*.26, side*.26, side*.48, side*.48))
        painter.end()


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
        elif index.parent().isValid() and index.column() == 0:
            self._paint_customer(painter, option, index, text or '')
        else:
            super().paint(painter, option, index)

    @staticmethod
    def _paint_customer(painter, option, index, text):
        # Draw the native checkbox + selection without the default single-font text.
        opt = QStyleOptionViewItem(option)
        style = opt.widget.style()
        opt.text = ''
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        region = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget)
        if region.width() < 50:
            region = option.rect.adjusted(30, 2, -3, -2)
        name, _, suburb = str(text).partition('\n')
        painter.save()
        painter.setClipRect(option.rect)
        name_font = QFont(option.font)
        name_font.setWeight(QFont.Weight.DemiBold)
        name_font.setPixelSize(13)
        subtitle_font = QFont(option.font)
        subtitle_font.setPixelSize(11)
        name_metric = QFontMetrics(name_font)
        sub_metric = QFontMetrics(subtitle_font)
        painter.setFont(name_font)
        painter.setPen(QColor('#52050A'))
        if suburb:
            top = option.rect.center().y() - (name_metric.height() + sub_metric.height() + 3)//2
        else:
            top = option.rect.center().y() - name_metric.height()//2
        painter.drawText(region.left()+2, top+name_metric.ascent(),
                         name_metric.elidedText(name, Qt.TextElideMode.ElideRight, max(30, region.width()-6)))
        if suburb:
            painter.setFont(subtitle_font)
            painter.setPen(QColor('#736970'))
            painter.drawText(region.left()+2, top+name_metric.height()+3+sub_metric.ascent(),
                             sub_metric.elidedText(suburb, Qt.TextElideMode.ElideRight, max(30, region.width()-6)))
        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), 58 if index.parent().isValid() else 48)


class JobsPage(QWidget):
    """Compact schedule with independent filters/sorting and an actionable preview."""

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
        self._quick_buttons = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(13)
        heading = QHBoxLayout()
        heading.setSpacing(12)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        titles.addWidget(label('JOBS WORKSPACE', 'JobsKicker'))
        titles.addWidget(label('Jobs', 'JobsPageTitle'))
        titles.addWidget(label('Plan your days and manage service jobs.', 'PageHelper'))
        heading.addLayout(titles, 1)
        self.export_button = owner._button('Export CSV', lambda: None)
        self.export_button.setProperty('role', 'accent')
        self.export_button.setObjectName('JobsExportButton')
        self.export_menu = QMenu(self.export_button)
        self.export_menu.setObjectName('JobsMenu')
        self.export_selected_action = self.export_menu.addAction('Export selected jobs', owner.export_selected_jobs)
        self.export_filtered_action = self.export_menu.addAction('Export all filtered jobs', owner.export_jobs)
        self.export_button.setMenu(self.export_menu)
        heading.addWidget(self.export_button)
        add_button = owner._button('+  Add job', owner.add_job)
        add_button.setProperty('role', 'primary')
        add_button.setObjectName('JobsAddButton')
        heading.addWidget(add_button)
        layout.addLayout(heading)

        # Navigation-like view presets, distinct from the more precise controls below.
        top = QHBoxLayout()
        top.setSpacing(12)
        self.search = QLineEdit()
        self.search.setObjectName('JobsSearch')
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText('Search jobs or customers…')
        self.search.setAccessibleName('Search jobs')
        top.addWidget(self.search, 5)
        quick = QWidget()
        quick.setObjectName('JobsQuickFilters')
        quick_layout = QHBoxLayout(quick)
        quick_layout.setContentsMargins(3, 3, 3, 3)
        quick_layout.setSpacing(2)
        self.quick_group = QButtonGroup(self)
        self.quick_group.setExclusive(True)
        for key, text in (('all', 'All jobs'), ('today', 'Today'), ('upcoming', 'Upcoming'),
                          ('overdue', 'Overdue'), ('completed', 'Completed')):
            b = QPushButton(text)
            b.setObjectName('JobsQuickButton')
            b.setProperty('kind', key)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setAccessibleName(f'Show {text.lower()}')
            self.quick_group.addButton(b)
            quick_layout.addWidget(b)
            self._quick_buttons[key] = b
            b.clicked.connect(lambda _=False, selection=key: self._activate_quick(selection))
        self._quick_buttons['all'].setChecked(True)
        top.addWidget(quick, 6)
        layout.addLayout(top)

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(9)
        self.date_range = self._combo('Filter jobs by date range')
        for caption, value in [('All dates', 'all'), ('Today', 'today'), ('This week', 'week'),
                               ('Next 7 days', 'next7'), ('Next 30 days', 'next30'),
                               ('This month', 'month'), ('Custom range', 'custom')]:
            self.date_range.addItem(caption, value)
        self.status_filter = self._combo('Filter jobs by status')
        self.status_filter.addItems(['All', 'Upcoming', 'Overdue', *JOB_STATUSES, 'Trash'])
        self.payment_filter = self._combo('Filter by payment status')
        self.payment_filter.addItem('All payments', '')
        for value in ('Paid', 'Unpaid', 'Invoiced', 'Part-paid'):
            self.payment_filter.addItem(value, value)
        self.service_filter = self._combo('Filter by saved service')
        self.service_filter.addItem('All services', '')
        for w in (self.date_range, self.status_filter, self.payment_filter, self.service_filter):
            w.setMinimumWidth(105)
            filter_bar.addWidget(w, 1)
        filter_bar.addSpacing(6)
        filter_bar.addWidget(label('Sort by', 'JobsFilterLabel'))
        self.sort_by = self._combo('Sort jobs')
        self.sort_by.addItem('Scheduled date: newest first', 'date_desc')
        self.sort_by.addItem('Scheduled date: soonest first', 'date_asc')
        self.sort_by.addItem('Customer name: A–Z', 'name_asc')
        self.sort_by.addItem('Customer name: Z–A', 'name_desc')
        self.sort_by.addItem('Job status', 'status')
        self.sort_by.addItem('Fee: highest first', 'fee_high')
        self.sort_by.addItem('Fee: lowest first', 'fee_low')
        self.sort_by.setMinimumWidth(180)
        filter_bar.addWidget(self.sort_by, 2)
        filter_bar.addWidget(label('Group by', 'JobsFilterLabel'))
        self.group_by = self._combo('Group jobs')
        for caption, value in [('Scheduled day', 'date'), ('Completed day', 'completed'),
                               ('Customer', 'customer'), ('Status', 'status'), ('No grouping', 'none')]:
            self.group_by.addItem(caption, value)
        self.group_by.setMinimumWidth(130)
        filter_bar.addWidget(self.group_by, 1)
        layout.addLayout(filter_bar)

        self.custom_dates = QWidget()
        custom = QHBoxLayout(self.custom_dates)
        custom.setContentsMargins(0, 0, 0, 0)
        custom.setSpacing(9)
        self.from_date = QDateEdit(QDate.currentDate())
        self.to_date = QDateEdit(QDate.currentDate().addDays(6))
        for w, caption in ((self.from_date, 'From date'), (self.to_date, 'To date')):
            w.setCalendarPopup(True)
            w.setDisplayFormat('dd/MM/yyyy')
            w.setAccessibleName(caption)
            custom.addWidget(label(caption, 'JobsFilterLabel'))
            custom.addWidget(w)
        custom.addStretch()
        layout.addWidget(self.custom_dates)
        self.custom_dates.hide()
        self.date_error = label('From date must be on or before To date.', 'JobsError')
        layout.addWidget(self.date_error)
        self.date_error.hide()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName('JobsSplitter')
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(12)
        self.list_card = QWidget()
        self.list_card.setObjectName('JobsListCard')
        self.list_card.setMinimumWidth(390)
        left = QVBoxLayout(self.list_card)
        left.setContentsMargins(13, 14, 13, 12)
        left.setSpacing(9)
        list_header = QHBoxLayout()
        list_header.addWidget(label('Jobs overview', 'JobsPanelTitle'), 1)
        self.expand_button = owner._button('Expand all', lambda: self.tree.expandAll())
        self.collapse_button = owner._button('Collapse all', lambda: self.tree.collapseAll())
        for b in (self.expand_button, self.collapse_button):
            b.setProperty('role', 'link')
            list_header.addWidget(b)
        left.addLayout(list_header)
        self.count = label('0 jobs', 'JobsCount')
        left.addWidget(self.count)
        self.empty = label('No jobs yet. Use Add job to get started.', 'CustomerEmpty')
        left.addWidget(self.empty)
        self.tree = QTreeWidget()
        self.tree.setObjectName('JobsTree')
        self.tree.setAccessibleName('Jobs list: choose a row to view details, check boxes for export')
        self.tree.badge_columns = set()
        self.tree.setItemDelegate(JobDelegate(self.tree))
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setUniformRowHeights(False)
        self.tree.setAlternatingRowColors(False)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tree.setMinimumHeight(150)
        self.tree.itemChanged.connect(self._check_changed)
        self.tree.currentItemChanged.connect(self._focus_changed)
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        left.addWidget(self.tree, 1)
        selection_bar = QHBoxLayout()
        self.select_all = QCheckBox('Select all')
        self.select_all.setTristate(True)
        self.select_all.setAccessibleName('Select all filtered jobs for export')
        selection_bar.addWidget(self.select_all)
        self.selection_caption = label('No jobs selected for export.', 'JobsSelection')
        selection_bar.addWidget(self.selection_caption, 1)
        self.clear_button = owner._button('Clear', self.clear_export_selection)
        self.clear_button.setProperty('role', 'link')
        selection_bar.addWidget(self.clear_button)
        self.export_selected_button = owner._button('Export selected (0)', owner.export_selected_jobs)
        self.export_selected_button.setProperty('role', 'accent')
        selection_bar.addWidget(self.export_selected_button)
        left.addLayout(selection_bar)
        self.splitter.addWidget(self.list_card)

        self.detail_card = QWidget()
        self.detail_card.setObjectName('JobDetailCard')
        self.detail_card.setMinimumWidth(345)
        right = QVBoxLayout(self.detail_card)
        right.setContentsMargins(16, 16, 16, 16)
        right.setSpacing(10)
        self.detail_stack = QStackedWidget()
        self.detail_empty = label('Select a job to see its details.\n\nTick the checkboxes to export several jobs.', 'CustomerEmpty')
        self.detail_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_stack.addWidget(self.detail_empty)
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setObjectName('JobDetailScroll')
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName('JobDetailContent')
        details = QVBoxLayout(content)
        details.setContentsMargins(1, 1, 6, 6)
        details.setSpacing(19)
        # Dynamic chips and optional custom fields must increase the scrollable
        # content height instead of painting underneath the fixed action bar.
        from PySide6.QtWidgets import QLayout
        details.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        heading2 = QHBoxLayout()
        self.job_id = QLabel('')
        self.job_id.setObjectName('JobIdentifier')
        self.job_id.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        heading2.addWidget(self.job_id, 1)
        self.job_status = label('', 'JobStatus')
        self.job_status.setWordWrap(False)
        self.job_status.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        heading2.addWidget(self.job_status)
        details.addLayout(heading2)
        self.customer_name = QLabel('')
        self.customer_name.setObjectName('JobCustomerName')
        self.customer_name.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.customer_name.setWordWrap(True)
        details.addWidget(self.customer_name)
        self.view_customer_button = owner._button('View customer  →', self.view_customer)
        self.view_customer_button.setProperty('role', 'link')
        details.addWidget(self.view_customer_button, 0, Qt.AlignmentFlag.AlignLeft)
        contact = QGridLayout()
        contact.setHorizontalSpacing(12)
        contact.setVerticalSpacing(7)
        self.address = label('', 'JobInfoValue')
        self.contact = label('', 'JobInfoValue')
        self._icon_fact(contact, 0, '⌖', 'SERVICE ADDRESS', self.address)
        self._icon_fact(contact, 1, '☎', 'CONTACT', self.contact)
        details.addLayout(contact)
        details.addWidget(self._rule())
        # Distinct information sections, deliberately built from existing job data.
        schedule_section, self.schedule_layout = self._section('▦', 'Schedule')
        self.scheduled_value = self._value_row(self.schedule_layout, 'Scheduled date')
        self.completed_value = self._value_row(self.schedule_layout, 'Completed date')
        details.addWidget(schedule_section)
        details.addWidget(self._rule())
        service_section, service_lay = self._section('✦', 'Service details')
        self.service_name_value = self._value_row(service_lay, 'Saved service')
        service_lay.addWidget(label('NATURE OF JOB', 'JobFieldCaption'))
        self.scope_chips = QWidget()
        self.scope_chips.setObjectName('JobChipHost')
        self.scope_layout = QVBoxLayout(self.scope_chips)
        self.scope_layout.setContentsMargins(0, 0, 0, 0)
        self.scope_layout.setSpacing(6)
        self.scope_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        service_lay.addWidget(self.scope_chips)
        service_lay.addWidget(label('EQUIPMENT', 'JobFieldCaption'))
        self.equipment_chips = QWidget()
        self.equipment_chips.setObjectName('JobChipHost')
        self.equipment_layout = QVBoxLayout(self.equipment_chips)
        self.equipment_layout.setContentsMargins(0, 0, 0, 0)
        self.equipment_layout.setSpacing(6)
        self.equipment_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        service_lay.addWidget(self.equipment_chips)
        details.addWidget(service_section)
        details.addWidget(self._rule())
        pricing_section, price_lay = self._section('$', 'Pricing & payment')
        self.fee_value = self._value_row(price_lay, 'Charge / fee (AUD)', 'JobFeeValue')
        self.payment_method_value = self._value_row(price_lay, 'Payment method')
        self.payment_status_value = self._value_row(price_lay, 'Payment status', 'JobPaymentValue')
        self.hours_value = self._value_row(price_lay, 'Number of hours')
        details.addWidget(pricing_section)
        self.extra_card, self.extra_fields = self._section('⋯', 'Additional details')
        details.addWidget(self.extra_card)
        self.notes_heading = label('JOB NOTES', 'JobFieldCaption')
        details.addWidget(self.notes_heading)
        self.notes = QTextEdit()
        self.notes.setObjectName('JobDetailNotes')
        self.notes.setReadOnly(True)
        self.notes.setAcceptRichText(False)
        self.notes.setMinimumHeight(72)
        self.notes.setMaximumHeight(125)
        details.addWidget(self.notes)
        details.addStretch()
        self.detail_scroll.setWidget(content)
        self.detail_stack.addWidget(self.detail_scroll)
        right.addWidget(self.detail_stack, 1)
        actions = QHBoxLayout()
        self.edit_button = owner._button('Edit job', owner.edit_job)
        self.edit_button.setObjectName('JobEditAction')
        self.complete_button = owner._button('Mark completed', owner.mark_completed)
        self.complete_button.setProperty('role', 'primary')
        self.restore_button = owner._button('Restore job', owner.restore_job)
        self.restore_button.setProperty('role', 'accent')
        for button in (self.edit_button, self.complete_button, self.restore_button):
            actions.addWidget(button, 1)
        right.addLayout(actions)
        self.more_button = owner._button('More actions', lambda: None)
        self.more_button.setProperty('role', 'jobMenu')
        self.more_menu = QMenu(self.more_button)
        self.more_menu.setObjectName('JobsMenu')
        self.trash_action = self.more_menu.addAction('Move to Trash', owner.trash_job)
        self.more_button.setMenu(self.more_menu)
        right.addWidget(self.more_button, 0, Qt.AlignmentFlag.AlignRight)
        self.splitter.addWidget(self.detail_card)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 5)
        self.splitter.setSizes([770, 450])
        layout.addWidget(self.splitter, 1)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self._filters_changed)
        self.search.textChanged.connect(lambda *_: self.search_timer.start())
        for combo in (self.status_filter, self.date_range, self.payment_filter, self.service_filter):
            combo.currentIndexChanged.connect(self._filters_changed)
        self.sort_by.currentIndexChanged.connect(self._presentation_changed)
        self.group_by.currentIndexChanged.connect(self._presentation_changed)
        self.from_date.dateChanged.connect(self._filters_changed)
        self.to_date.dateChanged.connect(self._filters_changed)
        self.select_all.checkStateChanged.connect(self._select_all_changed)
        self.clear_detail()
        self._update_export_selection()

    @staticmethod
    def _combo(accessible_name):
        combo = JobsFilterCombo()
        combo.setProperty('role', 'jobFilter')
        combo.setAccessibleName(accessible_name)
        combo.setMinimumContentsLength(9)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        return combo

    @staticmethod
    def _rule():
        line = QFrame()
        line.setObjectName('JobDetailDivider')
        line.setFixedHeight(1)
        return line

    @staticmethod
    def _section(symbol, title):
        box = QWidget()
        box.setObjectName('JobDetailSection')
        vertical = QVBoxLayout(box)
        vertical.setContentsMargins(0, 0, 0, 0)
        vertical.setSpacing(12)
        heading = QHBoxLayout()
        heading.setContentsMargins(0, 3, 0, 7)
        heading.setSpacing(11)
        kind = {'▦': 'calendar', '✦': 'service', '$': 'payment', '⋯': 'other'}.get(symbol, 'other')
        heading.addWidget(JobLineIcon(kind, 32), 0, Qt.AlignmentFlag.AlignVCenter)
        title_label = QLabel(title)
        title_label.setObjectName('JobSectionTitle')
        title_label.setWordWrap(False)
        title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        title_label.setMinimumHeight(35)
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        heading.addWidget(title_label, 1)
        vertical.addLayout(heading)
        return box, vertical

    @staticmethod
    def _value_row(where, caption, name='JobInfoValue'):
        line = QWidget()
        line.setObjectName('JobDetailValueRow')
        columns = QHBoxLayout(line)
        columns.setContentsMargins(0, 1, 0, 3)
        columns.setSpacing(15)
        key = QLabel(caption)
        key.setObjectName('JobFieldCaption')
        key.setWordWrap(True)
        key.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        key.setMinimumWidth(110)
        columns.addWidget(key, 2, Qt.AlignmentFlag.AlignTop)
        value = QLabel('')
        value.setObjectName(name)
        value.setTextFormat(Qt.TextFormat.PlainText)
        value.setWordWrap(True)
        value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        columns.addWidget(value, 3, Qt.AlignmentFlag.AlignTop)
        where.addWidget(line)
        return value

    @staticmethod
    def _icon_fact(grid, column, icon, caption, value):
        container = QWidget()
        container.setObjectName('JobContactFact')
        row = QVBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        heading = QHBoxLayout()
        heading.setSpacing(8)
        heading.addWidget(JobLineIcon('address' if caption == 'SERVICE ADDRESS' else 'phone', 30))
        key = QLabel(caption)
        key.setObjectName('JobFactCaption')
        key.setWordWrap(False)
        key.setMinimumHeight(28)
        key.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        key.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        heading.addWidget(key, 1)
        row.addLayout(heading)
        value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        value.setWordWrap(True)
        row.addWidget(value, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(container, 0, column, Qt.AlignmentFlag.AlignTop)
        grid.setColumnStretch(column, 1)

    @staticmethod
    def _chips(layout, values, tone):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for value in (values or ['Not recorded']):
            chip = QLabel(str(value))
            chip.setObjectName('JobDetailChip')
            chip.setTextFormat(Qt.TextFormat.PlainText)
            chip.setProperty('tone', tone)
            chip.setMinimumHeight(30)
            chip.setWordWrap(True)
            chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(chip)
        layout.invalidate()

    def _activate_quick(self, selection):
        blockers = [QSignalBlocker(w) for w in (self.status_filter, self.date_range)]
        self.status_filter.setCurrentText({'all': 'All', 'today': 'All', 'upcoming': 'Upcoming',
                                            'overdue': 'Overdue', 'completed': 'Completed'}[selection])
        self.date_range.setCurrentIndex(self.date_range.findData('today' if selection == 'today' else 'all'))
        del blockers
        self._filters_changed()

    def _sync_quick(self):
        state = self.status_filter.currentText()
        day = self.date_range.currentData()
        selection = ('today' if state == 'All' and day == 'today' else
                     'upcoming' if state == 'Upcoming' and day == 'all' else
                     'overdue' if state == 'Overdue' and day == 'all' else
                     'completed' if state == 'Completed' and day == 'all' else
                     'all' if state == 'All' and day == 'all' else None)
        blocker = QSignalBlocker(self.quick_group)
        self.quick_group.setExclusive(False)
        for key, button in self._quick_buttons.items():
            button.setChecked(key == selection)
        self.quick_group.setExclusive(True)
        del blocker

    def _presentation_changed(self, *_):
        # Reordering must not throw away export selections.
        self.owner.refresh_jobs()
        self.owner.remember_job_filters()

    def _refresh_service_choices(self):
        """Only show names that exist in jobs; keep a selected historical name."""
        selected = self.service_filter.currentData() or ''
        try:
            existing = self.owner.db.list_jobs()
        except Exception:
            return
        names = sorted({str(j.get('service_name') or '').strip() for j in existing if j.get('service_name')}, key=str.casefold)
        if selected and selected not in names:
            names.append(selected)
        blocker = QSignalBlocker(self.service_filter)
        self.service_filter.clear()
        self.service_filter.addItem('All services', '')
        for name in names:
            self.service_filter.addItem(name, name)
        self.service_filter.setCurrentIndex(max(0, self.service_filter.findData(selected)))
        del blocker

    def _filters_changed(self, *_):
        self.custom_dates.setVisible(self.date_range.currentData() == 'custom')
        self._selection_cleared = bool(self.checked_ids)
        self.checked_ids.clear()
        self._sync_quick()
        self.owner.refresh_jobs()
        self.owner.remember_job_filters()

    def preference_filters(self):
        return {'status': self.status_filter.currentText(), 'range': self.date_range.currentData(),
                'group': self.group_by.currentData(), 'sort': self.sort_by.currentData(),
                'payment': self.payment_filter.currentData() or '',
                'service': self.service_filter.currentData() or '',
                'from': self.from_date.date().toString('yyyy-MM-dd'),
                'to': self.to_date.date().toString('yyyy-MM-dd')}

    def load_preferences(self):
        settings = self.owner.settings
        filters = settings.jobs_filters if settings.remember_jobs_filters else {}
        widgets = (self.status_filter, self.date_range, self.group_by, self.sort_by,
                   self.payment_filter, self.service_filter, self.from_date, self.to_date)
        blockers = [QSignalBlocker(widget) for widget in widgets]
        # All jobs, newest first: avoids burying recent jobs beneath historical records.
        self.status_filter.setCurrentText(filters.get('status', 'All'))
        self.date_range.setCurrentIndex(max(0, self.date_range.findData(filters.get('range', 'all'))))
        self.group_by.setCurrentIndex(max(0, self.group_by.findData(filters.get('group', settings.jobs_default_group))))
        self.sort_by.setCurrentIndex(max(0, self.sort_by.findData(filters.get('sort', 'date_desc'))))
        self.payment_filter.setCurrentIndex(max(0, self.payment_filter.findData(filters.get('payment', ''))))
        self._refresh_service_choices()
        self.service_filter.setCurrentIndex(max(0, self.service_filter.findData(filters.get('service', ''))))
        for widget, key in ((self.from_date, 'from'), (self.to_date, 'to')):
            value = QDate.fromString(filters.get(key, ''), 'yyyy-MM-dd')
            if value.isValid():
                widget.setDate(value)
        self.custom_dates.setVisible(self.date_range.currentData() == 'custom')
        del blockers
        self._sync_quick()

    def date_field(self):
        return 'completed_date' if self.group_by.currentData() == 'completed' else 'scheduled_date'

    def filter_dates(self, jobs):
        # Local filters sit after database status/search filtering; they never
        # mutate the records or influence CSV exports outside the visible set.
        choice = self.date_range.currentData()
        self.date_error.hide()
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
        elif choice == 'next30':
            start, end = today, today + timedelta(days=29)
        elif choice == 'month':
            start = today.replace(day=1)
            end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        else:
            start = end = None
        if start is not None:
            key = self.date_field()
            jobs = [j for j in jobs if j.get(key) and start.isoformat() <= j[key] <= end.isoformat()]
        # Upcoming excludes overdue work (which has its own preset).
        if self.status_filter.currentText() == 'Upcoming':
            jobs = [j for j in jobs if j.get('scheduled_date') and j['scheduled_date'] >= today.isoformat()]
        pay = self.payment_filter.currentData()
        if pay:
            jobs = [j for j in jobs if j.get('payment_status') == pay]
        service = self.service_filter.currentData()
        if service:
            jobs = [j for j in jobs if j.get('service_name') == service]
        return jobs

    def _sorted_jobs(self, jobs):
        sort = self.sort_by.currentData() or 'date_desc'
        ordered = list(jobs)
        if sort in ('date_desc', 'date_asc'):
            # Missing dates always come last, in either direction.
            present = [j for j in ordered if j.get('scheduled_date')]
            missing = [j for j in ordered if not j.get('scheduled_date')]
            present.sort(key=lambda j: (j['scheduled_date'], j['id']), reverse=sort == 'date_desc')
            return present + missing
        if sort in ('name_asc', 'name_desc'):
            return sorted(ordered, key=lambda j: ((j.get('customer_name') or '').casefold(), j['id']),
                          reverse=sort == 'name_desc')
        if sort == 'status':
            rank = {'Overdue': 0, 'In progress': 1, 'Scheduled': 2, 'Completed': 3, 'Cancelled': 4}
            today = date.today().isoformat()
            def status_key(j):
                state = ('Overdue' if j.get('status') in ('Scheduled', 'In progress') and
                         j.get('scheduled_date') and j['scheduled_date'] < today else j.get('status'))
                return (rank.get(state, 5), j.get('scheduled_date') or '9999-12-31', j['id'])
            return sorted(ordered, key=status_key)
        if sort in ('fee_high', 'fee_low'):
            present = [j for j in ordered if j.get('fee') not in ('', None)]
            missing = [j for j in ordered if j.get('fee') in ('', None)]
            present.sort(key=lambda j: (Decimal(str(j['fee'])), j['id']), reverse=sort == 'fee_high')
            return present + missing
        if sort == 'updated':
            return sorted(ordered, key=lambda j: (j.get('updated_at') or j.get('scheduled_date') or '', j['id']), reverse=True)
        return ordered

    def _bucket(self, job):
        kind = self.group_by.currentData()
        if kind == 'none':
            return ('all', 'all'), 'All matching jobs'
        if kind == 'customer':
            return ('customer', job['customer_id']), job['customer_name']
        if kind == 'status':
            return ('status', job['status']), job['status']
        value = job.get(self.date_field())
        day = date.fromisoformat(value) if value else None
        caption = (day.strftime('%A') + f', {day.day} ' + day.strftime('%B %Y')) if day else (
            'No completion date' if kind == 'completed' else 'Unscheduled')
        return (kind, value), caption

    def set_jobs(self, jobs):
        previous = self.focused_id
        collapsed = {bucket for bucket, item in self.groups.items() if not item.isExpanded()}
        same_grouping = self.grouping == self.group_by.currentData()
        self.grouping = self.group_by.currentData()
        self.rows = self._sorted_jobs(jobs)
        self.checked_ids.intersection_update(j['id'] for j in jobs)
        self._updating = True
        with QSignalBlocker(self.tree):
            self.tree.clear()
            self.items = {}
            self.groups = {}
            # Six essentials fit the available width better than all configured
            # fields. All other fields remain available in the detail panel.
            self.tree.setColumnCount(6)
            self.tree.setHeaderLabels(['Customer / suburb', 'Service', 'Status', 'Payment', 'Scheduled', 'Fee (AUD)'])
            self.tree.badge_columns = {2, 3}
            buckets = {}
            for job in self.rows:
                bucket, caption = self._bucket(job)
                buckets.setdefault(bucket, (caption, []))[1].append(job)
            for bucket, (caption, records) in buckets.items():
                caption = f'{caption}   ·   {len(records)} job' + ('' if len(records) == 1 else 's') + f'   ·   {fees_text(records)}'
                group = QTreeWidgetItem([caption])
                group.setData(0, Qt.ItemDataRole.UserRole + 1, bucket)
                group.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
                group.setCheckState(0, Qt.CheckState.Unchecked)
                font = QFont(self.tree.font())
                font.setWeight(QFont.Weight.Bold)
                font.setPixelSize(13)
                group.setFont(0, font)
                group.setForeground(0, QColor('#52050A'))
                for c in range(6):
                    group.setBackground(c, QColor('#F8EEE9'))
                self.tree.addTopLevelItem(group)
                group.setFirstColumnSpanned(True)
                self.groups[bucket] = group
                for job in records:
                    customer = (job.get('customer_name') or 'Unnamed customer') + (
                        '\n' + job['suburb'] if job.get('suburb') else '')
                    from .main_window import display
                    values = [customer, str(job.get('service_name') or 'Usual service'),
                              str(job.get('status') or ''), str(job.get('payment_status') or ''),
                              display(job.get('scheduled_date'), 'date') or 'Unscheduled',
                              display(job.get('fee'), 'currency') or 'Not set']
                    item = QTreeWidgetItem(values)
                    item.setData(0, Qt.ItemDataRole.UserRole, job['id'])
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.CheckState.Checked if job['id'] in self.checked_ids else Qt.CheckState.Unchecked)
                    item.setTextAlignment(5, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    for index, value in enumerate(values):
                        item.setToolTip(index, value)
                    group.addChild(item)
                    self.items[job['id']] = item
                group.setExpanded(not (same_grouping and bucket in collapsed))
            for index, width in enumerate((190, 122, 106, 93, 110, 95)):
                self.tree.setColumnWidth(index, width)
            self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            if previous in self.items:
                target = self.items[previous]
                target.parent().setExpanded(True)
                self.tree.setCurrentItem(target)
            elif self.rows:
                # Open with a useful job preview rather than an empty sidebar.
                self.tree.setCurrentItem(self.items[self.rows[0]['id']])
        self._updating = False
        self._sync_quick()
        self._refresh_service_choices()
        self._refresh_quick_counts()
        count = len(self.rows)
        self.count.setText(f'{count} job' + ('' if count == 1 else 's') +
                           f'  ·  {len(self.groups)} group' + ('' if len(self.groups) == 1 else 's') +
                           f'  ·  Total fees {fees_text(self.rows)}')
        self.empty.setVisible(not self.rows)
        self.empty.setText('No jobs match these filters.' if not self.rows else '')
        self._focus_changed(self.tree.currentItem(), None)
        self._update_export_selection()

    def _refresh_quick_counts(self):
        try:
            records = self.owner.db.list_jobs()
        except Exception:
            return
        today = date.today().isoformat()
        counts = {
            'all': len(records),
            'today': sum(j.get('scheduled_date') == today for j in records),
            'upcoming': sum(j.get('status') in ('Scheduled', 'In progress') and
                            bool(j.get('scheduled_date')) and j['scheduled_date'] >= today for j in records),
            'overdue': sum(j.get('status') in ('Scheduled', 'In progress') and
                           bool(j.get('scheduled_date')) and j['scheduled_date'] < today for j in records),
            'completed': sum(j.get('status') == 'Completed' for j in records),
        }
        for key, button in self._quick_buttons.items():
            button.setText({'all': 'All jobs', 'today': 'Today', 'upcoming': 'Upcoming',
                            'overdue': 'Overdue', 'completed': 'Completed'}[key] + f'  {counts[key]}')

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
            self.selection_caption.setText(caption + f' · {fees_text(records)}')
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
        self.job_id.setText(f'JOB #{job_id}')
        current_status = 'In Trash' if job.get('deleted_at') else job.get('status') or 'Not set'
        self.job_status.setText(current_status)
        self.job_status.setProperty('status', current_status.lower().replace(' ', '-'))
        self.job_status.style().unpolish(self.job_status)
        self.job_status.style().polish(self.job_status)
        self.customer_name.setText(job.get('customer_name') or 'Unnamed customer')
        self.address.setText('\n'.join(filter(None, [customer.get('address_line_1'), customer.get('address_line_2'),
            ' '.join(filter(None, [customer.get('suburb'), customer.get('state'), customer.get('postcode')]))])) or 'Address not recorded')
        self.contact.setText('\n'.join(filter(None, [customer.get('phone'), customer.get('email')])) or 'Not recorded')
        from .main_window import display
        self.scheduled_value.setText(display(job.get('scheduled_date'), 'date') or 'Not scheduled')
        self.completed_value.setText(display(job.get('completed_date'), 'date') or 'Not completed')
        self.service_name_value.setText(str(job.get('service_name') or 'Usual service'))
        scope = job.get('job_type') or []
        if isinstance(scope, str):
            scope = [scope] if scope else []
        sides = job.get('job_type_sides') or {}
        scope = [str(n) + (f' ({str(sides[n]).title()})' if sides.get(n) else '') for n in scope]
        equipment = job.get('equipment') or []
        if isinstance(equipment, str):
            equipment = [equipment] if equipment else []
        self._chips(self.scope_layout, scope, 'teal')
        self._chips(self.equipment_layout, equipment, 'maroon')
        self.fee_value.setText(display(job.get('fee'), 'currency') or 'Not set')
        self.payment_method_value.setText(str(job.get('payment_type') or 'Not set'))
        self.payment_status_value.setText(str(job.get('payment_status') or 'Not set'))
        self.payment_status_value.setProperty('state', str(job.get('payment_status') or '').lower().replace(' ', '-'))
        self.payment_status_value.style().unpolish(self.payment_status_value)
        self.payment_status_value.style().polish(self.payment_status_value)
        self.hours_value.setText(str(job['hours']) if job.get('hours') not in (None, '') else 'Not set')
        # Preserve any custom, user-configured job fields here.
        while self.extra_fields.count() > 1:
            child = self.extra_fields.takeAt(1)
            if child.widget():
                child.widget().deleteLater()
        custom_fields = [f for f in self.owner.settings.fields_for('jobs')
                         if f.enabled and f.key not in ('scheduled_date', 'completed_date', 'status',
                                                        'job_type', 'equipment', 'fee', 'payment_type',
                                                        'payment_status', 'hours', 'service_name', 'notes')]
        self.extra_card.setVisible(bool(custom_fields))
        for field in custom_fields:
            element = self._value_row(self.extra_fields, field.label)
            element.setText(self.owner._field_value(job, field, 'jobs') or 'Not recorded')
        note = next((f for f in self.owner.settings.fields_for('jobs') if f.key == 'notes'), None)
        self.notes_heading.setVisible(bool(note and note.enabled))
        self.notes.setVisible(bool(note and note.enabled))
        self.notes.setPlainText(str(job.get('notes') or 'No job notes recorded.'))
        self.detail_scroll.verticalScrollBar().setValue(0)
        deleted = bool(job.get('deleted_at'))
        self.edit_button.setEnabled(not deleted)
        self.edit_button.setVisible(not deleted)
        # Don't show a meaningless disabled Mark completed button on completed jobs.
        self.complete_button.setVisible(not deleted and job.get('status') in ('Scheduled', 'In progress'))
        self.complete_button.setEnabled(not deleted and job.get('status') in ('Scheduled', 'In progress'))
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
        self.complete_button.hide()
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
