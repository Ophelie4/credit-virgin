"""Gemini: document extraction (any language) and score explanations (chosen language)."""
import asyncio
import hashlib
import json
import logging
from pathlib import Path

from google import genai
from google.genai import types

from ..config import settings
from ..models import ExtractedDocument

log = logging.getLogger("creditvirgin.gemini")

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        opts = {"timeout": settings.gemini_timeout_ms}
        try:  # one attempt per model; we do our own fallback across models
            opts["retry_options"] = types.HttpRetryOptions(attempts=1)
        except Exception:  # noqa: BLE001  (older SDKs)
            pass
        _client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(**opts))
    return _client


EXTRACTION_PROMPT = """You are a meticulous financial document analyst.
The attached document is a financial record (mobile money statement, bank statement, rent receipts, payslip,
or utility bills) from anywhere in the world, in any language.

Extract EVERY transaction row into structured JSON. Rules:
- Keep the original description text; do not translate it.
- direction is 'in' if money entered this account, 'out' if it left.
- amount is positive and excludes fees; put a separately listed fee in 'fee'.
- balance is the running balance after the row if the document shows one, else null.
- Dates: convert to ISO YYYY-MM-DD. Day/month order follows the document's locale (dd/mm for French and most of Africa).
- Categories: salary (wages/income from an employer), rent (payments to a landlord or receipts for rent), utilities
  (electricity, water, gas, internet), savings (transfers to savings, savings groups like ikimina/tontine/chama),
  loan_repayment, transfer_in / transfer_out (ONLY moves between the person's own accounts, e.g. bank to mobile wallet;
  money from family or friends is 'other'),
  merchant (shops, restaurants), cash (ATM/agent withdrawals or deposits), fees (bank/account charges),
  airtime, education (school fees), health, transport, other.
- For a rent receipt document, each receipt is one 'out' transaction with category 'rent' and direction 'out'.
- language is the ISO 639-1 code of the document's language. currency is the ISO 4217 code.
- Be exhaustive and exact with numbers. Thousands separators may be commas, spaces or dots.
"""


def _models() -> list[str]:
    extra = [m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()]
    return [settings.gemini_model] + [m for m in extra if m != settings.gemini_model]


def _retryable(e: Exception) -> bool:
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    msg = str(e)
    return code in (429, 500, 502, 503, 504) or any(x in msg for x in ("429", "503", "504", "DEADLINE", "imed out", "Timeout"))


def _generate(contents, config):
    """Call Gemini, falling through the model list on quota/overload errors."""
    last: Exception | None = None
    for model in _models():
        try:
            return client().models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:  # noqa: BLE001
            last = e
            if _retryable(e):
                log.warning("%s unavailable (%s); trying next model", model, str(e)[:80])
                continue
            raise
    raise last if last else RuntimeError("no Gemini model configured")


async def extract_document(pdf_bytes: bytes, mime_type: str, filename: str, text: str = "") -> ExtractedDocument:
    """Text layer if the PDF has one (fast, cheap); otherwise the file itself (scans, photos)."""
    if text and len(text) > 200:
        contents = [f"Filename: {filename}\n\nDocument text (extracted from the PDF, layout preserved line by line):\n"
                    f"<<<\n{text}\n>>>\n\n{EXTRACTION_PROMPT}"]
    else:
        contents = [types.Part.from_bytes(data=pdf_bytes, mime_type=mime_type), f"Filename: {filename}\n\n{EXTRACTION_PROMPT}"]

    def _call() -> ExtractedDocument:
        resp = _generate(
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExtractedDocument,
                temperature=0,
            ),
        )
        parsed = resp.parsed
        if isinstance(parsed, ExtractedDocument):
            return parsed
        return ExtractedDocument.model_validate_json(resp.text)

    return await asyncio.to_thread(_call)


def _cache_path(kind: str, key: str) -> Path:
    d = Path(settings.extraction_cache_dir); d.mkdir(parents=True, exist_ok=True)
    return d / f"{kind}_{hashlib.sha256(key.encode()).hexdigest()[:24]}.json"


LANG_NAMES = {
    "en": "English", "fr": "French", "rw": "Kinyarwanda", "es": "Spanish", "ht": "Haitian Creole", "pt": "Portuguese",
}


async def explain_score(summary: dict, language: str, audience: str = "applicant") -> str:
    """Plain-language explanation of the score in the requested language."""
    lang = LANG_NAMES.get(language, "English")
    if audience == "landlord":
        who = ("a landlord or lender reading a one-page report about an applicant with no local credit history. "
               "Be factual and neutral; it is evidence for their decision, not a recommendation.")
    else:
        who = ("the applicant themselves, a newcomer with no local credit history. Be warm, clear and specific, "
               "and tell them the one thing that would raise their score most.")
    prompt = f"""Write in {lang} only. Audience: {who}
Write 3 short sentences (max 70 words total), no headings, no bullet points, no emojis.
Use the numbers below; do not invent anything that is not in them. Refer to the score as a "cashflow trust score",
never as a credit score.

Data (JSON): {summary}
"""

    cache = _cache_path("explain", json.dumps(summary, sort_keys=True, default=str) + language + audience)
    if cache.exists():
        return cache.read_text()

    def _call() -> str:
        resp = _generate(contents=prompt, config=types.GenerateContentConfig(temperature=0.4))
        return (resp.text or "").strip()

    try:
        text = await asyncio.to_thread(_call)
        if text:
            cache.write_text(text)
        return text
    except Exception as e:  # explanation is a nice-to-have; never break the page
        log.warning("explain_score failed: %s", e)
        return ""
