-- Run this in pgAdmin while connected to the skeptic_engine database.

DROP TABLE IF EXISTS sample_general_ledger;

CREATE TABLE sample_general_ledger (
    transaction_id TEXT PRIMARY KEY,
    posted_at TIMESTAMP NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_period TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    supplier_country TEXT NOT NULL,
    gl_account TEXT NOT NULL,
    account_name TEXT NOT NULL,
    department TEXT NOT NULL,
    cost_center TEXT NOT NULL,
    region TEXT NOT NULL,
    currency TEXT NOT NULL,
    fx_rate_used NUMERIC(12, 6) NOT NULL,
    amount_original NUMERIC(14, 2) NOT NULL,
    amount_usd NUMERIC(14, 2) NOT NULL,
    debit NUMERIC(14, 2) NOT NULL,
    credit NUMERIC(14, 2) NOT NULL,
    invoice_number TEXT NOT NULL,
    po_number TEXT,
    payment_method TEXT NOT NULL,
    posted_by TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    document_status TEXT NOT NULL,
    related_party_flag TEXT NOT NULL,
    risk_hint TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE INDEX idx_sample_gl_posted_at ON sample_general_ledger (posted_at);
CREATE INDEX idx_sample_gl_vendor ON sample_general_ledger (vendor_name);
CREATE INDEX idx_sample_gl_risk_hint ON sample_general_ledger (risk_hint);
