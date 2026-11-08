import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "salary", "rent", "utilities", "savings", "loan_repayment", "transfer_in", "transfer_out",
    "merchant", "cash", "fees", "airtime", "education", "health", "transport", "other",
]
DocType = Literal["mobile_money", "bank_statement", "rent_receipts", "payslip", "utility_bills", "other"]


class ExtractedTransaction(BaseModel):
    date: dt.date = Field(description="Transaction date, ISO format YYYY-MM-DD")
    description: str = Field(description="Original description text, as written in the document")
    direction: Literal["in", "out"] = Field(description="'in' if money came into this account, 'out' if it left")
    amount: float = Field(description="Positive amount, excluding fees")
    fee: float = Field(default=0, description="Transaction fee if listed separately, else 0")
    balance: float | None = Field(default=None, description="Running balance after this transaction if shown")
    category: Category = Field(description="Best category for this transaction")
    counterparty: str | None = Field(default=None, description="Who the money went to or came from, if identifiable")


class ExtractedDocument(BaseModel):
    source_name: str = Field(description="Institution or provider named on the document")
    doc_type: DocType
    account_holder: str | None = None
    currency: str = Field(description="ISO 4217 currency code, e.g. RWF, KES, USD")
    language: str = Field(description="ISO 639-1 code of the document's language, e.g. en, fr, rw")
    period_start: dt.date | None = None
    period_end: dt.date | None = None
    opening_balance: float | None = None
    transactions: list[ExtractedTransaction]


class DocumentOut(BaseModel):
    id: str
    filename: str
    doc_type: str
    source_name: str | None
    currency: str | None
    language: str | None
    period_start: dt.date | None
    period_end: dt.date | None
    tx_count: int
    created_at: str


class ScoreFactor(BaseModel):
    key: str
    label: str
    points: int
    max_points: int
    detail: str


class Check(BaseModel):
    key: str
    label: str
    status: Literal["pass", "warn", "fail", "skip"]
    detail: str


class ScoreOut(BaseModel):
    score: int
    band: str
    factors: list[ScoreFactor]
    checks: list[Check]
    months_covered: int
    currency: str | None
    avg_monthly_income: float | None
    avg_monthly_income_usd: float | None
    avg_rent: float | None
    rent_to_income: float | None
    on_time_rent_months: int
    explanation: str | None = None
