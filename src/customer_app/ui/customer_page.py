"""Customer directory and customer workspace with stronger visual hierarchy.

This revision keeps the existing selection, editing, services and history
behaviour intact, but makes the customer profile look much closer to the
approved mock-up by introducing icon tiles, clearer metric cards and more
intentional spacing.
"""
from PySide6.QtCore import QSize, Qt, QRectF, QEvent, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QFrame
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QScrollArea, QSizePolicy, QSplitter,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)


def label(text='', name='CustomerValue'):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    widget.setMinimumWidth(0)
    widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


class GlyphIcon(QWidget):
    """Small line icon with a coloured circular background."""

    PALETTE = {
        'maroon': ('#F8EAE8', '#7A0B16'),
        'teal': ('#EAF7F9', '#258EA6'),
        'coral': ('#FFF0EB', '#F87666'),
        'green': ('#EAF7F0', '#2D7650'),
    }

    def __init__(self, kind: str, tone: str = 'teal', size: int = 38, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.tone = tone
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        bg, ink = self.PALETTE.get(self.tone, self.PALETTE['teal'])
        s = self._size
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawEllipse(QRectF(0, 0, s, s))
        pen = QPen(QColor(ink), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx = s / 2
        cy = s / 2

        if self.kind == 'location':
            painter.drawEllipse(QRectF(cx - 5, 8, 10, 10))
            painter.drawLine(cx, 18, cx, s - 10)
            painter.drawLine(cx, s - 10, cx - 5, s - 15)
            painter.drawLine(cx, s - 10, cx + 5, s - 15)
        elif self.kind == 'phone':
            painter.drawArc(QRectF(10, 10, 8, 18), 250 * 16, 120 * 16)
            painter.drawArc(QRectF(18, 10, 10, 18), -10 * 16, 120 * 16)
            painter.drawLine(14, 26, 18, 30)
            painter.drawLine(23, 8, 28, 12)
        elif self.kind == 'repeat':
            painter.drawArc(QRectF(8, 12, 16, 14), 30 * 16, 250 * 16)
            painter.drawLine(24, 10, 28, 14)
            painter.drawLine(24, 10, 22, 15)
            painter.drawArc(QRectF(14, 12, 16, 14), 210 * 16, 250 * 16)
            painter.drawLine(14, 28, 10, 24)
            painter.drawLine(14, 28, 16, 23)
        elif self.kind == 'card':
            painter.drawRoundedRect(QRectF(9, 12, 20, 14), 3, 3)
            painter.drawLine(9, 17, 29, 17)
            painter.drawLine(13, 22, 18, 22)
        elif self.kind == 'calendar':
            painter.drawRoundedRect(QRectF(9, 12, 20, 16), 3, 3)
            painter.drawLine(9, 17, 29, 17)
            painter.drawLine(14, 9, 14, 14)
            painter.drawLine(24, 9, 24, 14)
            painter.drawPoint(15, 22)
            painter.drawPoint(23, 22)
        elif self.kind == 'check':
            painter.drawRoundedRect(QRectF(9, 10, 20, 20), 5, 5)
            painter.drawLine(14, 20, 18, 24)
            painter.drawLine(18, 24, 25, 16)
        else:
            painter.drawEllipse(QRectF(cx - 6, cy - 6, 12, 12))
        painter.end()


class FactTile(QWidget):
    def __init__(self, caption: str, tone: str, kind: str, parent=None):
        super().__init__(parent)
        self.setObjectName('CustomerInfoTile')
        self.setProperty('tone', tone)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.addWidget(GlyphIcon(kind, tone, 36), 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        text_col.addWidget(label(caption, 'CustomerTileCaption'))
        self.value = label('', 'CustomerTileValue')
        self.value.setWordWrap(False)
        text_col.addWidget(self.value)
        layout.addLayout(text_col, 1)


class MetricTile(QWidget):
    def __init__(self, caption: str, tone: str, kind: str, parent=None):
        super().__init__(parent)
        self.setObjectName('CustomerMetricTile')
        self.setProperty('tone', tone)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(GlyphIcon(kind, tone, 40), 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.addWidget(label(caption, 'CustomerMetricCaption'))
        self.value = label('', 'CustomerMetricValue')
        self.value.setWordWrap(False)
        text_col.addWidget(self.value)
        layout.addLayout(text_col, 1)


class DirectoryDelegate(QStyledItemDelegate):
    """Paint a compact or expanded card for *each* directory record.

    Expanded facts are stored on the individual table item, not in a separate
    selected-customer widget. Row heights follow the available column width.
    """
    DETAILS_ROLE = Qt.ItemDataRole.UserRole + 1

    @staticmethod
    def _font(base, pixels, bold=False):
        font = QFont(base)
        font.setPixelSize(pixels)
        font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        return font

    def _measure(self, font, value, width):
        metrics = QFontMetrics(font)
        return max(metrics.height(), metrics.boundingRect(
            0, 0, max(55, width), 20000,
            int(Qt.TextFlag.TextWordWrap), str(value)
        ).height())

    def _elements(self, option, index, width):
        """Build text runs with measured heights, shared by paint/sizeHint."""
        compact_lines = str(index.data(Qt.ItemDataRole.DisplayRole) or '').split('\n')
        details = index.data(self.DETAILS_ROLE) or []
        elements = []
        for i, text in enumerate(compact_lines[:3]):
            font = self._font(option.font, 15 if i == 0 else 12, i == 0)
            height = self._measure(font, text, width) if i == 0 else QFontMetrics(font).height()
            elements.append(('compact', text, font, height, 3 if i == 0 else 2))
        if details:
            elements.append(('divider', '', option.font, 1, 10))
            for heading, value in details:
                heading_font = self._font(option.font, 11, True)
                body_font = self._font(option.font, 12)
                elements.append(('heading', heading, heading_font,
                                 self._measure(heading_font, heading, width), 3))
                elements.append(('body', str(value), body_font,
                                 self._measure(body_font, value, width), 11))
        return elements

    def paint(self, painter, option, index):
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = option.rect.adjusted(3, 4, -4, -4)
        content = rect.adjusted(16, 12, -29, -8)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(option.rect)
        painter.fillRect(option.rect, QColor('#fffdfb'))
        painter.setPen(QColor('#b8dce4' if selected else '#e8ddd6'))
        painter.setBrush(QColor('#edf8fa' if selected else '#fbf7f3' if hovered else '#fffdfb'))
        painter.drawRoundedRect(rect, 12, 12)
        if selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor('#258ea6'))
            painter.drawRoundedRect(rect.adjusted(0, 1, -rect.width() + 4, -1), 2, 2)

        y = content.top()
        for kind, value, font, height, gap in self._elements(option, index, content.width()):
            if kind == 'divider':
                painter.setPen(QPen(QColor('#d7e6e8'), 1))
                painter.drawLine(content.left(), y + 2, content.right(), y + 2)
            else:
                painter.setFont(font)
                painter.setPen(QColor('#52050a' if kind == 'heading' else
                                      '#176478' if kind == 'compact' and y != content.top() and selected else
                                      '#302a30' if kind in ('compact', 'body') else '#176478'))
                if kind == 'heading':
                    painter.setPen(QColor('#176478'))
                elif kind == 'compact' and font.pixelSize() == 12:
                    painter.setPen(QColor('#6b6267'))
                bounds = QRectF(content.left(), y, content.width(), height + 2)
                painter.drawText(bounds, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop |
                                 Qt.TextFlag.TextWordWrap, value)
            y += height + gap

        arrow_font = self._font(option.font, 22)
        painter.setFont(arrow_font)
        painter.setPen(QColor('#258ea6' if selected else '#8a8185'))
        painter.drawText(rect.adjusted(0, 0, -13, 0),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, '›')
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QColor('#258ea6'))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)
        painter.restore()

    def sizeHint(self, option, index):
        table = self.parent()
        width = max(160, table.columnWidth(index.column()) - 3 - 4 - 16 - 29)
        elements = self._elements(option, index, width)
        total = 12 + sum(h + gap for _, _, _, h, gap in elements) + 8 + 8
        return QSize(200, max(86, total))


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
        rect.setWidth(min(rect.width(), option.fontMetrics.horizontalAdvance(text) + 18))
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
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(16)

        heading = QHBoxLayout()
        heading.setSpacing(12)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(label('CUSTOMER WORKSPACE', 'CustomersKicker'))
        titles.addWidget(label('Customers', 'CustomersTitle'))
        titles.addWidget(label('Manage customers, service details and visit history.', 'CustomersSubtitle'))
        heading.addLayout(titles, 1)
        export_button = owner._button('Export CSV', owner.export_customers)
        export_button.setObjectName('CustomerExportButton')
        export_button.setProperty('role', 'accent')
        self.new_customer_button = owner._button('+  Add customer', owner.add_customer)
        self.new_customer_button.setObjectName('CustomerAddButton')
        self.new_customer_button.setProperty('role', 'primary')
        heading.addWidget(export_button)
        heading.addWidget(self.new_customer_button)
        layout.addLayout(heading)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName('CustomerSplitter')
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(14)
        directory = QWidget()
        directory.setObjectName('CustomerDirectory')
        directory.setMinimumWidth(250)
        directory.setMaximumWidth(390)
        left = QVBoxLayout(directory)
        left.setContentsMargins(15, 15, 15, 12)
        left.setSpacing(10)
        self.search = QLineEdit()
        self.search.setObjectName('CustomerSearch')
        self.search.setPlaceholderText('Search customers')
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName('Search customers')
        self.search.textChanged.connect(owner.refresh_customers)
        left.addWidget(self.search)
        self.search_hint = label('Name, suburb, phone…', 'CustomerSearchHint')
        left.addWidget(self.search_hint)
        directory_heading = QHBoxLayout()
        directory_heading.setSpacing(6)
        self.inactive = QCheckBox('Include inactive')
        self.inactive.toggled.connect(owner.refresh_customers)
        directory_heading.addWidget(self.inactive, 1)
        self.count = label('0 customers', 'CustomerDirectoryCount')
        self.count.setWordWrap(False)
        directory_heading.addWidget(self.count)
        left.addLayout(directory_heading)
        self.show_directory_details = False
        self.details_button = owner._button('More detail', self.toggle_directory_details)
        self.details_button.setProperty('role', 'link')
        self.details_button.setObjectName('CustomerDirectoryDetailsButton')
        self.details_button.setToolTip('Expand or collapse the details for every visible customer')
        left.addWidget(self.details_button, 0, Qt.AlignmentFlag.AlignRight)
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
        self.customer_table.setMouseTracking(True)
        self.customer_table.viewport().installEventFilter(self)
        self.splitter.splitterMoved.connect(lambda *_: self._schedule_directory_resize())
        self.customer_table.setAccessibleName('Customer directory')
        self.customer_table.itemSelectionChanged.connect(owner.show_selected_customer)
        self.customer_table.cellDoubleClicked.connect(lambda *_: owner.edit_customer())
        left.addWidget(self.customer_table, 1)
        self.splitter.addWidget(directory)

        self.stack = QStackedWidget()
        self.stack.setMinimumWidth(0)
        self.empty = label('Select a customer from the list to see their profile and jobs.', 'CustomerEmpty')
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.empty)
        self.workspace = QWidget()
        self.workspace.setObjectName('CustomerWorkspace')
        right = QVBoxLayout(self.workspace)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(14)

        self.overview_scroll = QScrollArea()
        self.overview_scroll.setObjectName('CustomerOverviewScroll')
        self.overview_scroll.setWidgetResizable(True)
        self.overview_scroll.setMinimumHeight(295)
        self.overview_scroll.setMaximumHeight(360)
        self.overview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        overview = QWidget()
        overview.setObjectName('CustomerProfileCard')
        card = QVBoxLayout(overview)
        card.setContentsMargins(22, 18, 22, 18)
        card.setSpacing(14)

        title = QHBoxLayout()
        title.setSpacing(12)
        title_left = QHBoxLayout()
        title_left.setSpacing(10)
        self.name = label('', 'CustomerName')
        self.name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_left.addWidget(self.name, 1)
        self.status = label('', 'CustomerStatus')
        self.status.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.status.setWordWrap(False)
        title_left.addWidget(self.status, 0, Qt.AlignmentFlag.AlignVCenter)
        title.addLayout(title_left, 1)
        self.activation_button = owner._button('Deactivate', owner.toggle_customer)
        self.activation_button.setObjectName('CustomerActivationButton')
        self.activation_button.setProperty('role', 'secondary')
        title.addWidget(self.activation_button)
        self.edit_customer_button = owner._button('Edit customer', owner.edit_customer)
        self.edit_customer_button.setObjectName('CustomerEditButton')
        title.addWidget(self.edit_customer_button)
        card.addLayout(title)

        # Address and contact stay readable and large.
        contact = QGridLayout()
        contact.setHorizontalSpacing(24)
        contact.setVerticalSpacing(3)
        contact.addWidget(label('SERVICE ADDRESS', 'CustomerInfoCaption'), 0, 0)
        contact.addWidget(label('CONTACT', 'CustomerInfoCaption'), 0, 1)
        self.profile = label()
        self.contact = label()
        contact.addWidget(self.profile, 1, 0)
        contact.addWidget(self.contact, 1, 1)
        contact.setColumnStretch(0, 1)
        contact.setColumnStretch(1, 1)
        card.addLayout(contact)

        self.quick_info_panel = QWidget()
        self.quick_info_panel.setObjectName('CustomerQuickInfo')
        info_grid = QGridLayout(self.quick_info_panel)
        info_grid.setContentsMargins(0, 0, 0, 0)
        info_grid.setHorizontalSpacing(10)
        info_grid.setVerticalSpacing(10)
        self.quick_info = {}
        for column, (key, caption, tone, kind) in enumerate((
            ('suburb', 'Suburb', 'teal', 'location'),
            ('frequency', 'Service frequency', 'teal', 'repeat'),
            ('payment', 'Usual payment method', 'teal', 'card'),
        )):
            tile = FactTile(caption, tone, kind)
            info_grid.addWidget(tile, 0, column)
            info_grid.setColumnStretch(column, 1)
            self.quick_info[key] = tile.value
        card.addWidget(self.quick_info_panel)

        divider = QFrame()
        self.profile_divider = divider
        divider.setObjectName('CustomerDivider')
        divider.setFixedHeight(1)
        card.addWidget(divider)

        self.summary_panel = QWidget()
        self.summary_panel.setObjectName('CustomerMetrics')
        summary = QGridLayout(self.summary_panel)
        summary.setContentsMargins(0, 0, 0, 0)
        summary.setHorizontalSpacing(12)
        summary.setVerticalSpacing(4)
        self.summary = {}
        for column, (key, caption, tone, kind) in enumerate((
            ('jobs_completed', 'Completed jobs', 'maroon', 'check'),
            ('last_job', 'Last completed', 'maroon', 'calendar'),
            ('next_due', 'Next due', 'coral', 'calendar'),
        )):
            tile = MetricTile(caption, tone, kind)
            summary.addWidget(tile, 0, column)
            summary.setColumnStretch(column, 1)
            self.summary[key] = tile.value
        card.addWidget(self.summary_panel)
        self.overview_scroll.setWidget(overview)
        right.addWidget(self.overview_scroll)

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setObjectName('CustomerDetailTabs')
        self.detail_tabs.setMinimumWidth(0)
        jobs = QWidget()
        jobs.setObjectName('CustomerDetailPage')
        job_layout = QVBoxLayout(jobs)
        job_layout.setContentsMargins(12, 15, 12, 10)
        job_layout.setSpacing(13)
        job_heading = QHBoxLayout()
        job_heading.setSpacing(10)
        self.job_heading_icon = GlyphIcon('calendar', 'maroon', 36)
        job_heading.addWidget(self.job_heading_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        self.job_history_title = label('Job history', 'CustomerJobHeading')
        self.job_history_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.job_history_title.setWordWrap(False)
        job_heading.addWidget(self.job_history_title)
        self.job_count = label('0 linked jobs', 'CustomerJobCount')
        self.job_count.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.job_count.setWordWrap(False)
        job_heading.addWidget(self.job_count)
        job_heading.addStretch()
        self.edit_job_button = owner._button('Edit selected job', self.edit_selected_job)
        self.edit_job_button.setObjectName('CustomerEditJobButton')
        job_heading.addWidget(self.edit_job_button)
        self.add_job_button = owner._button('Add job', lambda: owner.add_job(owner.selected_customer))
        self.add_job_button.setObjectName('CustomerAddJobButton')
        self.add_job_button.setProperty('role', 'primary')
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
        self.history.verticalHeader().setDefaultSectionSize(52)
        self.history.setMinimumHeight(135)
        self.history.setMinimumWidth(0)
        self.history.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.history.setShowGrid(False)
        self.history.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.history.cellDoubleClicked.connect(owner.edit_history_job)
        self.history.itemSelectionChanged.connect(self.update_job_action)
        job_layout.addWidget(self.history)
        job_layout.addStretch(1)
        self.detail_tabs.addTab(jobs, 'Jobs')

        from .customer_services import CustomerServices
        self.services = CustomerServices(owner)
        self.detail_tabs.addTab(self.services, 'Services')

        notes_page = QWidget()
        notes_page.setObjectName('CustomerDetailPage')
        notes_layout = QVBoxLayout(notes_page)
        notes_layout.setContentsMargins(13, 12, 13, 14)
        notes_layout.setSpacing(12)
        notes_heading = QHBoxLayout()
        notes_heading.addWidget(label('Customer notes', 'CustomerJobHeading'), 1)
        edit_notes = owner._button('Edit notes', owner.edit_customer)
        edit_notes.setObjectName('CustomerEditButton')
        notes_heading.addWidget(edit_notes)
        notes_layout.addLayout(notes_heading)
        notes_layout.addWidget(label('Customer instructions and background information.', 'CustomerDetailHelper'))
        notes_card = QFrame()
        notes_card.setObjectName('CustomerNotesCard')
        notes_card_layout = QVBoxLayout(notes_card)
        notes_card_layout.setContentsMargins(14, 12, 14, 12)
        self.notes = QTextEdit()
        self.notes.setObjectName('CustomerNotes')
        self.notes.setReadOnly(True)
        self.notes.setAccessibleName('Customer notes; edit through Edit customer')
        self.notes.setPlaceholderText('No notes for this customer yet.')
        notes_card_layout.addWidget(self.notes)
        notes_layout.addWidget(notes_card, 1)
        self.detail_tabs.addTab(notes_page, 'Notes')
        self.detail_tabs.currentChanged.connect(self._detail_tab_changed)
        details_card = QWidget()
        details_card.setObjectName('CustomerDetailsCard')
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(15, 10, 15, 12)
        details_layout.addWidget(self.detail_tabs)
        right.addWidget(details_card, 1)

        self.stack.addWidget(self.workspace)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([306, 930])
        layout.addWidget(self.splitter, 1)
        self.clear_customer()

    def _detail_tab_changed(self, index):
        compact = self.detail_tabs.widget(index) is not self.detail_tabs.widget(0)
        self.summary_panel.setVisible(not compact)
        self.quick_info_panel.setVisible(not compact)
        self.profile_divider.setVisible(not compact)
        self.overview_scroll.setMinimumHeight(175 if compact else 295)
        self.overview_scroll.setMaximumHeight(230 if compact else 360)

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
            item = QTableWidgetItem('\n'.join(lines))
            item.setData(Qt.ItemDataRole.UserRole, customer['id'])
            item.setData(DirectoryDelegate.DETAILS_ROLE,
                         self._directory_details(customer) if self.show_directory_details else [])
            # The old mouse tooltip repeated unrelated information in an unstyled
            # popup. Every expanded card now carries its own readable details.
            table.setItem(row, 0, item)
            if customer['id'] == selected:
                selected_row = row
        if selected_row is not None:
            table.selectRow(selected_row)
        table.blockSignals(False)
        self._resize_directory_rows()
        count = len(records)
        self.count.setText(f'{count} customer' + ('' if count == 1 else 's'))
        self.directory_empty.setVisible(not records)
        searching = bool(self.search.text().strip())
        self.directory_empty.setText('No matching customers. Try another search or include inactive customers.'
                                     if searching or self.inactive.isChecked() else
                                     'No active customers. Add a customer or include inactive customers.')

    def _directory_details(self, customer):
        """Build the same structured snapshot independently for every customer."""
        from ..models import work_description
        from decimal import Decimal, InvalidOperation

        contact = '\n'.join(str(customer.get(key)) for key in ('phone', 'email')
                            if customer.get(key)) or 'Not set'
        address = '\n'.join(str(customer.get(key)) for key in (
            'address_line_1', 'address_line_2', 'suburb') if customer.get(key))
        region = ' '.join(str(customer.get(key)) for key in ('state', 'postcode') if customer.get(key))
        if region:
            address = (address + '\n' if address else '') + region
        scope = work_description(customer.get('default_job_type') or [],
                                 customer.get('default_job_type_sides') or {}) or 'Not configured'
        fee = customer.get('default_fee')
        try:
            fee_text = f'${Decimal(str(fee)):,.2f}' if fee is not None and fee != '' else 'Fee not set'
        except (InvalidOperation, ValueError, TypeError):
            fee_text = str(fee) if fee else 'Fee not set'
        equipment = ', '.join(customer.get('default_equipment') or [])
        return [
            ('CONTACT', contact),
            ('ADDRESS', address or 'Not set'),
            ('SERVICE & FREQUENCY', self.owner.frequency_text(customer) + '\n' + scope),
            ('EQUIPMENT', equipment or 'Not configured'),
            ('PRICING & PAYMENT', fee_text + ' · ' + (customer.get('default_payment_type') or 'Not set')),
        ]

    def toggle_directory_details(self):
        self.show_directory_details = not self.show_directory_details
        self.details_button.setText('Less detail' if self.show_directory_details else 'More detail')
        # Refill EVERY directory item. Keep active filtering and selection.
        self.owner.refresh_customers()

    def _resize_directory_rows(self):
        if not hasattr(self, 'customer_table'):
            return
        self.customer_table.resizeRowsToContents()

    def _schedule_directory_resize(self):
        QTimer.singleShot(0, self._resize_directory_rows)

    def eventFilter(self, watched, event):
        if (hasattr(self, 'customer_table') and watched is self.customer_table.viewport()
                and event.type() == QEvent.Type.Resize):
            self._schedule_directory_resize()
        return super().eventFilter(watched, event)

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
        for value in self.quick_info.values():
            value.clear()
        for value in self.summary.values():
            value.clear()
        self.job_count.setText('0 linked jobs')
        self.notes.clear()
        self.history.clearSelection()
        self.history.setRowCount(0)
        for button in (self.edit_customer_button, self.add_job_button,
                       self.activation_button, self.edit_job_button):
            button.setEnabled(False)

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
        self.quick_info['suburb'].setText(customer['suburb'] or 'Not set')
        self.quick_info['frequency'].setText(self.owner.frequency_text(customer))
        self.quick_info['payment'].setText(customer['default_payment_type'] or 'Not set')
        self.summary['jobs_completed'].setText(str(summary['jobs_completed']))
        self.summary['last_job'].setText(self.date_text(summary['last_job']))
        self.summary['next_due'].setText(self.date_text(summary['next_due']))
        self.notes.setPlainText(customer['notes'] if 'notes' in enabled else '')
        self.notes.setPlaceholderText('No customer notes.' if 'notes' in enabled else 'Customer notes are disabled in Field settings.')
        self.activation_button.setText('Deactivate' if customer['active'] else 'Activate')
        self.edit_customer_button.setEnabled(True)
        self.activation_button.setEnabled(True)
        self.add_job_button.setEnabled(customer['active'])
        self.job_count.setText(f'{len(jobs)} linked job' + ('' if len(jobs) == 1 else 's'))
        self.owner._fill_table(self.history, jobs, 'jobs')
        for row in range(len(jobs)):
            self.history.setRowHeight(row, 52)
        header_height = self.history.horizontalHeader().height()
        self.history.setFixedHeight(max(135, min(8, len(jobs)) * 52 + header_height + 6))
        self.history.badge_columns = {index for index, field in enumerate(self.owner._columns('jobs'))
                                      if field.key in ('status', 'payment_status')}
        self.history.clearSelection()
        self.history_empty.setVisible(not jobs)
        self.history.setVisible(bool(jobs))
        self.update_job_action()

    def update_job_action(self):
        self.edit_job_button.setEnabled(bool(self.history.selectedItems()))

    def edit_selected_job(self):
        items = self.history.selectedItems()
        if items:
            self.owner._edit_job_id(items[0].data(Qt.ItemDataRole.UserRole))
