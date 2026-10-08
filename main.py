"""Entry point for source launches and PyInstaller builds."""
from pathlib import Path
import sys

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from customer_app.entrypoint import main

if __name__ == '__main__':
    raise SystemExit(main())
