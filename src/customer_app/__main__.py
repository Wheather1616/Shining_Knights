from .qt_bootstrap import configure_qt_plugin_paths

configure_qt_plugin_paths()

from .app import run

if __name__ == "__main__":
    raise SystemExit(run())
