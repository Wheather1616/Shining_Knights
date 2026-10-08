"""Compose the ReceiptFlow-style design tokens and customer component layers."""
from .base import BASE_QSS
from .common import COMMON_QSS
from .controls import CONTROLS_QSS
from .shell import SHELL_QSS
from .home import HOME_QSS
from .browse import BROWSE_QSS
from .settings import SETTINGS_QSS
from .customers import CUSTOMERS_QSS
from .jobs import JOBS_QSS

STYLE_LAYERS = (BASE_QSS, COMMON_QSS, CONTROLS_QSS, SHELL_QSS, HOME_QSS, BROWSE_QSS, SETTINGS_QSS, CUSTOMERS_QSS, JOBS_QSS)
APP_QSS = '\n\n'.join(layer.strip() for layer in STYLE_LAYERS if layer.strip())

__all__ = ['APP_QSS', 'STYLE_LAYERS']
