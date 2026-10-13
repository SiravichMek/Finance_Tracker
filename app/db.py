from __future__ import annotations
import json
import os
import psycopg
from psycopg.types.json import Jsonb

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
  id BIGSERIAL PRIMARY KEY,
  source_message_id TEXT NOT NULL UNIQUE,
  bank TEXT NOT NULL,
  bank_transaction_id TEXT,
  transaction_type TEXT NOT NULL,
  direction TEXT NOT NULL,
  amount NUMERIC(14,2) NOT NULL,
  fee NUMERIC(14,2) NOT NULL DEFAULT 0,
  currency CHAR(3) NOT NULL DEFAULT 'THB',
  occurred_at TIMESTAMPTZ NOT NULL,
  counterparty TEXT,
  account_hint TEXT,
  status TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'Uncategorized',
  raw_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_transactions_occurred_at ON transactions (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_bank ON transactions (bank);
CREATE TABLE IF NOT EXISTS sync_runs (
  id BIGSERIAL PRIMARY KEY,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  messages_seen INTEGER NOT NULL DEFAULT 0,
  transactions_imported INTEGER NOT NULL DEFAULT 0,
  parse_failures INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'running',
  error TEXT
);
"""


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"])


def init_db(conn):
    conn.execute(SCHEMA)
    conn.commit()


def add_transaction(conn, message_id: str, tx: dict) -> bool:
    fields = dict(tx)
    occurred_at = fields.pop("occurred_at")
    cur = conn.execute(
        """INSERT INTO transactions
        (source_message_id, bank, bank_transaction_id, transaction_type, direction,
         amount, fee, currency, occurred_at, counterparty, account_hint, status, category, raw_fields)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (source_message_id) DO NOTHING RETURNING id""",
        (message_id, fields["bank"], fields.get("bank_transaction_id"), fields["transaction_type"],
         fields["direction"], fields["amount"], fields["fee"], fields["currency"], occurred_at,
         fields.get("counterparty"), fields.get("account_hint"), fields["status"], fields["category"],
         Jsonb({k: str(v) for k, v in fields.items()})),
    )
    inserted = cur.fetchone() is not None
    conn.commit()
    return inserted
