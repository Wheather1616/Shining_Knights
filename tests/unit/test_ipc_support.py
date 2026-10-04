"""Keep socket capability checks reliable with macOS's long temporary paths."""
import errno
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tests import ipc_support


def install_socket(monkeypatch, bind, tmp_path):
    class Endpoint:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def bind(self, path): bind(Path(path))
    monkeypatch.setattr(ipc_support.socket, 'socket', lambda *a: Endpoint())
    monkeypatch.setattr(ipc_support, 'os', type('Unix', (), {'name': 'posix'}))
    if os.name == 'nt':
        # Exercise the Unix branch on Windows without requiring a /tmp folder.
        # Still check that the helper requests the short Unix root explicitly.
        def temporary_directory(*, prefix, dir):
            assert dir == '/tmp'
            return TemporaryDirectory(prefix=prefix, dir=tmp_path)
        monkeypatch.setattr(ipc_support, 'TemporaryDirectory', temporary_directory)


def test_probe_uses_short_private_path_and_cleans_up(monkeypatch, tmp_path):
    long_temp = tmp_path / ('macos-temporary-directory-' * 6)
    long_temp.mkdir()
    monkeypatch.setenv('TMPDIR', str(long_temp))
    observed = []
    def bind(path):
        if os.name != 'nt':
            assert len(bytes(path)) < 104
            assert path.parent.stat().st_mode & 0o777 == 0o700
        path.touch()
        observed.append(path)
    install_socket(monkeypatch, bind, tmp_path)
    ipc_support.check_unix_socket_support()
    assert len(observed) == 1
    assert not observed[0].parent.exists()


@pytest.mark.parametrize('error, skip', [(errno.EPERM, True), (errno.EACCES, False)])
def test_probe_skips_only_sandbox_denial_and_cleans_up(monkeypatch, tmp_path, error, skip):
    observed = []
    def bind(path):
        path.touch()
        observed.append(path)
        raise OSError(error, 'Injected socket failure')
    install_socket(monkeypatch, bind, tmp_path)
    expected = pytest.skip.Exception if skip else OSError
    with pytest.raises(expected): ipc_support.check_unix_socket_support()
    assert not observed[0].parent.exists()


def test_windows_does_not_probe_unix_sockets(monkeypatch):
    monkeypatch.setattr(ipc_support, 'os', type('Windows', (), {'name': 'nt'}))
    def forbidden(*args): raise AssertionError('Windows should use Qt named pipes')
    monkeypatch.setattr(ipc_support.socket, 'socket', forbidden)
    ipc_support.check_unix_socket_support()
