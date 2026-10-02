"""Simple functional theme, pending a separate design pass."""
APP_QSS = '''
QWidget { font-size: 13px; color: #253444; }
QMainWindow, QDialog { background: #f4f6f8; }
QTabWidget::pane { border: 1px solid #d4dde5; background: #f4f6f8; }
QTabBar::tab { padding: 12px 20px; background: #e3eaf0; }
QTabBar::tab:selected { background: #ffffff; color: #176c87; }
QLineEdit, QPlainTextEdit, QComboBox, QListWidget { background: #ffffff; border: 1px solid #bbc9d4; border-radius: 4px; padding: 6px; }
QLineEdit:disabled, QComboBox:disabled { background: #e9edf0; color: #687885; }
QPushButton { padding: 8px 13px; background: #176c87; color: white; border: none; border-radius: 4px; }
QPushButton:hover { background: #12546a; }
QPushButton:disabled { background: #abb7c0; }
QTableWidget, QTreeWidget { background: white; alternate-background-color: #f0f5f8; gridline-color: #e1e8ed; selection-background-color: #176c87; selection-color: white; }
QHeaderView::section { background: #e4ecf1; padding: 7px; border: 0; border-bottom: 1px solid #bbc9d4; }
QLabel#title { font-size: 26px; font-weight: 600; padding: 8px 0; }
QLabel#metrics { font-size: 18px; padding: 16px; background: white; border: 1px solid #d4dde5; border-radius: 6px; }
QCheckBox { spacing: 6px; }
'''
