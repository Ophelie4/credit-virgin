"""Deterministic category guardrails applied after Gemini extraction.

Gemini is good at reading documents; these rules keep a handful of categories that drive the score
(salary, rent, savings, own-account transfers) from drifting between uploads.
"""
import re

from ..models import ExtractedDocument

_OWN_ACCOUNT = re.compile(r"own account|propre compte|mon compte|my (own )?account|portefeuille mobile|mobile wallet|"
                          r"to (my )?wallet|from (my )?bank|vers (le )?compte|konti yanjye", re.I)
_SALARY = re.compile(r"salaire|salary|salario|salário|wages|paie\b|payroll|umushahara", re.I)
_RENT = re.compile(r"\brent\b|loyer|landlord|propri[eé]taire|alquiler|aluguel|ubukode|lwaye", re.I)
_SAVINGS = re.compile(r"ikimina|tontine|chama|savings|[eé]pargne|ahorro|poupan[cç]a|kuzigama", re.I)
_LOAN = re.compile(r"loan|pr[eê]t\b|remboursement|pr[eé]stamo|empr[eé]stimo|inguzanyo", re.I)
_UTIL = re.compile(r"electric|electricity|water|utility|gaz|internet|wifi|[eé]lectricit[eé]|eau\b|token", re.I)
_AIRTIME = re.compile(r"airtime|data bundle|recharge|forfait", re.I)
_EDU = re.compile(r"school fees|tuition|frais scolaires|minerval|amashuri", re.I)
_CASH = re.compile(r"withdrawal|retrait|cash out|guichet|\batm\b", re.I)
_MERCHANT = re.compile(r"merchant|supermarket|pharmacy|restaurant|shop|market|boutique|pharmacie", re.I)
_TRANSPORT = re.compile(r"moto|taxi|bus|transport|uber|fuel|carburant", re.I)
_FEES = re.compile(r"frais de tenue|account fee|maintenance fee|service charge|bank charge", re.I)


def normalize(doc: ExtractedDocument) -> ExtractedDocument:
    for t in doc.transactions:
        d = f"{t.description} {t.counterparty or ''}"
        if _OWN_ACCOUNT.search(d) and not _SALARY.search(d):
            t.category = "transfer_in" if t.direction == "in" else "transfer_out"
        elif _SALARY.search(d) and t.direction == "in":
            t.category = "salary"
        elif _RENT.search(d) and t.direction == "out":
            t.category = "rent"
        elif _SAVINGS.search(d) and t.direction == "out":
            t.category = "savings"
        elif _LOAN.search(d) and t.direction == "out":
            t.category = "loan_repayment"
        elif _FEES.search(d) and t.direction == "out":
            t.category = "fees"
        elif t.category == "other" and t.direction == "out":
            for rx, cat in ((_UTIL, "utilities"), (_AIRTIME, "airtime"), (_EDU, "education"), (_CASH, "cash"),
                            (_MERCHANT, "merchant"), (_TRANSPORT, "transport")):
                if rx.search(d):
                    t.category = cat
                    break
    if doc.doc_type == "rent_receipts":
        for t in doc.transactions:
            t.direction, t.category = "out", "rent"
    return doc
