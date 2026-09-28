"""Compose ReceiptFlow's design-system and component QSS layers."""

from .base import BASE_QSS
from .common import COMMON_QSS
from .shell import SHELL_QSS
from .home import HOME_QSS
from .browse import BROWSE_QSS
from .settings import SETTINGS_CORE_QSS, SETTINGS_CATALOG_QSS, SETTINGS_SURCHARGE_QSS
from .receipt import RECEIPT_QSS
from .desktop import DESKTOP_QSS

STYLE_LAYERS = (
    BASE_QSS,
    COMMON_QSS,
    SHELL_QSS,
    HOME_QSS,
    BROWSE_QSS,
    SETTINGS_CORE_QSS,
    SETTINGS_CATALOG_QSS,
    SETTINGS_SURCHARGE_QSS,
    RECEIPT_QSS,
    DESKTOP_QSS,
)

APP_QSS = "\n\n".join(layer.strip() for layer in STYLE_LAYERS if layer.strip())

__all__ = [
    "APP_QSS",
    "STYLE_LAYERS",
    "BASE_QSS",
    "COMMON_QSS",
    "SHELL_QSS",
    "HOME_QSS",
    "BROWSE_QSS",
    "SETTINGS_CORE_QSS",
    "SETTINGS_CATALOG_QSS",
    "SETTINGS_SURCHARGE_QSS",
    "RECEIPT_QSS",
    "DESKTOP_QSS",
]
