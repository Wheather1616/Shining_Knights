import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

@pytest.mark.parametrize('passes',[True,False])
def test_runner_uses_its_project_root_and_propagates_failure(tmp_path,passes):
    root=Path(__file__).resolve().parents[2]
    project=tmp_path/'Project with spaces'
    (project/'scripts').mkdir(parents=True)
    (project/'src/customer_app').mkdir(parents=True)
    (project/'tests').mkdir()
    shutil.copy2(root/'scripts/run_tests.py',project/'scripts/run_tests.py')
    (project/'src/customer_app/__init__.py').write_text('')
    (project/'src/customer_app/__main__.py').write_text('')
    (project/'src/customer_app/qt_bootstrap.py').write_text('def configure_qt_plugin_paths(): pass\n')
    (project/'pytest.ini').write_text('[pytest]\ntestpaths = tests\nqt_api = pyside6\n')
    (project/'tests/test_example.py').write_text(f'''import customer_app
from pathlib import Path
def test_source_origin():
    assert Path(customer_app.__file__).resolve()==Path({str(project/'src/customer_app/__init__.py')!r}).resolve()
    assert {passes!r}
''')
    result=subprocess.run([sys.executable,str(project/'scripts/run_tests.py'),'-q','--no-cov'],
        cwd=tmp_path,env={**os.environ},text=True,capture_output=True,timeout=30)
    assert result.returncode==(0 if passes else 1),result.stdout+result.stderr
