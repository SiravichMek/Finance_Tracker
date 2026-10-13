"""Deterministic parsers for KBank and Krungsri transaction notification emails."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

BANGKOK = ZoneInfo("Asia/Bangkok")


def _field(text: str, label: str) -> str | None:
    pattern = rf"^\s*{re.escape(label)}\s*:\s*(.*?)\s*$"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def _amount(value: str | None) -> Decimal | None:
    if not value:
        return None
    cleaned = value.replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = re.sub(r"\s+", " ", value.strip())
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=BANGKOK)
        except ValueError:
            pass
    return None


def parse_krungsri(text: str) -> dict[str, Any] | None:
    if "krungsri app" not in text.lower() and "ORDER ID:" not in text.upper():
        return None
    status = _field(text, "Transaction Result")
    if status and status.lower() != "success":
        return None
    amount = _amount(_field(text, "Amount (THB)"))
    occurred_at = _date(_field(text, "Date/Time"))
    if amount is None or occurred_at is None:
        return None
    return {
        "bank": "krungsri",
        "transaction_type": _field(text, "Type of Transaction") or "Unknown",
        "direction": "outgoing",
        "amount": amount,
        "fee": _amount(_field(text, "Fee (THB)")) or Decimal("0.00"),
        "currency": "THB",
        "occurred_at": occurred_at,
        "counterparty": _field(text, "To Biller"),
        "status": status or "Success",
        "bank_transaction_id": _field(text, "ORDER ID") or _field(text, "Reference No."),
        "account_hint": _field(text, "From Account"),
        "category": "Bills & Utilities" if (_field(text, "Type of Transaction") or "").lower() == "bill payment" else "Uncategorized",
    }


def parse_kbank(text: str) -> dict[str, Any] | None:
    if "k plus service" not in text.lower() and "promptpay funds transfer" not in text.lower():
        return None
    # This sample identifies success in the subject. Reject explicit failures if present.
    if re.search(r"\b(failed|failure|unsuccessful)\b", text, flags=re.IGNORECASE):
        return None
    amount = _amount(_field(text, "Amount (THB)"))
    occurred_at = _date(_field(text, "Transaction Date"))
    if amount is None or occurred_at is None:
        return None
    return {
        "bank": "kbank",
        "transaction_type": "PromptPay Funds Transfer",
        "direction": "outgoing",
        "amount": amount,
        "fee": _amount(_field(text, "Fee (THB)")) or Decimal("0.00"),
        "currency": "THB",
        "occurred_at": occurred_at,
        "counterparty": _field(text, "Received Name") or _field(text, "To Account"),
        "status": "Success",
        "bank_transaction_id": _field(text, "Transaction Number"),
        "account_hint": _field(text, "From Account"),
        # A person-to-person transfer is not automatically treated as consumption.
        "category": "Transfer / Review",
    }


def parse_transaction(text: str) -> dict[str, Any] | None:
    return parse_krungsri(text) or parse_kbank(text)
