"""Home-dashboard component styles."""

from .tokens import themed

HOME_QSS = themed(r'''
QScrollArea#HomeScroll,
QScrollArea#HomeScroll > QWidget > QWidget,
QWidget#HomeContent {
    background: @canvas@;
    border: none;
}

QLabel#HomeDisplayTitle {
    font-size: 42px;
}

QLabel#HomeLead {
    font-size: 16px;
}

QFrame#HomeHeroCard,
QFrame#HomeFeatureCard {
    border-radius: @radius_large@;
}

QLabel#HomeBadge {
    background: #fff0eb;
    border: 1px solid #f9d1ca;
    border-radius: 12px;
    color: #c3594c;
    font-family: @font_regular@;
    font-size: 12px;
    letter-spacing: 1px;
    padding: 6px 12px;
}

QLabel#HomeHeroTitle {
    font-size: 32px;
}

QLabel#HomeHeroBody {
    font-size: 16px;
}

QFrame#HomeIllustrationPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(168, 70, 160, 0.10),
        stop:0.5 rgba(215, 208, 200, 0.20),
        stop:1 rgba(248, 118, 102, 0.12));
    border: 1px dashed #e6c7c2;
    border-radius: @radius_card@;
}

QLabel#HomeIllustrationTitle {
    color: #8c6d71;
    font-family: @font_regular@;
    font-size: 17px;
}

QLabel#HomeIllustrationCaption {
    color: #8d8283;
    font-family: @font_body@;
    font-size: 13px;
}

QLabel#HomeFeatureEyebrow {
    color: #8a7173;
    font-family: @font_regular@;
    font-size: 11px;
    letter-spacing: 1.3px;
}

QLabel#HomeFeatureTitle {
    font-size: 22px;
}

QLabel#HomeFeatureBody {
    font-size: 14px;
}

QLabel#HomeFeatureIcon {
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    border-radius: 16px;
    background: @cyan_soft@;
    border: 1px solid @cyan_border@;
    qproperty-alignment: AlignCenter;
}

QLabel#HomeFeatureIcon[accent="cyan"] {
    background: @cyan_soft@;
    border-color: @cyan_border@;
}

QLabel#HomeFeatureIcon[accent="amethyst"] {
    background: @amethyst_soft@;
    border-color: @amethyst_border@;
}

QLabel#HomeFeatureIcon[accent="coral"] {
    background: @coral_soft@;
    border-color: @coral_border@;
}

QFrame#HomeFooter {
    background: transparent;
    border-top: 1px solid #eadfd8;
}

QLabel#HomeFooterStat {
    color: #4f4a52;
    font-family: @font_regular@;
    font-size: 14px;
}

QLabel#HomeFooterNote {
    color: #7a7477;
    font-family: @font_body@;
    font-size: 13px;
}
''')
