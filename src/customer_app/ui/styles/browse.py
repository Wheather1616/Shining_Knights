"""Shared customer, job, equipment and history views."""
from .tokens import themed

BROWSE_QSS = themed(r'''
QTableView, QTableWidget, QTreeView, QTreeWidget, QListView, QListWidget {
    background: @surface@; color: @text@;
    alternate-background-color: @surface_soft@;
    border: 1px solid @border@;
    border-radius: 7px;
    gridline-color: #eadfd8;
    selection-background-color: #dff1f5;
    selection-color: @text@;
    outline: 0; font-family: @font_body@; font-size: 14px;
}
QTableView::item, QTreeView::item, QListView::item { padding: 6px 8px; border: none; }
QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {
    background: #dff1f5; color: @text@;
}
QTableView::item:selected:!active, QTreeView::item:selected:!active, QListView::item:selected:!active {
    background: #e9eef1; color: @text@;
}
QTreeView::item { min-height: 24px; }
QListView::item { min-height: 20px; }
QTreeView::branch { background: transparent; }
QTreeView::branch:has-children:closed { image: @icon_right@; }
QTreeView::branch:has-children:open { image: @icon_down@; }
QHeaderView::section {
    background: #f2e7df; color: @bordeaux@;
    border: none; border-right: 1px solid @border@;
    border-bottom: 1px solid @border_strong@;
    padding: 9px 10px; font-family: @font_body@; font-size: 13px;
}
QTableCornerButton::section { background: #f2e7df; border: none; }
''')
