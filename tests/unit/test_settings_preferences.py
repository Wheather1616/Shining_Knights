import copy
import pytest
from customer_app.config import AppSettings, SettingsStore


def test_older_configuration_gains_safe_preference_defaults(context):
    data=context.settings.to_dict()
    for key in ('inactive_options','default_payment_method','remember_jobs_filters','jobs_default_group','jobs_filters'): data.pop(key)
    loaded=AppSettings.from_dict(data)
    assert not loaded.remember_jobs_filters and loaded.jobs_default_group == 'date'
    assert loaded.inactive_options == {} and loaded.default_payment_method == ''
    assert loaded.customer_fields == context.settings.customer_fields


def test_preferences_and_inactive_catalogue_roundtrip(context):
    settings=copy.deepcopy(context.settings)
    settings.equipment_options.remove('3m ladder');settings.inactive_options={'equipment_options':['3m ladder']}
    settings.default_payment_method='Card';settings.remember_jobs_filters=True
    settings.jobs_default_group='customer';settings.jobs_filters={'status':'Upcoming','range':'custom','group':'date','from':'2026-10-01','to':'2026-10-07'}
    context.store.save(settings)
    assert context.store.load() == settings
    assert '3m ladder' not in next(f for f in settings.fields_for('jobs') if f.key == 'equipment').options


@pytest.mark.parametrize('attr,value', [('inactive_options',{'bad':['Ladder']}),('inactive_options',{'equipment_options':['3m ladder']}),
    ('inactive_options',{'equipment_options':['','x']}),('inactive_options',{'equipment_options':['Old','old']}),
    ('default_payment_method','Cheque'),('remember_jobs_filters','yes'),('jobs_default_group','week'),
    ('jobs_filters',{'search':'private'}),('jobs_filters',{'status':'Bad'}),('jobs_filters',{'range':'year'}),
    ('jobs_filters',{'group':'week'}),('jobs_filters',{'from':'bad'}),('jobs_filters',{'from':'20261007'})])
def test_invalid_preferences_are_rejected(context,attr,value):
    settings=copy.deepcopy(context.settings);setattr(settings,attr,value)
    with pytest.raises(ValueError): settings.validate()
