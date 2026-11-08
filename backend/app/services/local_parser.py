"""Deterministic fallback parser for statements that have a text layer.

Used when Gemini is unavailable, so a demo or an upload is never blocked by the model provider.
It handles the common shape of a statement: one row per line, starting with a date and ending with
amounts, optionally a running balance. Direction (in/out) comes from the balance movement when a
balance column exists, otherwise from keywords.
"""
from __future__ import annotations

import datetime as dt
import io
import re

from ..models import ExtractedDocument, ExtractedTransaction

DATE = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b")
# An amount: 1,234 / 1 234 / 1.234 / 1234 (optionally with decimals and a leading minus)
AMOUNT = re.compile(r"-?\d{1,3}(?:[ ,. ]\d{3})+(?:[.,]\d{1,2})?|-?\d+(?:[.,]\d{1,2})?")

IN_WORDS = re.compile(r"\b(received|recu|reçu|credit|deposit|salary|salaire|virement recu|transfer received|refund)\b", re.I)


def pdf_text(data: bytes) -> str:
    """Text layer of a PDF, or '' if it has none (a scan). Uses pdfplumber if installed, else pure-Python pypdf."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:  # noqa: BLE001  (not installed, or failed)
        pass
    try:
        from pypdf import PdfReader
        raw = "\n".join((p.extract_text(extraction_mode="layout") or "") for p in PdfReader(io.BytesIO(data)).pages)
        # layout mode pads columns with runs of spaces; keep single spaces (thousands separators like "410 000")
        return "\n".join(re.sub(r"[ \t]{2,}", " ", l).strip() for l in raw.splitlines() if l.strip())
    except Exception:  # noqa: BLE001
        return ""


def _num(s: str) -> float:
    s = s.replace(" ", " ").strip()
    neg = s.startswith("-")
    s = s.lstrip("-")
    # decimal part only if the last separator is followed by 1-2 digits
    m = re.match(r"^(.*?)([.,](\d{1,2}))?$", s)
    whole, dec = (m.group(1), m.group(3)) if m else (s, None)
    whole = re.sub(r"[ ,.]", "", whole)
    v = float(whole or 0) + (float(f"0.{dec}") if dec else 0)
    return -v if neg else v


def _date(m: re.Match) -> dt.date | None:
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    try:
        return dt.date(y, mo, d)
    except ValueError:
        try:
            return dt.date(y, d, mo)  # mm/dd fallback
        except ValueError:
            return None


def _header_value(text: str, *labels: str) -> str | None:
    for lab in labels:
        m = re.search(rf"{lab}\s*:?\s*([^\n]+)", text, re.I)
        if m:
            return m.group(1).strip()
    return None


def _header_block(text: str) -> str:
    """Everything above the first transaction row."""
    out = []
    for line in text.splitlines():
        if DATE.match(line.strip()):
            break
        out.append(line)
    return "\n".join(out)


def _doc_type(text: str) -> str:
    head = _header_block(text).lower()
    if "receipt" in head or "rent payment record" in head or "reçu" in head and "loyer" in head:
        return "rent_receipts"
    if "mobile money" in head or "wallet" in head or "portefeuille" in head:
        return "mobile_money"
    if "payslip" in head or "fiche de paie" in head:
        return "payslip"
    return "bank_statement"


def _language(text: str) -> str:
    fr = len(re.findall(r"\b(releve|relevé|solde|libelle|libellé|virement|titulaire|devise)\b", text, re.I))
    return "fr" if fr >= 2 else "en"


def _currency(text: str) -> str:
    for code, pat in [("RWF", r"RWF|franc rwandais|rwandan franc"), ("KES", r"KES|kenyan shilling"), ("UGX", r"UGX"),
                      ("NGN", r"NGN|naira"), ("GHS", r"GHS|cedi"), ("XOF", r"XOF|CFA"), ("EUR", r"EUR|€"),
                      ("HTG", r"HTG|gourde"), ("USD", r"USD|\$")]:
        if re.search(pat, text, re.I):
            return code
    return "USD"


def _source_name(text: str) -> str:
    first = next((l.strip() for l in text.splitlines() if l.strip()), "Document")
    return first[:80]


def parse(text: str) -> ExtractedDocument | None:
    if not text or len(text) < 80:
        return None
    doc_type = _doc_type(text)
    ob_raw = _header_value(text, "opening balance", r"solde d'ouverture", "solde initial", "saldo inicial")
    opening = None
    if ob_raw:
        m = AMOUNT.search(ob_raw)
        opening = _num(m.group(0)) if m else None

    header = _header_block(text).splitlines()[-1].lower() if _header_block(text) else ""
    has_fee = bool(re.search(r"\b(fee|fees|frais|commission|tarif)\b", header))
    max_nums = 3 if has_fee else 2  # amount [+ fee] + balance; in/out share one slot per row

    rows: list[ExtractedTransaction] = []
    prev_bal = opening
    for line in text.splitlines():
        line = line.strip()
        dm = DATE.match(line)
        if not dm:
            continue
        date = _date(dm)
        if not date:
            continue
        rest = line[dm.end():].strip()
        # Peel amounts off the right end of the line
        tail_nums: list[str] = []
        words = rest.split(" ")
        while words:
            tok = words[-1]
            if AMOUNT.fullmatch(tok):
                tail_nums.insert(0, words.pop())
            elif re.fullmatch(r"\d{1,3}", tok) is None and len(words) >= 2 and AMOUNT.fullmatch(words[-2] + " " + tok):
                tail_nums.insert(0, words.pop(-2) + " " + words.pop())
            else:
                break
        if len(tail_nums) > max_nums:  # numbers that belong to the description (account no., etc.)
            words += tail_nums[: len(tail_nums) - max_nums]
            tail_nums = tail_nums[len(tail_nums) - max_nums:]
        desc = " ".join(words)
        # Drop a leading reference code (e.g. KP240037, REC-2024-01)
        desc = re.sub(r"^[A-Z]{1,4}[-]?\d[\w-]*\s+", "", desc)

        if doc_type == "rent_receipts":
            # amounts are mid-line; take the first amount-looking token >= 1000
            toks = re.findall(r"(?<![\w-])\d{1,3}(?:[ ,.\u202f]\d{3})+(?:[.,]\d{1,2})?(?![\w-])", rest)  # formatted amounts
            if not toks:  # plain numbers that aren't years or reference fragments
                toks = [n for n in re.findall(r"(?<![\w-])\d{3,}(?![\w-])", rest) if not 1900 <= int(n) <= 2100]
            nums = [_num(n) for n in toks]
            if not nums:
                continue
            rows.append(ExtractedTransaction(date=date, description=desc or "Rent payment", direction="out",
                                             amount=nums[0], category="rent", counterparty=None))
            continue

        if not tail_nums:
            continue
        vals = [_num(n) for n in tail_nums]
        balance = vals[-1] if len(vals) >= 2 else None
        amount = vals[0]
        fee = vals[1] if len(vals) >= 3 else 0.0
        if balance is not None and prev_bal is not None:
            direction = "in" if balance > prev_bal else "out"
        else:
            direction = "in" if IN_WORDS.search(desc) else "out"
        rows.append(ExtractedTransaction(date=date, description=desc, direction=direction, amount=abs(amount),
                                         fee=abs(fee), balance=balance, category="other", counterparty=None))
        if balance is not None:
            prev_bal = balance

    if not rows:
        return None
    return ExtractedDocument(
        source_name=_source_name(text), doc_type=doc_type,  # type: ignore[arg-type]
        account_holder=_header_value(text, "customer", "titulaire", "tenant", "account holder"),
        currency=_currency(text), language=_language(text),
        period_start=min(r.date for r in rows), period_end=max(r.date for r in rows),
        opening_balance=opening, transactions=rows,
    )
