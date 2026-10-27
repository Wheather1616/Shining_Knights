"""Shining Knights home dashboard: focused schedule and customer actions."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ..models import work_description


def label(text: str = '', name: str = 'PageHelper', *, wrap: bool = False) -> QLabel:
    widget = QLabel(str(text))
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    widget.setMinimumWidth(0)
    return widget


def short_date(value: str) -> str:
    day = date.fromisoformat(value)
    return f'{day.day} {day.strftime("%b")}'


class MetricIcon(QWidget):
    COLOURS = {
        'maroon': ('#F8EAE8', '#52050A'),
        'teal': ('#E6F4F6', '#258EA6'),
        'coral': ('#FFF0EB', '#F87666'),
    }

    def __init__(self, kind: str, tone: str = 'maroon', parent=None):
        super().__init__(parent)
        self.kind = kind
        self.tone = tone
        self.setFixedSize(46, 46)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        bg, ink = self.COLOURS[self.tone]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawEllipse(QRectF(0, 0, 46, 46))
        pen = QPen(QColor(ink), 2.1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind == 'alert':
            painter.drawEllipse(QRectF(14, 12, 18, 18))
            painter.drawLine(23, 17, 23, 23)
            painter.drawPoint(23, 26)
        elif self.kind == 'spark':
            path = QPainterPath()
            path.moveTo(23, 11)
            path.lineTo(26, 20)
            path.lineTo(35, 23)
            path.lineTo(26, 26)
            path.lineTo(23, 35)
            path.lineTo(20, 26)
            path.lineTo(11, 23)
            path.lineTo(20, 20)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawRoundedRect(QRectF(13, 15, 20, 18), 3, 3)
            painter.drawLine(13, 21, 33, 21)
            painter.drawLine(19, 12, 19, 17)
            painter.drawLine(27, 12, 27, 17)
            painter.drawPoint(19, 26)
            painter.drawPoint(26, 26)
        painter.end()


class SummaryCard(QPushButton):
    def __init__(self, title: str, hint: str, kind: str, tone: str, handler):
        super().__init__()
        self.title = title
        self.setObjectName('HomeSummaryCard')
        self.setProperty('tone', tone)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(132)

        contents = QHBoxLayout(self)
        contents.setContentsMargins(20, 16, 18, 16)
        contents.setSpacing(14)
        contents.addWidget(MetricIcon(kind, tone), 0, Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.setContentsMargins(0, 2, 0, 0)
        heading = label(title, 'HomeSummaryTitle')
        heading.setWordWrap(True)
        self.count = label('0', 'HomeSummaryCount')
        self.hint = label(hint, 'HomeSummaryHint', wrap=True)
        for child in (heading, self.count, self.hint):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            text_col.addWidget(child)
        text_col.addStretch(1)
        contents.addLayout(text_col, 1)
        arrow = label('›', 'HomeMetricArrow')
        arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        contents.addWidget(arrow, 0, Qt.AlignmentFlag.AlignTop)
        self.clicked.connect(handler)

    def set_count(self, count: int):
        self.count.setText(str(count))
        self.setAccessibleName(f'{self.title}: {count}. Activate to view.')


class HomePage(QWidget):
    MAX_VISITS = 5
    MAX_BOOKINGS = 4

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setObjectName('HomePage')
        self.overview = None
        self.show_all_bookings = False
        self._shown_jobs = []
        self._selected_job_id = None
        self._compact_mode = None

        self.backup_label = label('Backup status is available in Settings.', 'HomeHiddenBackup')
        self.backup_label.setParent(self)
        self.backup_label.hide()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.page_scroll = QScrollArea()
        self.page_scroll.setObjectName('HomePageScroll')
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(self.page_scroll)

        content = QWidget()
        content.setObjectName('HomeDashboardContent')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 30)
        layout.setSpacing(18)
        self.page_scroll.setWidget(content)

        heading = QHBoxLayout()
        heading.setSpacing(16)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title_stack.addWidget(label('YOUR WORKSPACE', 'HomeEyebrow'))
        title_stack.addWidget(label('Dashboard', 'HomeTitle'))
        self.date_label = label('', 'HomeDate')
        title_stack.addWidget(self.date_label)
        heading.addLayout(title_stack, 1)
        self.add_customer_button = owner._button('Add customer', owner.add_customer)
        self.add_customer_button.setProperty('role', 'secondary')
        self.add_job_button = owner._button('New job', owner.add_job)
        self.add_job_button.setProperty('role', 'primary')
        heading.addWidget(self.add_customer_button)
        heading.addWidget(self.add_job_button)
        layout.addLayout(heading)

        summaries = QHBoxLayout()
        summaries.setSpacing(14)
        self.today_card = SummaryCard("Today's jobs", 'Open visits today', 'calendar', 'maroon',
                                      lambda: owner.open_home_jobs('today'))
        self.next7_card = SummaryCard('Next 7 days', 'Including today', 'calendar', 'teal',
                                      lambda: owner.open_home_jobs('next7'))
        self.booking_card = SummaryCard('Needs scheduling', 'Due soon or overdue', 'alert', 'coral',
                                        self.view_all_bookings)
        for card in (self.today_card, self.next7_card, self.booking_card):
            summaries.addWidget(card, 1)
        layout.addLayout(summaries)

        self.overdue_notice = QWidget()
        self.overdue_notice.setObjectName('HomeOverdueNotice')
        notice = QHBoxLayout(self.overdue_notice)
        notice.setContentsMargins(14, 9, 14, 9)
        notice.setSpacing(10)
        self.overdue_label = label('', 'HomeOverdueText', wrap=True)
        notice.addWidget(self.overdue_label, 1)
        notice.addWidget(self._link('Review jobs  →', lambda: owner.open_home_jobs('overdue')))
        layout.addWidget(self.overdue_notice)
        self.overdue_notice.hide()

        self.body_grid = QGridLayout()
        self.body_grid.setHorizontalSpacing(16)
        self.body_grid.setVerticalSpacing(16)

        self.visits_card, visits = self._card()
        header = QHBoxLayout()
        header.addWidget(label('Upcoming jobs', 'HomeSectionTitle'), 1)
        header.addWidget(self._link('View all jobs  →', lambda: owner.open_home_jobs('all')))
        visits.addLayout(header)
        self.visits_empty = label('No upcoming jobs in the next seven days.', 'HomeEmpty', wrap=True)
        visits.addWidget(self.visits_empty)
        self.visits_table = QTableWidget(0, 4)
        self.visits_table.setObjectName('HomeVisits')
        self.visits_table.setAccessibleName('Upcoming jobs. Select a row to preview its details. Double-click to open.')
        self.visits_table.setHorizontalHeaderLabels(['When', 'Customer', 'Suburb', 'Service'])
        self.visits_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.visits_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.visits_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.visits_table.setShowGrid(False)
        self.visits_table.setAlternatingRowColors(False)
        self.visits_table.setWordWrap(False)
        self.visits_table.verticalHeader().hide()
        self.visits_table.verticalHeader().setDefaultSectionSize(53)
        self.visits_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.visits_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.visits_table.setColumnWidth(0, 106)
        self.visits_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.visits_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.visits_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.visits_table.setFixedHeight(90)
        self.visits_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.visits_table.itemSelectionChanged.connect(self._visit_selection_changed)
        self.visits_table.cellDoubleClicked.connect(self.open_visit)
        self.visits_table.itemActivated.connect(lambda item: self.open_visit(item.row(), item.column()))
        visits.addWidget(self.visits_table)
        self.visits_hint = label('', 'HomeFootnote', wrap=True)
        visits.addWidget(self.visits_hint)

        self.details_card, details = self._card()
        detail_header = QHBoxLayout()
        detail_header.addWidget(label('Job details', 'HomeSectionTitle'), 1)
        self.edit_job_button = owner._button('Edit job', self._edit_selected_job)
        self.edit_job_button.setProperty('role', 'secondary')
        detail_header.addWidget(self.edit_job_button)
        details.addLayout(detail_header)
        self.details_empty = label('Select an upcoming job to see its details.', 'HomeEmpty', wrap=True)
        details.addWidget(self.details_empty)
        self.details_content = QWidget()
        self.details_content.setObjectName('HomeDetailsContent')
        detail_body = QHBoxLayout(self.details_content)
        detail_body.setContentsMargins(0, 6, 0, 3)
        detail_body.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(7)
        self.detail_name = label('', 'HomeDetailName', wrap=True)
        self.detail_date = label('', 'HomeDetailLine', wrap=True)
        self.detail_suburb = label('', 'HomeDetailLine', wrap=True)
        self.detail_service = label('', 'HomeDetailLine', wrap=True)
        left.addWidget(self.detail_name)
        left.addWidget(self.detail_date)
        left.addWidget(self.detail_suburb)
        left.addWidget(self.detail_service)
        left.addStretch()
        detail_body.addLayout(left, 3)
        separator = QFrame()
        separator.setObjectName('HomeDetailDivider')
        separator.setFrameShape(QFrame.Shape.VLine)
        detail_body.addWidget(separator)
        note_col = QVBoxLayout()
        note_col.setSpacing(7)
        note_col.addWidget(label('VISIT NOTES', 'HomeDetailCaption'))
        self.detail_notes = label('', 'HomeDetailNotes', wrap=True)
        self.detail_notes.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        note_col.addWidget(self.detail_notes)
        note_col.addStretch()
        self.open_job_button = self._link('Open full job  →', self._open_selected_job)
        note_col.addWidget(self.open_job_button, 0, Qt.AlignmentFlag.AlignLeft)
        detail_body.addLayout(note_col, 2)
        details.addWidget(self.details_content)
        self.details_content.hide()
        self.edit_job_button.setEnabled(False)

        self.bookings_card, bookings = self._card()
        booking_header = QHBoxLayout()
        booking_header.addWidget(label('Needs scheduling', 'HomeSectionTitle'), 1)
        self.booking_list_button = self._link('View all  →', self.toggle_bookings)
        booking_header.addWidget(self.booking_list_button)
        bookings.addLayout(booking_header)
        self.bookings_scroll = QScrollArea()
        self.bookings_scroll.setObjectName('HomeBookingsScroll')
        self.bookings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.bookings_scroll.setWidgetResizable(True)
        self.bookings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bookings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bookings_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.bookings_scroll.setFixedHeight(96)
        bookings.addWidget(self.bookings_scroll)

        self.actions_card, actions = self._card()
        actions.addWidget(label('Quick actions', 'HomeSectionTitle'))
        actions.addWidget(self._action('Add customer', owner.add_customer, 'teal'))
        actions.addWidget(self._action('Backups & help', owner.open_backup_settings, 'neutral'))

        self._reflow(self.width())
        layout.addLayout(self.body_grid)
        layout.addStretch(1)

    @staticmethod
    def _card():
        widget = QWidget()
        widget.setObjectName('HomeContentCard')
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(13)
        return widget, layout

    def _link(self, caption, handler):
        button = self.owner._button(caption.replace('&', '&&'), handler)
        button.setProperty('role', 'link')
        button.setAccessibleName(caption.replace('→', '').strip())
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _action(self, caption, handler, tone):
        button = self.owner._button(caption.replace('&', '&&') + '    ›', handler)
        button.setObjectName('HomeQuickAction')
        button.setProperty('tone', tone)
        button.setAccessibleName(caption)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _reflow(self, width):
        compact = width < 1060
        if compact == self._compact_mode:
            return
        self._compact_mode = compact
        for widget in (self.visits_card, self.details_card, self.bookings_card, self.actions_card):
            self.body_grid.removeWidget(widget)
        if compact:
            for row, widget in enumerate((self.visits_card, self.details_card,
                                          self.bookings_card, self.actions_card)):
                self.body_grid.addWidget(widget, row, 0)
            self.body_grid.setColumnStretch(0, 1)
            self.body_grid.setColumnStretch(1, 0)
        else:
            self.body_grid.addWidget(self.visits_card, 0, 0)
            self.body_grid.addWidget(self.bookings_card, 0, 1)
            self.body_grid.addWidget(self.details_card, 1, 0)
            self.body_grid.addWidget(self.actions_card, 1, 1)
            self.body_grid.setColumnStretch(0, 2)
            self.body_grid.setColumnStretch(1, 1)
        self.body_grid.invalidate()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'body_grid'):
            self._reflow(event.size().width())

    def set_overview(self, overview):
        self.overview = overview
        day = date.fromisoformat(overview['as_of'])
        self.date_label.setText(f'{day.strftime("%A")}, {day.day} {day.strftime("%B %Y")}')
        self.today_card.set_count(overview['today_jobs'])
        self.next7_card.set_count(overview['next7_jobs'])
        self.booking_card.set_count(len(overview['needs_booking']))
        overdue = overview['overdue_jobs']
        self.overdue_notice.setVisible(bool(overdue))
        self.overdue_label.setText(f'{overdue} past visit' + ('' if overdue == 1 else 's') +
                                   ' still open. Review or reschedule.')
        self._shown_jobs = list(overview['upcoming'][:self.MAX_VISITS])
        self.visits_empty.setVisible(not self._shown_jobs)
        self.visits_table.setVisible(bool(self._shown_jobs))
        self.visits_table.blockSignals(True)
        self.visits_table.setRowCount(len(self._shown_jobs))
        self.visits_table.setFixedHeight(42 + max(1, len(self._shown_jobs)) * 53 + 4)
        selection = 0
        for row, job in enumerate(self._shown_jobs):
            if job['id'] == self._selected_job_id:
                selection = row
            scheduled = job['scheduled_date']
            when = 'Today' if scheduled == overview['as_of'] else (
                date.fromisoformat(scheduled).strftime('%a ') + short_date(scheduled))
            values = (when, job.get('customer_name') or 'Unnamed customer',
                      job.get('suburb') or 'Not recorded', self._service(job))
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, job['id'])
                item.setToolTip(str(value))
                self.visits_table.setItem(row, col, item)
        if self._shown_jobs:
            self.visits_table.selectRow(selection)
        self.visits_table.blockSignals(False)
        self._visit_selection_changed()
        count = len(overview['upcoming'])
        self.visits_hint.setText(f'Showing {self.MAX_VISITS} of {count} jobs. View all for the complete schedule.'
                                 if count > self.MAX_VISITS else '')
        self.visits_hint.setVisible(count > self.MAX_VISITS)
        self._render_bookings()

    @staticmethod
    def _service(job):
        return (job.get('service_name') or
                work_description(job.get('job_type') or [], job.get('job_type_sides') or {}) or
                'Service not specified')

    def _visit_selection_changed(self):
        row = self.visits_table.currentRow()
        if not (0 <= row < len(self._shown_jobs)):
            self._selected_job_id = None
            self.details_empty.show()
            self.details_content.hide()
            self.edit_job_button.setEnabled(False)
            return
        job = self._shown_jobs[row]
        self._selected_job_id = job['id']
        self.details_empty.hide()
        self.details_content.show()
        self.edit_job_button.setEnabled(True)
        self.detail_name.setText(job.get('customer_name') or 'Unnamed customer')
        self.detail_date.setText('Scheduled  ·  ' + date.fromisoformat(job['scheduled_date']).strftime('%a %d %b %Y'))
        self.detail_suburb.setText('Location  ·  ' + (job.get('suburb') or 'Suburb not set'))
        self.detail_service.setText('Service  ·  ' + self._service(job))
        try:
            full_job = self.owner.db.get_job(job['id'])
        except (LookupError, ValueError, KeyError):
            full_job = None
        notes = (full_job or job).get('notes') or ''
        self.detail_notes.setText(notes.strip() or 'No notes saved for this visit.')

    def _open_selected_job(self):
        if self._selected_job_id is not None:
            self.owner.open_home_jobs('all', self._selected_job_id)

    def _edit_selected_job(self):
        if self._selected_job_id is not None:
            self.owner._edit_job_id(self._selected_job_id)

    def open_visit(self, row, _column):
        if 0 <= row < len(self._shown_jobs):
            self.owner.open_home_jobs('all', self._shown_jobs[row]['id'])

    def view_all_bookings(self):
        self.show_all_bookings = True
        self._render_bookings()
        self.bookings_scroll.verticalScrollBar().setValue(0)
        self.bookings_scroll.setFocus()

    def toggle_bookings(self):
        self.show_all_bookings = not self.show_all_bookings
        self._render_bookings()

    def _render_bookings(self):
        if self.overview is None:
            return
        rows = self.overview['needs_booking']
        displayed = rows if self.show_all_bookings else rows[:self.MAX_BOOKINGS]
        content = QWidget()
        content.setObjectName('HomeBookingContent')
        container = QVBoxLayout(content)
        container.setContentsMargins(0, 0, 2, 0)
        container.setSpacing(0)
        self.booking_buttons = {}
        self.customer_buttons = {}
        if not rows:
            container.addWidget(label('Everything is scheduled. No customers need attention.',
                                      'HomeEmpty', wrap=True))
        for index, customer in enumerate(displayed):
            entry = QWidget()
            entry.setObjectName('HomeBookingEntry')
            box = QVBoxLayout(entry)
            box.setContentsMargins(0, 10, 0, 10)
            box.setSpacing(6)
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            identity = QVBoxLayout()
            identity.setSpacing(3)
            name = self._link(customer['name'],
                              lambda _=False, cid=customer['id']: self.owner.open_home_customer(cid))
            name.setObjectName('HomeCustomerLink')
            name.setAccessibleName('View customer: ' + customer['name'])
            identity.addWidget(name)
            identity.addWidget(label(customer.get('suburb') or 'No suburb recorded', 'HomeBookingSuburb'))
            row_layout.addLayout(identity, 1)
            schedule = self.owner._button('Schedule',
                                          lambda _=False, cid=customer['id']: self.owner.add_job(cid))
            schedule.setProperty('role', 'primary')
            schedule.setAccessibleName('Schedule a job for ' + customer['name'])
            row_layout.addWidget(schedule, 0, Qt.AlignmentFlag.AlignVCenter)
            box.addLayout(row_layout)
            due_date = customer.get('next_due')
            if due_date:
                overdue = due_date < self.overview['as_of']
                badge = label(('Overdue · ' if overdue else 'Due ') + short_date(due_date), 'HomeDueBadge')
                badge.setProperty('overdue', overdue)
                badge.setToolTip(date.fromisoformat(due_date).strftime('%d %B %Y'))
                box.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
            self.customer_buttons[customer['id']] = name
            self.booking_buttons[customer['id']] = schedule
            container.addWidget(entry)
            if index < len(displayed) - 1:
                rule = QFrame()
                rule.setObjectName('HomeBookingDivider')
                rule.setFixedHeight(1)
                container.addWidget(rule)
        container.addStretch(1)
        self.bookings_scroll.setWidget(content)
        height = 64 if not rows else 10 + min(len(displayed), 4) * 98
        self.bookings_scroll.setFixedHeight(min(410, height))
        self.booking_list_button.setVisible(len(rows) > self.MAX_BOOKINGS)
        self.booking_list_button.setText('Show first 4  →' if self.show_all_bookings else f'View all {len(rows)}  →')
