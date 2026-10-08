"""A reviewed restore followed by a separate final confirmation."""
from datetime import datetime
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout
from .customer_page import label
from .field_settings import button, card


class RestoreDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.step = 2
        self.setWindowTitle('Restore a backup')
        self.resize(570, 470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.progress = label('Step 2 of 3 · Review your backup', 'PageHelper')
        layout.addWidget(self.progress)
        layout.addWidget(label('Review your backup', 'PageTitle'))
        timestamp = datetime.fromtimestamp(info['modified']).strftime('%d %B %Y, %I:%M %p')
        layout.addWidget(label('Backup date: ' + timestamp))
        layout.addWidget(label(f"Includes {info['customers']} customers and {info['jobs']} jobs (including Trash)."))
        layout.addWidget(label('Settings will also be restored.' if info['settings'] else 'This older backup contains records only. Your current settings will be kept.', 'PageHelper'))
        widget, inner = card('What will happen', 'Your current records will be replaced by this backup. Changes made after its date will be removed.')
        widget.setObjectName('RestoreWarning')
        layout.addWidget(widget)
        layout.addWidget(label('A safety copy of your current records and settings will be saved first.', 'PageHelper'))
        self.confirmation = label('', 'SettingsError')
        layout.addWidget(self.confirmation)
        layout.addStretch()
        row = QHBoxLayout()
        row.addWidget(button('Cancel', self.reject))
        row.addStretch()
        self.continue_button = button('Continue', self.next_step, 'primary')
        row.addWidget(self.continue_button)
        layout.addLayout(row)

    def next_step(self):
        if self.step == 2:
            self.step = 3
            self.progress.setText('Step 3 of 3 · Confirm restore')
            self.confirmation.setText('Ready to replace your current records with the backup shown above?')
            self.continue_button.setText('Restore backup')
        else:
            self.accept()
