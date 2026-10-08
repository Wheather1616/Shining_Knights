"""Small native input controls that keep scrolling from changing saved choices."""
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QDate, QRegularExpression, Qt
from PySide6.QtGui import QIcon, QRegularExpressionValidator
from PySide6.QtWidgets import (QCalendarWidget, QCheckBox, QComboBox, QFrame,
    QButtonGroup, QPushButton, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QSpinBox, QVBoxLayout, QWidget)


class ClickComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()  # The containing form scrolls; the current choice stays put.


class IntervalSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class NumericInput(QLineEdit):
    def __init__(self, pattern, value='', parent=None):
        super().__init__(parent)
        self.setValidator(QRegularExpressionValidator(QRegularExpression(pattern), self))
        self.setText(str(value) if value is not None else '')


class DateInput(QLineEdit):
    """An optional, editable date with a native calendar and a genuine blank value."""
    def __init__(self, value='', parent=None):
        super().__init__(parent)
        self.setPlaceholderText('dd/mm/yyyy, or leave blank')
        self.setClearButtonEnabled(True)
        self.setAccessibleDescription('Type a date or use the calendar button. Alt+Down opens the calendar.')
        self.setText(value or '')
        if value:
            try:
                self.setText(date.fromisoformat(value).strftime('%d/%m/%Y'))
            except ValueError:
                pass
        arrow = Path(__file__).resolve().parents[1] / 'assets/theme/chevron-down.svg'
        self.calendar_action = self.addAction(QIcon(str(arrow)), QLineEdit.ActionPosition.TrailingPosition)
        self.calendar_action.setText('Choose date')
        self.calendar_action.setToolTip('Choose a date from the calendar')
        self.calendar_action.triggered.connect(self.show_calendar)
        self.popup = QFrame(self, Qt.WindowType.Popup)
        self.popup.setObjectName('FormCalendarPopup')
        layout = QVBoxLayout(self.popup)
        layout.setContentsMargins(8, 8, 8, 8)
        self.calendar = QCalendarWidget(self.popup)
        self.calendar.setObjectName('FormCalendar')
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setMinimumSize(340, 270)
        self.calendar.setMinimumDate(QDate(1, 1, 1))
        layout.addWidget(self.calendar)
        self.calendar.clicked.connect(self._choose)
        self.calendar.activated.connect(self._choose)

    def show_calendar(self):
        chosen = date.today()
        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                chosen = datetime.strptime(self.text(), fmt).date()
                break
            except ValueError:
                pass
        self.calendar.setSelectedDate(QDate(chosen.year, chosen.month, chosen.day))
        self.popup.adjustSize()
        position = self.mapToGlobal(self.rect().bottomLeft())
        available = self.screen().availableGeometry()
        position.setX(max(available.left(), min(position.x(), available.right() - self.popup.width())))
        if position.y() + self.popup.height() > available.bottom():
            position.setY(self.mapToGlobal(self.rect().topLeft()).y() - self.popup.height())
        self.popup.move(position)
        self.popup.show()
        self.calendar.setFocus()

    def _choose(self, chosen):
        self.setText(chosen.toString('dd/MM/yyyy'))
        self.popup.hide()
        self.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Down and event.modifiers() & Qt.KeyboardModifier.AltModifier:
            self.show_calendar()
            event.accept()
        else:
            super().keyPressEvent(event)


class ChoiceLabel(QLabel):
    def __init__(self, text, checkbox):
        super().__init__(text)
        self.checkbox = checkbox
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
            event.accept()
        else:
            super().mousePressEvent(event)


class ChoiceGrid(QWidget):
    """All equipment choices in a wrapping grid, without an inner scroll area."""
    def __init__(self, options, selected=(), parent=None, *, empty_text="No equipment choices. Add them in Settings."):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 2, 0, 2)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(10)
        self.checkboxes = {}
        self.entries = []
        self._columns = 0
        for option in dict.fromkeys([*options, *selected]):
            checkbox = QCheckBox()
            checkbox.setChecked(option in selected)
            checkbox.setAccessibleName(option)
            checkbox.setToolTip(option)
            entry = QWidget()
            row = QHBoxLayout(entry)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            row.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(ChoiceLabel(option, checkbox), 1)
            self.entries.append(entry)
            self.checkboxes[option] = checkbox
        self.empty_label = QLabel(empty_text) if not self.entries else None
        self._reflow(2)

    def _reflow(self, columns):
        if columns == self._columns:
            return
        for column in range(max(columns, self._columns)):
            self.grid.setColumnStretch(column, 0)
        while self.grid.count():
            self.grid.takeAt(0)
        for i, entry in enumerate(self.entries):
            self.grid.addWidget(entry, i // columns, i % columns)
        if self.empty_label is not None:
            self.grid.addWidget(self.empty_label, 0, 0, 1, columns)
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)
        self._columns = columns
        self.updateGeometry()

    def resizeEvent(self, event):
        self._reflow(3 if self.width() >= 660 else 2 if self.width() >= 340 else 1)
        super().resizeEvent(event)

    def selected_values(self):
        return [option for option, checkbox in self.checkboxes.items() if checkbox.isChecked()]


class WorkTypeGrid(ChoiceGrid):
    """Tick work types, then choose the side beneath each selected type."""
    def __init__(self, options, selected=(), sides=None, parent=None, **kwargs):
        super().__init__(options, selected, parent, **kwargs)
        self.side_buttons = {}
        self.side_frames = {}
        self.side_groups = {}
        for option, entry in zip(self.checkboxes, self.entries):
            checkbox = self.checkboxes[option]
            row = entry.layout()
            # Retain the existing label/tick row, with its side control below.
            heading = QWidget()
            heading.setLayout(row)
            column = QVBoxLayout(entry)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(6)
            column.addWidget(heading)
            below = QHBoxLayout()
            below.setContentsMargins(0, 0, 0, 0)
            below.addSpacing(26)
            frame = QFrame()
            frame.setObjectName('WorkSideSelector')
            frame.setAccessibleName(f'{option}: inside, outside or both')
            segments = QHBoxLayout(frame)
            segments.setContentsMargins(3, 3, 3, 3)
            segments.setSpacing(2)
            group = QButtonGroup(frame)
            group.setExclusive(True)
            buttons = {}
            for side, caption in [('inside', 'Inside'), ('outside', 'Outside'), ('both', 'Both')]:
                button = QPushButton(caption)
                button.setProperty('role', 'workSide')
                button.setCheckable(True)
                button.setAutoDefault(False)
                button.setMinimumWidth(0)
                button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                button.setAccessibleName(f'{option}: {caption}')
                group.addButton(button)
                segments.addWidget(button, 1)
                buttons[side] = button
            below.addWidget(frame, 1)
            column.addLayout(below)
            column.addStretch()
            frame.setVisible(checkbox.isChecked())
            checkbox.toggled.connect(frame.setVisible)
            self.side_buttons[option] = buttons
            self.side_frames[option] = frame
            self.side_groups[option] = group
        self.set_sides(sides or {})

    def set_sides(self, sides):
        # Replacing a selected service must also clear the previous side choices.
        for option, group in self.side_groups.items():
            group.setExclusive(False)
            for side, button in self.side_buttons[option].items():
                button.setChecked(sides.get(option) == side)
            group.setExclusive(True)

    def selected_sides(self):
        return {option: side for option in self.selected_values()
                for side, button in self.side_buttons[option].items() if button.isChecked()}
