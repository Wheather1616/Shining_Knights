"""Jobs workspace surfaces and distinctive maroon dropdown controls."""
from .tokens import themed

JOBS_QSS = themed(r'''
QWidget#JobsPage { background: @canvas@; }
QWidget#JobsListCard, QWidget#JobDetailCard {
    background: @surface@; border: 1px solid @border@; border-radius: @radius_card@;
}
QScrollArea#JobDetailScroll { border: none; background: @surface@; }
QWidget#JobDetailContent { background: @surface@; }
QTreeWidget#JobsTree { border: none; border-radius: 0; }
QTreeWidget#JobsTree::item { border-bottom: 1px solid @border@; padding: 6px 8px; }
QLabel#JobCustomerName { color: @bordeaux@; font-family: @font_regular@; font-size: 24px; }
QLabel#JobStatus {
    background: @cyan_soft@; color: #176478; border: 1px solid @cyan_border@;
    border-radius: 7px; padding: 5px 8px;
}
QLabel#JobsSelection { color: @text@; font-size: 13px; }
QLabel#JobsError { color: #8d332c; }
QPushButton[role="link"] {
    background: transparent; color: #176478; border: none;
    font-family: @font_body@; padding: 6px; min-height: 22px;
}
QPushButton[role="link"]:hover { background: @cyan_soft@; }
QPushButton[role="link"]:focus { border: 1px solid @cyan@; padding: 5px; }
QPushButton[role="link"]:disabled { color: #71656d; background: transparent; }
QComboBox[role="jobFilter"], QPushButton[role="jobMenu"] {
    background: @bordeaux_mid@; color: @white@; border: 1px solid @bordeaux_mid@;
    border-radius: 9px; padding: 8px 34px 8px 12px; min-height: 22px;
    font-family: @font_body@;
}
QComboBox[role="jobFilter"]:hover, QPushButton[role="jobMenu"]:hover {
    background: @bordeaux@; border-color: @bordeaux@;
}
QComboBox[role="jobFilter"]:focus, QPushButton[role="jobMenu"]:focus {
    border: 2px solid @cyan@; padding: 7px 33px 7px 11px;
}
QComboBox[role="jobFilter"]::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 30px; border: none; background: transparent;
}
QComboBox[role="jobFilter"]::down-arrow {
    image: @icon_down_white@; width: 14px; height: 14px;
}
QPushButton[role="jobMenu"]::menu-indicator {
    image: @icon_down_white@; width: 14px; height: 14px;
    subcontrol-origin: padding; subcontrol-position: right center; right: 8px;
}
QComboBox[role="jobFilter"] QAbstractItemView {
    background: @surface@; color: @bordeaux_mid@;
    selection-background-color: @bordeaux_mid@; selection-color: @white@;
    border: 1px solid @bordeaux_mid@; padding: 4px; outline: 0;
}
QComboBox[role="jobFilter"]:disabled, QPushButton[role="jobMenu"]:disabled {
    background: #f0eae5; color: #71656d; border-color: @border@;
}
QMenu#JobsMenu { background: @surface@; color: @text@; border: 1px solid @border_strong@; padding: 6px; }
QMenu#JobsMenu::item { padding: 8px 16px; background: transparent; }
QMenu#JobsMenu::item:selected { background: @bordeaux_mid@; color: @white@; }
QMenu#JobsMenu::item:disabled { color: #71656d; }
''')
