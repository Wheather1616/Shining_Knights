import copy
import json
import pytest
from customer_app import config
from customer_app.config import AppSettings, FieldDefinition, SettingsStore

@pytest.mark.parametrize('key',['id','fee_cents','Name','123','has space','name'])
def test_custom_field_keys_cannot_conflict_with_core_storage(tmp_path,key):
    settings=AppSettings(db_path=tmp_path/'data.db')
    settings.customer_fields.append(FieldDefinition(key,'Invalid'))
    with pytest.raises(ValueError): settings.validate()

@pytest.mark.parametrize('kind',['core_type','core_hidden','core_missing','required_hidden','empty_choices','duplicates','blank_label','bad_type','lookup_duplicates','status_choices'])
def test_configuration_rejects_invalid_contracts(tmp_path,kind):
    settings=AppSettings(db_path=tmp_path/'data.db')
    if kind=='core_type': settings.customer_fields[0].field_type='number'
    elif kind=='core_hidden': settings.customer_fields[0].enabled=False
    elif kind=='core_missing': settings.customer_fields.pop(0)
    elif kind=='required_hidden': settings.customer_fields.append(FieldDefinition('custom','Custom',required=True,enabled=False))
    elif kind=='empty_choices': settings.customer_fields.append(FieldDefinition('custom','Custom','dropdown'))
    elif kind=='duplicates': settings.customer_fields.append(FieldDefinition('custom','Custom','dropdown',options=['A','A']))
    elif kind=='blank_label': settings.customer_fields[0].label=' '
    elif kind=='bad_type': settings.customer_fields.append(FieldDefinition('custom','Custom','invalid'))
    elif kind=='lookup_duplicates': settings.equipment_options=['Ladder','ladder']
    elif kind=='status_choices': settings.job_fields[2].options=['Scheduled']
    with pytest.raises(ValueError): settings.validate()

def test_load_merges_new_core_fields_and_preserves_custom_definitions(tmp_path):
    settings=AppSettings(db_path=tmp_path/'data.db')
    settings.customer_fields.append(FieldDefinition('access','Access instructions'))
    data=settings.to_dict()
    data['customer_fields']=[f for f in data['customer_fields'] if f['key']!='business_name']
    loaded=AppSettings.from_dict(data)
    assert {f.key for f in loaded.customer_fields}>={'business_name','access'}
    assert loaded.db_path==settings.db_path
    with pytest.raises(ValueError,match='version'): AppSettings.from_dict({'config_version':999})

def test_failed_atomic_settings_save_preserves_last_good_version(tmp_path,monkeypatch):
    store=SettingsStore(tmp_path/'settings.json')
    original=AppSettings(db_path=tmp_path/'data.db'); store.save(original)
    before=store.settings_path.read_bytes()
    changed=copy.deepcopy(original); changed.customer_fields[0].label='Customer'
    def fail(*args): raise OSError('Disk unavailable')
    monkeypatch.setattr(config.os,'replace',fail)
    with pytest.raises(OSError,match='Disk unavailable'): store.save(changed)
    assert store.settings_path.read_bytes()==before
    assert store.load().customer_fields[0].label=='Client name'

@pytest.mark.parametrize('content',['{broken','[]','{"customer_fields": null}','{"config_version": 99}'])
def test_unreadable_settings_are_preserved(tmp_path,content):
    path=tmp_path/'settings.json'; path.write_text(content)
    with pytest.raises(ValueError,match='preserved'): SettingsStore(path).load()
    assert path.read_text()==content

def test_field_options_are_independent_snapshots(tmp_path):
    settings=AppSettings(db_path=tmp_path/'data.db')
    fields=settings.fields_for('customers')
    fields[0].label='Changed'
    next(f for f in fields if f.key=='default_equipment').options.clear()
    assert settings.customer_fields[0].label=='Client name'
    assert settings.equipment_options
    with pytest.raises(ValueError): settings.fields_for('receipts')
