"""Overview queries use real encrypted files and explicit calendar boundaries."""
from dataclasses import fields
from datetime import timedelta

import pytest

from customer_app.models import CustomerRecord, JobRecord


def edit_customer(db, cid, **changes):
    saved = db.get_customer(cid)
    values = {f.name: saved[f.name] for f in fields(CustomerRecord)}
    db.update_customer(cid, CustomerRecord(**{**values, **changes}))


def test_seven_days_are_inclusive_and_open_jobs_only(context, today):
    db = context.db
    cid = db.create_customer(CustomerRecord(name='Same name', suburb='Coogee'))
    ids = {}
    for offset in (-1, 0, 6, 7):
        ids[offset] = db.create_job(JobRecord(cid, scheduled_date=(today + timedelta(days=offset)).isoformat()))
    progress = db.create_job(JobRecord(cid, scheduled_date=today.isoformat(), status='In progress'))
    db.create_job(JobRecord(cid, scheduled_date=today.isoformat(), status='Cancelled'))
    db.create_job(JobRecord(cid, scheduled_date=today.isoformat(), status='Completed', completed_date=today.isoformat()))
    trashed = db.create_job(JobRecord(cid, scheduled_date=today.isoformat()))
    db.trash_job(trashed)
    db.create_job(JobRecord(cid))
    db.set_customer_active(cid, False)  # Existing visits still need doing.
    result = db.home_overview(today)
    assert result['as_of'] == '2026-10-02'
    assert result['today_jobs'] == 2
    assert result['next7_jobs'] == 3
    assert [j['id'] for j in result['upcoming']] == [ids[0], progress, ids[6]]
    assert result['upcoming'][0]['customer_name'] == 'Same name'
    assert result['upcoming'][0]['suburb'] == 'Coogee'
    assert result['overdue_jobs'] == 1
    assert result['needs_booking'] == []


@pytest.mark.parametrize('offset,status,trashed,expected', [
    (0, 'Scheduled', False, False), (30, 'In progress', False, False),
    (-1, 'Scheduled', False, True), (None, 'Scheduled', False, True),
    (1, 'Cancelled', False, True), (1, 'Completed', False, True),
    (1, 'Scheduled', True, True),
])
def test_only_future_open_bookings_suppress_reminders(context, today, offset, status, trashed, expected):
    db = context.db
    cid = db.create_customer(CustomerRecord(name='Due customer', first_service_date=today.isoformat()))
    jid = db.create_job(JobRecord(cid, scheduled_date=(today + timedelta(days=offset)).isoformat() if offset is not None else '',
                                 status=status, completed_date=today.isoformat() if status == 'Completed' else ''))
    if trashed:
        db.trash_job(jid)
    # Completed one-off service has no repeat due date; give it a repeat interval.
    if status == 'Completed':
        edit_customer(db, cid, frequency_value=1, frequency_unit='days')
    assert bool(db.home_overview(today)['needs_booking']) is expected


def test_due_dates_recurrence_active_state_and_duplicate_names(context, today):
    db = context.db
    overdue = db.create_customer(CustomerRecord(name='Alex', suburb='Bondi', first_service_date='2026-09-01'))
    end = db.create_customer(CustomerRecord(name='Alex', suburb='Coogee', first_service_date='2026-10-08'))
    db.create_customer(CustomerRecord(name='Outside range', first_service_date='2026-10-09'))
    db.create_customer(CustomerRecord(name='No due date'))
    inactive = db.create_customer(CustomerRecord(name='Inactive', first_service_date='2026-09-01'))
    db.set_customer_active(inactive, False)
    repeat = db.create_customer(CustomerRecord(name='Repeated service', frequency_value=1, frequency_unit='months', first_service_date='2026-08-01'))
    db.create_job(JobRecord(repeat, status='Completed', completed_date='2026-09-08'))
    trashed = db.create_job(JobRecord(repeat, status='Completed', completed_date='2026-10-01'))
    db.trash_job(trashed)
    result = db.home_overview(today)
    assert [(c['id'], c['next_due']) for c in result['needs_booking']] == [(overdue, '2026-09-01'), (end, '2026-10-08'), (repeat, '2026-10-08')]
    assert db.get_customer(end)['suburb'] == 'Coogee'
    db.restore_job(trashed)
    assert repeat not in {c['id'] for c in db.home_overview(today)['needs_booking']}


def test_distant_due_dates_do_not_appear_on_the_home_page(context, today):
    db = context.db
    cid = db.create_customer(CustomerRecord(name='Very long interval', frequency_value=3650, frequency_unit='years'))
    db.create_job(JobRecord(cid, status='Completed', completed_date='2026-10-01'))
    assert db.home_overview()['needs_booking'] == []


@pytest.mark.parametrize('anchor,end,outside', [('2026-12-29','2027-01-04','2027-01-05'), ('2024-02-28','2024-03-05','2024-03-06')])
def test_seven_day_window_crosses_years_and_leap_days(context, anchor, end, outside):
    from datetime import date
    db = context.db
    cid = db.create_customer(CustomerRecord(name='Calendar boundary'))
    first = db.create_job(JobRecord(cid, scheduled_date=anchor))
    last = db.create_job(JobRecord(cid, scheduled_date=end))
    db.create_job(JobRecord(cid, scheduled_date=outside))
    overview = db.home_overview(date.fromisoformat(anchor))
    assert overview['next7_jobs'] == 2
    assert [job['id'] for job in overview['upcoming']] == [first, last]
