"""Small native input controls that keep scrolling from changing saved choices."""
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QDate, QRegularExpression, Qt, Signal
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


class SearchCustomerCombo(ClickComboBox):
    """Explicit, searchable picker. Typing never silently chooses a customer.

    Completing or clicking a matching result confirms an actual ID. An empty
    picker has an empty line edit so placeholder text never becomes user input.
    """
    selectionConfirmed = Signal(object)
    selectionCleared = Signal()

    def __init__(self, parent=None):
        from PySide6.QtWidgets import QCompleter
        super().__init__(parent)
        self._confirmed_id = None
        self._confirmed_caption = ''
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setObjectName('CustomerLookup')
        self.setMaxVisibleItems(12)
        self.lineEdit().setPlaceholderText('Search by name, suburb or phone…')
        self.lineEdit().setClearButtonEnabled(True)
        self.lineEdit().textEdited.connect(self._editing)
        self.activated[int].connect(self._activated)
        completer = QCompleter(self.model(), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(completer)
        completer.activated[str].connect(self._completed)

    def _editing(self, text):
        if text != self._confirmed_caption and self._confirmed_id is not None:
            self._confirmed_id = None
            self._confirmed_caption = ''
            self.selectionCleared.emit()

    def _activated(self, index):
        self._confirm(index)

    def _completed(self, value):
        # QCompleter can supply a string or QModelIndex on supported Qt builds.
        caption = value.data() if hasattr(value, 'data') else str(value)
        index = self.findText(caption, Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self._confirm(index)

    def _confirm(self, index):
        if index < 0 or self.itemData(index) is None:
            return
        cid = self.itemData(index)
        was_confirmed = self._confirmed_id == cid and self._confirmed_caption == self.itemText(index)
        self.blockSignals(True)
        self.setCurrentIndex(index)
        self.lineEdit().setText(self.itemText(index))
        self.blockSignals(False)
        self._confirmed_id = cid
        self._confirmed_caption = self.itemText(index)
        if not was_confirmed:
            self.selectionConfirmed.emit(cid)

    def select_customer(self, customer_id, *, emit=False):
        index = self.findData(customer_id) if customer_id is not None else -1
        self.blockSignals(True)
        self.setCurrentIndex(index)
        if index < 0:
            self.lineEdit().clear()
            self._confirmed_id = None
            self._confirmed_caption = ''
        else:
            self.lineEdit().setText(self.itemText(index))
            self._confirmed_id = customer_id
            self._confirmed_caption = self.itemText(index)
        self.blockSignals(False)
        if emit and self._confirmed_id is not None:
            self.selectionConfirmed.emit(self._confirmed_id)

    def valid_customer_id(self):
        if self._confirmed_id is None:
            return None
        index = self.findData(self._confirmed_id)
        if index < 0 or self.lineEdit().text().strip() != self.itemText(index):
            return None
        return self._confirmed_id


class ChoiceGrid(QWidget):
    """Accessible, selectable multi-choice chips, rather than giant checkbox lists.

    Checkbox state and .checkboxes are preserved for the caller and for
    service-switching code. Items created in Settings remain selectable.
    """
    def __init__(self, options, selected=(), parent=None, *, empty_text='No equipment choices. Add them in Settings.'):
        super().__init__(parent)
        self.setObjectName('ChoiceGrid')
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 3, 0, 3)
        self.grid.setHorizontalSpacing(9)
        self.grid.setVerticalSpacing(9)
        self.checkboxes = {}
        self.entries = []
        self._columns = 0
        for option in dict.fromkeys([*options, *selected]):
            checkbox = QCheckBox(str(option))
            checkbox.setObjectName('ChoiceChip')
            checkbox.setChecked(option in selected)
            checkbox.setAccessibleName(str(option))
            checkbox.setToolTip(str(option))
            checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
            entry = QWidget()
            entry.setObjectName('ChoiceChipEntry')
            col = QVBoxLayout(entry)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(6)
            col.addWidget(checkbox)
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
        # Let the available form width determine columns rather than fixed rows.
        self._reflow(3 if self.width() >= 750 else 2 if self.width() >= 440 else 1)
        super().resizeEvent(event)

    def selected_values(self):
        return [option for option, checkbox in self.checkboxes.items() if checkbox.isChecked()]


class WorkTypeGrid(ChoiceGrid):
    """Work chips with independent inside / outside / both segmented controls."""
    def __init__(self, options, selected=(), sides=None, parent=None, **kwargs):
        super().__init__(options, selected, parent, **kwargs)
        self.side_buttons = {}
        self.side_frames = {}
        self.side_groups = {}
        for option, entry in zip(self.checkboxes, self.entries):
            checkbox = self.checkboxes[option]
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
            entry.layout().addWidget(frame)
            frame.setVisible(checkbox.isChecked())
            checkbox.toggled.connect(frame.setVisible)
            self.side_buttons[option] = buttons
            self.side_frames[option] = frame
            self.side_groups[option] = group
        self.set_sides(sides or {})

    def set_sides(self, sides):
        for option, group in self.side_groups.items():
            group.setExclusive(False)
            for side, button in self.side_buttons[option].items():
                button.setChecked(sides.get(option) == side)
            group.setExclusive(True)

    def selected_sides(self):
        return {option: side for option in self.selected_values()
                for side, button in self.side_buttons[option].items() if button.isChecked()}


class GroupedWorkTypeGrid(QWidget):
    """Categorise configured work types visually without changing stored values.

    Unrecognised custom types always remain available in 'Other services'.
    """
    GROUPS = ('Windows & glass', 'Exterior cleaning', 'Doors & other', 'Commercial', 'Other services')

    @staticmethod
    def classify(name):
        name = name.casefold()
        if any(term in name for term in ('commercial', 'shop front', 'common area', 'front facade')):
            return 'Commercial'
        if any(term in name for term in ('door', 'tracks', 'louvres', 'louvers', 'fans')):
            return 'Doors & other'
        if any(term in name for term in ('pressure', 'gutter', 'roof', 'solar', 'fence', 'balustrade', 'pool')):
            return 'Exterior cleaning'
        if any(term in name for term in ('window', 'glass', 'screen', 'mirror', 'skylight', 'flyscreen', 'awning')):
            return 'Windows & glass'
        return 'Other services'

    def __init__(self, options, selected=(), sides=None, parent=None, **kwargs):
        super().__init__(parent)
        self.setObjectName('GroupedWorkTypes')
        self._options = list(dict.fromkeys([*options, *selected]))
        self._groups = {}
        self.checkboxes = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)
        buckets = {key: [] for key in self.GROUPS}
        for name in self._options:
            buckets[self.classify(str(name))].append(name)
        col = 0
        row = 0
        for title in self.GROUPS:
            if not buckets[title]:
                continue
            card = QFrame()
            card.setObjectName('WorkCategoryCard')
            vbox = QVBoxLayout(card)
            vbox.setContentsMargins(11, 11, 11, 11)
            vbox.setSpacing(7)
            heading = QLabel(title)
            heading.setObjectName('WorkCategoryTitle')
            vbox.addWidget(heading)
            grid = WorkTypeGrid(buckets[title], [item for item in selected if item in buckets[title]], sides or {},
                                empty_text=kwargs.get('empty_text', 'No work types configured.'))
            vbox.addWidget(grid)
            self._groups[title] = grid
            self.checkboxes.update(grid.checkboxes)
            layout.addWidget(card, row, col)
            col += 1
            if col == 2:
                col = 0
                row += 1
        if not self._groups:
            empty = QLabel(kwargs.get('empty_text', 'No work types configured.'))
            empty.setWordWrap(True)
            layout.addWidget(empty, 0, 0)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

    def selected_values(self):
        return [item for item in self._options if self.checkboxes[item].isChecked()]

    def selected_sides(self):
        return {key: value for group in self._groups.values()
                for key, value in group.selected_sides().items()}

    def set_sides(self, sides):
        for group in self._groups.values():
            group.set_sides(sides)
