"""Reusable presentation-only sections for record and service forms.

No persistence logic lives here. Sections may collapse, but their input widgets
remain alive and retain all unsaved values.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QToolButton, QSizePolicy, QLayout)


def plain(text, object_name):
    item = QLabel(text)
    item.setObjectName(object_name)
    item.setWordWrap(True)
    item.setTextFormat(Qt.TextFormat.PlainText)
    return item


class SectionCard(QFrame):
    """Brand-coloured heading and optional disclosure with a two-column field grid."""
    def __init__(self, title, subtitle='', symbol='✦', *, expanded=True, collapsible=False,
                 parent=None, tone=None):
        super().__init__(parent)
        self.setObjectName('FormSectionCard')
        tone = tone or self._tone_for(title)
        self.setProperty('tone', tone)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(17, 15, 17, 17)
        outer.setSpacing(11)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        heading = QHBoxLayout()
        heading.setSpacing(11)
        icon = plain(symbol, 'FormSectionSymbol')
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(36, 36)
        icon.setProperty('tone', tone)
        heading.addWidget(icon)
        words = QVBoxLayout()
        words.setSpacing(2)
        words.addWidget(plain(title, 'FormCardTitle'))
        if subtitle:
            words.addWidget(plain(subtitle, 'FormCardSubtitle'))
        heading.addLayout(words, 1)
        self.toggle = None
        if collapsible:
            self.toggle = QToolButton()
            self.toggle.setObjectName('FormDisclosureButton')
            self.toggle.setCheckable(True)
            self.toggle.setChecked(expanded)
            self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle.setAccessibleName('Show or hide ' + title)
            self.toggle.toggled.connect(self.set_expanded)
            heading.addWidget(self.toggle)
        outer.addLayout(heading)
        self.content = QWidget()
        self.content.setObjectName('FormCardContent')
        self.fields = QVBoxLayout(self.content)
        self.fields.setContentsMargins(0, 0, 0, 0)
        self.fields.setSpacing(11)
        self.fields.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        outer.addWidget(self.content)
        if collapsible:
            self.set_expanded(expanded)

    @staticmethod
    def _tone_for(title):
        value = title.lower()
        if any(term in value for term in ('contact', 'job overview', 'pricing', 'notes')):
            return 'coral'
        if any(term in value for term in ('address', 'saved service', 'equipment', 'service detail', 'defaults')):
            return 'teal'
        return 'maroon'

    def set_expanded(self, expanded):
        self.content.setVisible(expanded)
        self.content.updateGeometry()
        self.updateGeometry()
        if self.toggle is not None:
            self.toggle.setText('Hide  ▴' if expanded else 'Show  ▾')
            self.toggle.blockSignals(True)
            self.toggle.setChecked(expanded)
            self.toggle.blockSignals(False)

    def add_widget(self, widget):
        self.fields.addWidget(widget)
        return widget

    def add_field(self, title, control):
        field = QWidget()
        field.setObjectName('FormField')
        inner = QVBoxLayout(field)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(5)
        caption = plain(title, 'FormFieldLabel')
        caption.setBuddy(control)
        inner.addWidget(caption)
        inner.addWidget(control)
        self.add_widget(field)
        return field

    def add_pair(self, *items):
        container = QWidget()
        container.setObjectName('FormFieldRow')
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(5)
        for col, (title, control) in enumerate(items):
            heading = plain(title, 'FormFieldLabel')
            heading.setBuddy(control)
            layout.addWidget(heading, 0, col)
            layout.addWidget(control, 1, col)
            layout.setColumnStretch(col, 1)
        self.add_widget(container)
        return container

    def add_hint(self, text):
        return self.add_widget(plain(text, 'FormFieldHint'))


class SelectionDisclosure(QFrame):
    """A compact summary of a large set of selectable chips."""
    def __init__(self, title, choices, *, expanded=False, parent=None):
        super().__init__(parent)
        self.setObjectName('FormSelectionDisclosure')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(11, 10, 11, 10)
        outer.setSpacing(8)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        header = QHBoxLayout()
        title_label = plain(title, 'FormSelectionTitle')
        header.addWidget(title_label, 1)
        self.summary = plain('', 'FormSelectionSummary')
        self.summary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header.addWidget(self.summary, 2)
        self.toggle = QToolButton()
        self.toggle.setObjectName('FormDisclosureButton')
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setAccessibleName('Show or hide ' + title)
        self.toggle.toggled.connect(self.set_expanded)
        header.addWidget(self.toggle)
        outer.addLayout(header)
        self.choices = choices
        outer.addWidget(choices)
        for checkbox in choices.checkboxes.values():
            checkbox.toggled.connect(self.refresh_summary)
        self.set_expanded(expanded)
        self.refresh_summary()

    def set_expanded(self, expanded):
        self.choices.setVisible(expanded)
        self.toggle.setText('Hide  ▴' if expanded else 'Edit  ▾')
        self.choices.updateGeometry()
        self.updateGeometry()

    def refresh_summary(self, *_):
        items = self.choices.selected_values()
        self.summary.setText(', '.join(items[:3]) + (f' +{len(items)-3} more' if len(items) > 3 else '')
                             if items else 'None selected')
