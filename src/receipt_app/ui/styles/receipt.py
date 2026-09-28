"""Shared receipt-entry and receipt-dialog component styles."""

from .tokens import themed

RECEIPT_QSS = themed(r'''
QFrame#ReceiptDialogFormCard,
QFrame#ReceiptDialogHelperCard {
    border-radius: @radius_large@;
}

QLabel#ReceiptDialogTitle { font-size: 38px; }

QScrollArea#ReceiptDialogFormScroll,
QScrollArea#ReceiptDialogFormScroll > QWidget > QWidget,
QWidget#ReceiptDialogFormContent,
QWidget#ReceiptDialogEntryForm {
    background: transparent;
    border: none;
}

QLabel#ReceiptDialogFieldLabel {
    color: @text@;
    font-family: @font_regular@;
    font-size: 14px;
    min-width: 135px;
}

QWidget#ReceiptDialogEntryForm QTextEdit {
    min-height: 86px;
}

QFrame#ReceiptDialogHelperCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f8efed,
        stop:1 #f4ede8);
}

QFrame#ReceiptDialogIllustration {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(168, 70, 160, 0.12),
        stop:0.55 rgba(215, 208, 200, 0.28),
        stop:1 rgba(248, 118, 102, 0.14));
    border: 1px solid #e7d6d1;
    border-radius: @radius_card@;
}

QLabel#ReceiptDialogIllustrationIcon {
    color: @amethyst@;
}

QLabel#ReceiptDialogIllustrationCaption,
QLabel#ReceiptDialogTipsTitle {
    color: #8a6568;
    font-family: @font_regular@;
    font-size: 10px;
    letter-spacing: 1.5px;
}

QLabel#ReceiptDialogHelperTitle { font-size: 24px; }

QFrame#ReceiptDialogDivider {
    background: #dfd1ca;
    border: none;
    max-height: 1px;
}

QFrame#ReceiptDialogTipRow { background: transparent; border: none; }

QLabel#ReceiptDialogTipDot {
    border-radius: 6px;
    background: @border_strong@;
}
QLabel#ReceiptDialogTipDot[accent="coral"] { background: @coral@; }
QLabel#ReceiptDialogTipDot[accent="amethyst"] { background: @amethyst@; }
QLabel#ReceiptDialogTipDot[accent="cyan"] { background: @cyan@; }

QFrame#ReceiptDialogFooter {
    background: transparent;
    border-top: 1px solid #e3d8d1;
}

QLabel#ReceiptDialogBrand {
    color: @bordeaux@;
    font-family: @font_regular@;
    font-size: 20px;
}

QLabel#ReceiptDialogTagline {
    color: #9b8585;
    font-family: @font_regular@;
    font-size: 9px;
    letter-spacing: 1.2px;
}

QLabel#SurchargeHint {
    background: @cyan_soft@;
    color: #176f83;
    border: 1px solid #bddfe6;
    border-radius: 9px;
    padding: 7px 9px;
    font-family: @font_regular@;
    font-size: 12px;
}
''')
