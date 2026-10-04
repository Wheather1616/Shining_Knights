"""Customer application shell and tab navigation."""
from .tokens import themed

SHELL_QSS = themed(r'''
QMainWindow, QDialog, QWidget#AppShell,
QWidget#HomePage, QWidget#CustomersPage, QWidget#JobsPage,
QWidget#SettingsPage, QWidget#SettingsContent {
    background: @canvas@;
}
QWidget#CustomerProfileCard, QWidget#LookupSettingsCard, QWidget#RecordForm {
    background: @surface@;
    border: 1px solid @border@;
    border-radius: 12px;
}
QWidget#LookupSettingsCard QLabel, QWidget#RecordForm QLabel {
    color: @text@; background: transparent; border: none;
}
QTabWidget::pane {
    background: @canvas@; border: 1px solid @border@;
    border-top: 2px solid @bordeaux_mid@;
}
QTabBar::tab {
    background: @surface_soft@; color: @text_muted@;
    border: 1px solid @border@; border-bottom: none;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    padding: 11px 20px; margin-right: 3px;
    font-family: @font_regular@; font-size: 14px;
}
QTabBar::tab:selected { background: @bordeaux_mid@; color: @white@; border-color: @bordeaux_mid@; }
QTabBar::tab:!selected:hover { background: #f0e4dc; color: @bordeaux@; }
QTabWidget#SettingsTabs QTabBar::tab { padding: 9px 18px; }
QLabel#PageTitle { color: @bordeaux@; font-family: @font_regular@; font-size: 28px; }
QLabel#PageHelper, QLabel#SettingsHelper, QLabel#FormHelper { color: @text_muted@; font-size: 14px; }
QLabel#SectionTitle { color: @bordeaux@; font-family: @font_regular@; font-size: 18px; }
QStatusBar { background: @surface_soft@; color: @text_muted@; }
QStatusBar::item { border: none; }
QSplitter::handle { background: @border@; }
QSplitter::handle:hover { background: @cyan_border@; }
QScrollArea#RecordScroll { background: @canvas@; border: none; }
QScrollArea#RecordScroll > QWidget > QWidget { background: @canvas@; }
QDialogButtonBox { background: transparent; }
QMenu { background: @surface@; color: @text@; border: 1px solid @border@; padding: 5px; }
QMenu::item { padding: 7px 18px; }
QMenu::item:selected { background: #dff1f5; color: @text@; }
''')
