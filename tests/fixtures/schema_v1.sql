
CREATE TABLE customers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL CHECK(length(trim(name)) > 0),
 business_name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
 address_line_1 TEXT NOT NULL DEFAULT '', address_line_2 TEXT NOT NULL DEFAULT '',
 suburb TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT '', postcode TEXT NOT NULL DEFAULT '',
 frequency_value INTEGER, frequency_unit TEXT NOT NULL DEFAULT '', first_service_date TEXT NOT NULL DEFAULT '',
 default_job_type TEXT NOT NULL DEFAULT '', default_equipment TEXT NOT NULL DEFAULT '[]',
 default_fee_cents INTEGER CHECK(default_fee_cents IS NULL OR (typeof(default_fee_cents)='integer' AND default_fee_cents >= 0)),
 default_payment_type TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 custom_fields TEXT NOT NULL DEFAULT '{}', search_text TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CHECK((frequency_value IS NULL AND frequency_unit='') OR
 (typeof(frequency_value)='integer' AND frequency_value > 0 AND frequency_unit IN ('days','weeks','months','years')))
);
CREATE TABLE jobs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
 scheduled_date TEXT NOT NULL DEFAULT '', completed_date TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'Scheduled' CHECK(status IN ('Scheduled','In progress','Completed','Cancelled')),
 job_type TEXT NOT NULL DEFAULT '', equipment TEXT NOT NULL DEFAULT '[]',
 fee_cents INTEGER CHECK(fee_cents IS NULL OR (typeof(fee_cents)='integer' AND fee_cents >= 0)),
 payment_type TEXT NOT NULL DEFAULT '',
 payment_status TEXT NOT NULL DEFAULT 'Unpaid' CHECK(payment_status IN ('Unpaid','Invoiced','Part-paid','Paid')),
 notes TEXT NOT NULL DEFAULT '', custom_fields TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT,
 CHECK((status='Completed' AND completed_date<>'') OR (status<>'Completed' AND completed_date=''))
);
CREATE INDEX idx_customers_name ON customers(name COLLATE NOCASE);
CREATE INDEX idx_customers_active ON customers(active);
CREATE INDEX idx_jobs_customer ON jobs(customer_id);
CREATE INDEX idx_jobs_schedule ON jobs(scheduled_date, status, deleted_at);
CREATE INDEX idx_jobs_completed ON jobs(completed_date, status, deleted_at);
CREATE TABLE crm_schema (version INTEGER NOT NULL);
INSERT INTO crm_schema VALUES(1);
