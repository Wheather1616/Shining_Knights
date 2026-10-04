import pytest
from keyring.errors import KeyringError
from customer_app import security
from customer_app.security import SecureKeyStore, SecureKeyStoreError

def test_existing_key_is_normalised_without_replacement(monkeypatch):
    monkeypatch.setattr(security.keyring,'get_password',lambda *a:'AB'*32)
    assert SecureKeyStore().get_or_create_database_key()=='ab'*32

def test_new_key_is_stored_and_verified(monkeypatch):
    values={}
    monkeypatch.setattr(security.secrets,'token_hex',lambda length:'34'*32)
    monkeypatch.setattr(security.keyring,'get_password',lambda service,account:values.get((service,account)))
    monkeypatch.setattr(security.keyring,'set_password',lambda service,account,key:values.update({(service,account):key}))
    assert SecureKeyStore().get_or_create_database_key()=='34'*32
    assert values=={('ShiningKnights','database-key-v1'):'34'*32}

@pytest.mark.parametrize('bad',['bad','12'*31,'gg'*32])
def test_malformed_stored_key_is_refused(monkeypatch,bad):
    monkeypatch.setattr(security.keyring,'get_password',lambda *a:bad)
    with pytest.raises(SecureKeyStoreError,match='unexpected format'): SecureKeyStore().get_or_create_database_key()

@pytest.mark.parametrize('stage',['read','write','verify'])
def test_credential_store_errors_have_no_file_fallback(monkeypatch,stage,tmp_path):
    monkeypatch.chdir(tmp_path)
    calls=[]
    def get(*a):
        calls.append('read')
        if stage=='read': raise KeyringError('Unavailable')
        return None if len(calls)==1 else '00'*32
    def set_password(*a):
        if stage=='write': raise KeyringError('Unavailable')
    monkeypatch.setattr(security.keyring,'get_password',get)
    monkeypatch.setattr(security.keyring,'set_password',set_password)
    with pytest.raises(SecureKeyStoreError): SecureKeyStore().get_or_create_database_key()
    assert list(tmp_path.iterdir())==[]

def test_backend_description_and_failure(monkeypatch):
    monkeypatch.setattr(security.keyring,'get_keyring',lambda:object())
    assert SecureKeyStore.backend_name()=='builtins.object'
    monkeypatch.setattr(security.keyring,'get_keyring',lambda:1/0)
    assert SecureKeyStore.backend_name()=='unknown'
