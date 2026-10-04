"""Native Qt IPC checks; no real keychain, production path or database is used."""
from customer_app.single_instance import SingleInstanceManager
from tests.ipc_support import check_unix_socket_support

def test_secondary_launch_activates_primary_and_cannot_take_its_lock(qapp,qtbot):
    check_unix_socket_support()
    first=SingleInstanceManager(); second=SingleInstanceManager()
    try:
        assert first.acquire()==(True,False)
        with qtbot.waitSignal(first.activation_requested,timeout=2000):
            assert second.acquire()==(False,True)
        first.release()
        assert second.acquire()==(True,False)
    finally:
        first.release(); second.release()
