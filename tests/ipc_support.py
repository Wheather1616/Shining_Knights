"""Probe host socket permissions without using pytest's potentially long paths."""
import errno
import os
from pathlib import Path
import socket
from tempfile import TemporaryDirectory

import pytest


def check_unix_socket_support():
    if os.name == 'nt':
        return  # Qt uses named pipes on Windows.

    # macOS sun_path is limited to 104 bytes. pytest's descriptive tmp_path
    # can exceed it, so use a private, short-lived directory under /tmp.
    with TemporaryDirectory(prefix='sk-ipc-', dir='/tmp') as directory:
        probe = Path(directory) / 'p.sock'
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as endpoint:
                endpoint.bind(str(probe))
        except OSError as exc:
            if exc.errno == errno.EPERM:
                pytest.skip('The execution sandbox blocks native Unix sockets (EPERM).')
            raise
