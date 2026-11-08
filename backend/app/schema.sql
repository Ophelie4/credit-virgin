-- Credit Virgin schema for Tiger Data (TimescaleDB).
-- Statements are executed one at a time by db.init_schema(); keep one statement per block.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS applicants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth0_sub   TEXT UNIQUE,
    display_name TEXT,
    email       TEXT,
    home_country TEXT,
    language    TEXT NOT NULL DEFAULT 'en',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    applicant_id    UUID NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    doc_type        TEXT NOT NULL,            -- mobile_money | bank_statement | rent_receipts | payslip | utility_bills | other
    source_name     TEXT,                     -- e.g. "KivuPay Mobile Money"
    account_holder  TEXT,
    currency        TEXT,
    language        TEXT,
    period_start    DATE,
    period_end      DATE,
    opening_balance NUMERIC,
    status          TEXT NOT NULL DEFAULT 'processed',
    tx_count        INT NOT NULL DEFAULT 0,
    raw_json        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Time-series table of extracted transactions (hypertable)
CREATE TABLE IF NOT EXISTS transactions (
    time          TIMESTAMPTZ NOT NULL,
    id            UUID NOT NULL DEFAULT gen_random_uuid(),
    applicant_id  UUID NOT NULL,
    document_id   UUID NOT NULL,
    doc_type      TEXT NOT NULL,
    description   TEXT,
    direction     TEXT NOT NULL,              -- in | out
    amount        NUMERIC NOT NULL,
    fee           NUMERIC NOT NULL DEFAULT 0,
    balance       NUMERIC,
    currency      TEXT,
    category      TEXT NOT NULL DEFAULT 'other',
    counterparty  TEXT,
    PRIMARY KEY (time, id)
);

SELECT create_hypertable('transactions', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS transactions_applicant_time_idx ON transactions (applicant_id, time DESC);

CREATE INDEX IF NOT EXISTS transactions_document_idx ON transactions (document_id);

-- Continuous aggregate: monthly cashflow per applicant, refreshed automatically
CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_cashflow
WITH (timescaledb.continuous) AS
SELECT
    applicant_id,
    time_bucket('1 month', time) AS month,
    SUM(amount) FILTER (WHERE direction = 'in')  AS inflow,
    SUM(amount) FILTER (WHERE direction = 'out') AS outflow,
    SUM(amount) FILTER (WHERE direction = 'out' AND category = 'rent')    AS rent_paid,
    SUM(amount) FILTER (WHERE direction = 'out' AND category = 'savings') AS saved,
    SUM(amount) FILTER (WHERE direction = 'in'  AND category = 'salary')  AS salary,
    COUNT(*) AS tx_count,
    MIN(balance) AS min_balance
FROM transactions
WHERE doc_type <> 'rent_receipts'                          -- receipts duplicate payments already in statements
  AND category NOT IN ('transfer_in', 'transfer_out')      -- moves between the applicant's own accounts
GROUP BY applicant_id, month
WITH NO DATA;

SELECT add_continuous_aggregate_policy('monthly_cashflow',
    start_offset => INTERVAL '10 years',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE);

-- Share links to the landlord / lender report
CREATE TABLE IF NOT EXISTS share_links (
    token        TEXT PRIMARY KEY,
    applicant_id UUID NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
    label        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '30 days',
    views        INT NOT NULL DEFAULT 0
);

-- Marketplace ---------------------------------------------------------------
ALTER TABLE applicants ADD COLUMN IF NOT EXISTS role TEXT;

ALTER TABLE applicants ADD COLUMN IF NOT EXISTS us_monthly_income NUMERIC;

CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    landlord_id UUID NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    property_type TEXT,
    neighborhood TEXT,
    city TEXT DEFAULT 'Miami',
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    monthly_rent NUMERIC NOT NULL,
    security_deposit NUMERIC,
    first_last_required BOOLEAN DEFAULT FALSE,
    application_fee NUMERIC,
    bedrooms INT,
    bathrooms NUMERIC,
    size_sqft INT,
    lease_months INT,
    available_from DATE,
    furnished BOOLEAN DEFAULT FALSE,
    pets_allowed BOOLEAN DEFAULT FALSE,
    parking BOOLEAN DEFAULT FALSE,
    utilities_included TEXT[] DEFAULT '{}',
    amenities TEXT[] DEFAULT '{}',
    description TEXT,
    palette INT DEFAULT 0,
    min_score INT NOT NULL DEFAULT 50,
    max_rent_to_income NUMERIC NOT NULL DEFAULT 0.40,
    status TEXT NOT NULL DEFAULT 'listed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    renter_id UUID NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
    share_token TEXT REFERENCES share_links(token) ON DELETE SET NULL,
    score_at_submit INT,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    landlord_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ,
    UNIQUE (property_id, renter_id)
);

ALTER TABLE properties ADD COLUMN IF NOT EXISTS photo_urls TEXT[] DEFAULT '{}';

ALTER TABLE properties ADD COLUMN IF NOT EXISTS tour_url TEXT;
