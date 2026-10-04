"""Run the source test suite from any working directory with one command."""
from pathlib import Path
import importlib.util
import os
import subprocess
import sys

def main():
    root=Path(__file__).resolve().parents[1]
    if not (root/'src/customer_app/__main__.py').is_file():
        print('Expected src/customer_app/__main__.py under the project root.',file=sys.stderr)
        return 2
    os.chdir(root)
    sys.path.insert(0,str(root/'src'))
    args=sys.argv[1:]
    if '--native-ui' in args:
        args.remove('--native-ui')
        os.environ['QT_QPA_PLATFORM']={'darwin':'cocoa','win32':'windows'}.get(sys.platform,'xcb')
    else:
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    os.environ['PYTEST_QT_API']='pyside6'
    required=('pytest','pytestqt','pytest_cov','hypothesis','PySide6','sqlcipher3','keyring')
    missing=[name for name in required if importlib.util.find_spec(name) is None]
    if missing:
        print('Missing test dependencies: '+', '.join(missing),file=sys.stderr)
        print('Install with: python -m pip install -r requirements.txt -r requirements-test.txt',file=sys.stderr)
        return 2
    from customer_app.qt_bootstrap import configure_qt_plugin_paths
    configure_qt_plugin_paths()
    # Start measurement in a fresh process, before importing the application.
    # The parent only configures Qt paths for its child.
    os.environ['PYTHONPATH']=os.pathsep.join(filter(None,(str(root/'src'),os.environ.get('PYTHONPATH',''))))
    try:
        return subprocess.run([sys.executable,'-m','pytest','-c',str(root/'pytest.ini'),*args]).returncode
    except KeyboardInterrupt:
        return 130

if __name__=='__main__': raise SystemExit(main())
