from receipt_app.qt_bootstrap import configure_qt_plugin_paths

configure_qt_plugin_paths()

from receipt_app.app import run

if __name__ == "__main__":
    raise SystemExit(run())
