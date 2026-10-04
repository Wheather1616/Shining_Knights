from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
import pytest
from hypothesis import given, strategies as st
from customer_app.models import ValidationError, add_interval, money_text, money_to_cents

@given(st.integers(min_value=0,max_value=99_999_999_999))
def test_money_roundtrip_preserves_every_cent(cents):
    assert money_to_cents(money_text(cents)) == cents
    assert money_to_cents(Decimal(cents)/100) == cents

@given(st.integers(min_value=0,max_value=999_999),st.integers(min_value=1,max_value=9))
def test_fractional_cents_are_rejected(whole,tenth):
    with pytest.raises(ValidationError): money_to_cents(Decimal(whole)+Decimal(tenth)/1000)

@given(st.dates(min_value=date(1900,1,1),max_value=date(2090,12,31)),st.integers(min_value=1,max_value=60))
def test_month_recurrence_clamps_day_without_changing_month(anchor,months):
    year,month=divmod(anchor.year*12+anchor.month-1+months,12)
    expected=date(year,month+1,min(anchor.day,monthrange(year,month+1)[1]))
    assert add_interval(anchor.isoformat(),months,'months') == expected.isoformat()

@given(st.dates(min_value=date(1900,1,1),max_value=date(2090,12,31)),st.integers(min_value=1,max_value=365))
def test_week_recurrence_is_exactly_seven_days_per_week(anchor,weeks):
    assert add_interval(anchor.isoformat(),weeks,'weeks') == (anchor+timedelta(weeks=weeks)).isoformat()

@pytest.mark.parametrize('value,expected',[(None,None),('',None),('0.00',0),('$1,234.56',123456),('999999999.99',99999999999)])
def test_money_boundaries(value,expected):
    assert money_to_cents(value)==expected

@pytest.mark.parametrize('value',['1000000000.00','-0.01','NaN','Infinity','abc'])
def test_invalid_money_boundaries(value):
    with pytest.raises(ValidationError): money_to_cents(value)

@pytest.mark.parametrize('anchor,interval,unit',[('',1,'days'),('2026-01-01',None,'months'),('2026-01-01',1,'')])
def test_no_recurrence_without_an_anchor_and_interval(anchor,interval,unit):
    assert add_interval(anchor,interval,unit) is None
