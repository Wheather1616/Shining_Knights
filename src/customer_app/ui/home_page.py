"""A quiet, actionable overview of visits and customers needing a booking."""
from datetime import date

from ..models import work_description

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)


def label(text, name):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    return widget


def short_date(value):
    day = date.fromisoformat(value)
    return f'{day.day} ' + day.strftime('%b')


class SummaryCard(QPushButton):
    def __init__(self, title, hint, handler):
        super().__init__()
        self.setObjectName('HomeSummaryCard')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(154)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(2)
        self.title = title
        self.count = label('0', 'HomeSummaryCount')
        self.count.ensurePolished()
        self.count.setMinimumHeight(self.count.fontMetrics().height())
        for widget in (label(title, 'HomeSummaryTitle'), self.count, label(hint, 'PageHelper')):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(widget)
        self.clicked.connect(handler)

    def set_count(self, count):
        self.count.setText(str(count))
        self.setAccessibleName(f'{self.title}: {count}. Open list.')


class HomePage(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setObjectName('HomePage')
        self.overview = None
        self.show_all_bookings = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 16)
        layout.setSpacing(16)
        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(label('Overview', 'HomeTitle'))
        self.date_label = label('', 'PageHelper')
        titles.addWidget(self.date_label)
        heading.addLayout(titles, 1)
        self.add_customer_button = owner._button('Add customer', owner.add_customer)
        self.add_customer_button.setProperty('role', 'secondary')
        self.add_job_button = owner._button('Add job', owner.add_job)
        heading.addWidget(self.add_customer_button)
        heading.addWidget(self.add_job_button)
        layout.addLayout(heading)
        summaries = QHBoxLayout()
        summaries.setSpacing(16)
        self.today_card = SummaryCard("Today's jobs", 'Open visits scheduled today', lambda: owner.open_home_jobs('today'))
        self.next7_card = SummaryCard('Next 7 days', 'Including today', lambda: owner.open_home_jobs('next7'))
        self.booking_card = SummaryCard('Needs a booking', 'Due soon or overdue', self.view_all_bookings)
        for card in (self.today_card, self.next7_card, self.booking_card):
            summaries.addWidget(card, 1)
        layout.addLayout(summaries)

        self.overdue_notice = QWidget()
        self.overdue_notice.setObjectName('HomeOverdueNotice')
        notice = QHBoxLayout(self.overdue_notice)
        notice.setContentsMargins(12, 6, 12, 6)
        self.overdue_label = label('', 'HomeOverdueText')
        notice.addWidget(self.overdue_label, 1)
        notice.addWidget(self._link('Review jobs', lambda: owner.open_home_jobs('overdue')))
        layout.addWidget(self.overdue_notice)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.visits_card = QWidget()
        self.visits_card.setObjectName('HomeContentCard')
        self.visits_card.setMinimumWidth(400)
        visits = QVBoxLayout(self.visits_card)
        visits.setContentsMargins(18, 16, 18, 12)
        visits.setSpacing(10)
        caption = QHBoxLayout()
        caption.addWidget(label('Upcoming visits', 'HomeSectionTitle'), 1)
        caption.addWidget(self._link('View all jobs', lambda: owner.open_home_jobs('all')))
        visits.addLayout(caption)
        self.visits_empty = label('No visits booked for the next seven days.', 'HomeEmpty')
        visits.addWidget(self.visits_empty)
        self.visits_table = QTableWidget(0, 4)
        self.visits_table.setObjectName('HomeVisits')
        self.visits_table.setAccessibleName('Upcoming visits. Select a visit to open its job details.')
        self.visits_table.setHorizontalHeaderLabels(['When', 'Customer', 'Suburb', 'Service'])
        self.visits_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.visits_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.visits_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.visits_table.setShowGrid(False)
        self.visits_table.setWordWrap(False)
        self.visits_table.verticalHeader().hide()
        self.visits_table.verticalHeader().setDefaultSectionSize(48)
        self.visits_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.visits_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.visits_table.setColumnWidth(0, 88)
        self.visits_table.setMinimumHeight(100)
        self.visits_table.cellClicked.connect(self.open_visit)
        self.visits_table.itemActivated.connect(lambda item: self.open_visit(item.row(), item.column()))
        visits.addWidget(self.visits_table, 1)
        self.visits_hint = label('', 'PageHelper')
        visits.addWidget(self.visits_hint)
        body.addWidget(self.visits_card, 2)

        self.bookings_card = QWidget()
        self.bookings_card.setObjectName('HomeContentCard')
        self.bookings_card.setMinimumWidth(280)
        bookings = QVBoxLayout(self.bookings_card)
        bookings.setContentsMargins(18, 16, 18, 12)
        bookings.setSpacing(10)
        bookings.addWidget(label('Needs a booking', 'HomeSectionTitle'))
        bookings.addWidget(label('No upcoming visit booked.', 'PageHelper'))
        self.bookings_scroll = QScrollArea()
        self.bookings_scroll.setObjectName('HomeBookingsScroll')
        self.bookings_scroll.setWidgetResizable(True)
        self.bookings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bookings.addWidget(self.bookings_scroll, 1)
        self.booking_list_button = self._link('View all', self.toggle_bookings)
        bookings.addWidget(self.booking_list_button, 0, Qt.AlignmentFlag.AlignLeft)
        body.addWidget(self.bookings_card, 1)
        layout.addLayout(body, 1)

        footer = QWidget()
        footer.setObjectName('HomeFooter')
        bottom = QHBoxLayout(footer)
        bottom.setContentsMargins(0, 10, 0, 0)
        self.backup_label = label('No backup yet. Manage backups in Settings.', 'PageHelper')
        bottom.addWidget(self.backup_label, 1)
        bottom.addWidget(self._link('Backups & help', owner.open_backup_settings))
        layout.addWidget(footer)

    def _link(self, caption, handler):
        button = self.owner._button(caption.replace('&', '&&'), handler)
        button.setAccessibleName(caption)
        button.setProperty('role', 'link')
        return button

    def set_overview(self, overview):
        self.overview = overview
        day = date.fromisoformat(overview['as_of'])
        self.date_label.setText(day.strftime('%A') + f', {day.day} ' + day.strftime('%B %Y'))
        self.today_card.set_count(overview['today_jobs'])
        self.next7_card.set_count(overview['next7_jobs'])
        self.booking_card.set_count(len(overview['needs_booking']))
        overdue = overview['overdue_jobs']
        self.overdue_notice.setVisible(bool(overdue))
        self.overdue_label.setText(f'{overdue} past visit' + ('' if overdue == 1 else 's') + ' still open. Review or reschedule.')
        rows = overview['upcoming'][:5]
        self.visits_empty.setVisible(not rows)
        self.visits_table.setVisible(bool(rows))
        self.visits_table.setRowCount(len(rows))
        for row, job in enumerate(rows):
            when = 'Today' if job['scheduled_date'] == overview['as_of'] else date.fromisoformat(job['scheduled_date']).strftime('%a ') + short_date(job['scheduled_date'])
            for col, value in enumerate((when, job['customer_name'], job['suburb'], job.get('service_name') or work_description(job['job_type'], job['job_type_sides']) or 'Not recorded')):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, job['id'])
                item.setToolTip(value)
                self.visits_table.setItem(row, col, item)
        self.visits_hint.setText((f'Showing 5 of {len(overview["upcoming"])} visits. ' if len(overview['upcoming']) > 5 else '') + 'Select a visit to open its job details.' if rows else 'Use Add job to plan your next visit.')
        self._render_bookings()

    def open_visit(self, row, _column):
        self.owner.open_home_jobs('all', self.visits_table.item(row, 0).data(Qt.ItemDataRole.UserRole))

    def view_all_bookings(self):
        self.show_all_bookings = True
        self._render_bookings()
        self.bookings_scroll.verticalScrollBar().setValue(0)
        self.bookings_scroll.setFocus()

    def toggle_bookings(self):
        self.show_all_bookings = not self.show_all_bookings
        self._render_bookings()

    def _render_bookings(self):
        rows = self.overview['needs_booking']
        content = QWidget()
        content.setObjectName('HomeBookingContent')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(0)
        self.booking_buttons = {}
        self.customer_buttons = {}
        if not rows:
            layout.addWidget(label('No customers need booking.\nYou’re up to date.', 'HomeEmpty'))
        for customer in rows if self.show_all_bookings else rows[:5]:
            entry = QWidget()
            entry.setObjectName('HomeBookingEntry')
            entry_layout = QVBoxLayout(entry)
            entry_layout.setContentsMargins(0, 12, 0, 12)
            entry_layout.setSpacing(4)
            name = self._link(customer['name'], lambda _=False, cid=customer['id']: self.owner.open_home_customer(cid))
            name.setObjectName('HomeCustomerLink')
            name.setToolTip(customer['name'])
            name.setAccessibleName('View customer: ' + customer['name'])
            name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            entry_layout.addWidget(name)
            line = QHBoxLayout()
            details = QVBoxLayout()
            details.setSpacing(4)
            details.addWidget(label(customer['suburb'] or 'No suburb recorded', 'PageHelper'))
            overdue = customer['next_due'] < self.overview['as_of']
            due = label(('Overdue · ' if overdue else 'Due ') + short_date(customer['next_due']), 'HomeDueBadge')
            due.setProperty('overdue', overdue)
            due.setToolTip(date.fromisoformat(customer['next_due']).strftime('%d %B %Y'))
            details.addWidget(due, 0, Qt.AlignmentFlag.AlignLeft)
            line.addLayout(details, 1)
            button = self.owner._button('Add job', lambda _=False, cid=customer['id']: self.owner.add_job(cid))
            button.setProperty('role', 'secondary')
            button.setAccessibleName('Add job for ' + customer['name'])
            line.addWidget(button)
            entry_layout.addLayout(line)
            self.booking_buttons[customer['id']] = button
            self.customer_buttons[customer['id']] = name
            layout.addWidget(entry)
        layout.addStretch()
        self.bookings_scroll.setWidget(content)
        self.booking_list_button.setVisible(len(rows) > 5)
        self.booking_list_button.setText('Show first 5' if self.show_all_bookings else f'View all {len(rows)} customers')
