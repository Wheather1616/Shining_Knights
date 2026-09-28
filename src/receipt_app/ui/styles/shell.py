"""Application shell and sidebar styles."""

from .tokens import themed

SHELL_QSS = themed(r'''
QFrame#BrandSidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5c0a12,
        stop:1 #45050a);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

QLabel#SidebarBrandTitle {
    color: #fff7f4;
    font-family: @font_regular@;
    font-size: 28px;
}

QLabel#SidebarTagline {
    color: rgba(255, 244, 240, 0.76);
    font-family: @font_body@;
    font-size: 14px;
}

QPushButton#SidebarNavButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 14px;
    color: #fff7f4;
    font-family: @font_regular@;
    font-size: 15px;
    padding: 11px 14px;
    text-align: left;
}

QPushButton#SidebarNavButton:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.08);
}

QPushButton#SidebarNavButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(248, 118, 102, 0.32),
        stop:1 rgba(168, 70, 160, 0.16));
    border: 1px solid rgba(248, 118, 102, 0.28);
    color: #fffdfa;
}

QFrame#SidebarStatusCard {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: @radius_card@;
}

QLabel#SidebarStatusTitle {
    color: @white@;
    font-family: @font_regular@;
    font-size: 17px;
}

QLabel#SidebarStatusMeta {
    color: rgba(255, 247, 244, 0.78);
    font-family: @font_regular@;
    font-size: 13px;
}

QLabel#SidebarStatusPath {
    color: rgba(255, 247, 244, 0.70);
    font-family: @font_body@;
    font-size: 12px;
}

QPushButton#SidebarLinkButton {
    background: transparent;
    border: none;
    color: #fff1ec;
    font-family: @font_regular@;
    font-size: 13px;
    padding: 2px 0;
    text-align: left;
}

QPushButton#SidebarLinkButton:hover {
    color: @coral@;
    background: transparent;
    border: none;
}
''')
