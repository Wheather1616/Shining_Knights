"""Home summaries and customer profile text."""
from .tokens import themed

HOME_QSS = themed(r'''
QLabel#HomeMetrics {
    color: @bordeaux@; background: @surface@;
    border: 1px solid @border@; border-left: 5px solid @cyan@;
    border-radius: 12px; padding: 18px;
    font-family: @font_regular@; font-size: 18px;
}
QLabel#CustomerProfileText {
    background: transparent; color: @text@;
    border: none; padding: 4px; font-size: 14px;
}
''')
