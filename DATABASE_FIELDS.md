# Database and field map

One encrypted SQLCipher database holds both entities. `jobs.customer_id` references `customers.id`, with deletion restricted. Foreign keys are enabled for every connection.

## Customers

| Field | Stored type | Purpose |
|---|---|---|
| id | Integer primary key | Stable customer identifier |
| name | Text, required | Client name |
| business_name | Text | Optional business |
| phone, email | Text | Contact details; phones are not numeric fields |
| address_line_1, address_line_2 | Text | Street address |
| suburb, state, postcode | Text | Australian address components, preserving postcode zeros |
| frequency_value | Integer or NULL | Positive repeat interval; NULL for one-off/as needed |
| frequency_unit | Text | days, weeks, months, years, or empty |
| first_service_date | ISO date text or empty | Initial due date before first completed job |
| default_job_type | Text | Usual nature of job |
| default_equipment | JSON array | Multiple equipment selections |
| default_fee_cents | Integer or NULL | AUD cents; zero is distinct from unspecified |
| default_payment_type | Text | Usual payment method |
| notes | Text | Customer/access notes |
| active | 0 or 1 | Deactivated customers retained with history |
| custom_fields | JSON object | Configurable fields keyed by stable identifier |
| search_text | Text | Normalised searchable data and digit-only phone copy |
| created_at, updated_at | UTC ISO timestamp | Audit timestamps |

The Python/form field `default_fee` accepts decimal AUD text and maps to `default_fee_cents` in storage.

## Jobs

| Field | Stored type | Purpose |
|---|---|---|
| id | Integer primary key | Stable job identifier |
| customer_id | Integer foreign key, required | Linked customer |
| scheduled_date | ISO date text or empty | Planned service date |
| completed_date | ISO date text or empty | Required only for Completed status |
| status | Controlled text | Scheduled, In progress, Completed, Cancelled |
| job_type | Text | Actual nature of this visit |
| equipment | JSON array | Actual equipment required |
| fee_cents | Integer or NULL | Agreed charge for this job, preserving historical fee |
| payment_type | Text | Actual payment method |
| payment_status | Controlled text | Unpaid, Invoiced, Part-paid, Paid |
| notes | Text | Visit notes |
| custom_fields | JSON object | Job-specific configured values |
| created_at, updated_at | UTC ISO timestamp | Audit timestamps |
| deleted_at | UTC timestamp or NULL | Soft deletion / Trash |

The Python/form field `fee` accepts decimal AUD text and maps to `fee_cents`.

`crm_schema.version` records schema version 1. Unsupported versions stop startup; later versions should introduce explicit migrations. SQL constraints protect the relationship, valid statuses, whole-cent money, positive intervals and completion-date/status consistency. Application validation also checks real dates, money precision, contact formats and configured required fields/choices.

## Derived values

- Jobs completed: count completed non-deleted jobs for a customer.
- Last job: latest completion date among those jobs.
- Next due: last job plus current recurrence; otherwise first_service_date.
- Next scheduled: earliest date for a non-deleted Scheduled/In progress job.

These are computed rather than stored as mutable customer counters.

## Configuration

`crm-settings.json` defines separate `customer_fields` and `job_fields` arrays. Each definition holds key, label, field_type, required, browse_column, options and enabled. Global equipment/job-type/payment-method lists feed both customer defaults and actual job forms.

Core fields map to native columns. Additional fields live in each record's encrypted `custom_fields` object, so adding a field does not require altering a table. Field settings contain definitions and options, not customer records. Custom field types and keys stay fixed through the configuration screen.
