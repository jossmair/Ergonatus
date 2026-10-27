"""Never share a live user's IPC endpoints with test windows."""
import uuid
import pytest

@pytest.fixture(autouse=True)
def isolated_ipc_identity(monkeypatch):
    monkeypatch.setenv('USERDOMAIN','ErgonatusTest-'+uuid.uuid4().hex)
