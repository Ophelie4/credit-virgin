# Credit Virgin

**No credit score? You still have receipts.**

Newcomers to the US — immigrants, international students — arrive financially invisible. Years of paying rent on time and
saving every month back home count for nothing, so they get turned down for apartments, cards and loans.

Credit Virgin turns the financial paper trail people already have (mobile money statements, bank statements, rent receipts,
in any language) into a **verified cashflow trust score** with a one-page report a landlord or lender can actually read.

Built solo at SharkByte 2026 (Miami Dade College).

## Two sides

- **Renters** upload documents, get a verified cashflow trust score, and see every Miami listing sorted into
  *within reach*, *almost* (with the one tip that would get them there) and *not yet*. They apply by sending their
  verified report. Nothing is shared unless they choose to send it.
- **Landlords** list homes with their own requirements (minimum score, maximum rent-to-income), then review
  applications in an inbox: score, checks, documents, note. Approve or decline in one click.

Requirements are set by each landlord and apply equally to every applicant; the renter controls who sees their report.

## How it works

1. **Upload anything.** PDFs or photos, in any language. Gemini extracts every transaction into structured data.
2. **The story has to add up.** Documents are cross-checked against each other: running balances must reconcile row by row,
   rent receipts must match payments leaving an account, transfers out of one account must arrive in another.
   A failed check caps the score. Evidence that disagrees isn't evidence.
3. **An explainable score.** Five factors (income stability, payment consistency, savings behaviour, balance health,
   history length), every point with its reason. Gemini writes the plain-language summary in the reader's language.
   Payment consistency counts recurring bills (electricity, water, phone, loan instalments, school fees) as well as
   rent, so someone who lives with family and pays no rent can still show a payment history.
4. **Share one page.** A link or QR code opens a read-only report for the landlord, in English, French, Kinyarwanda,
   Spanish, Haitian Creole or Portuguese.

## Stack

| Layer | Tech |
|---|---|
| Document AI | **Google Gemini** (multimodal extraction with a strict JSON schema; multilingual explanations) |
| Database | **Tiger Data** (TimescaleDB): transactions as a hypertable, monthly cashflow as a continuous aggregate |
| Auth | **Auth0** (SPA login, JWT-verified API) |
| Backend | Python, FastAPI, asyncpg |
| Frontend | React, Vite, Tailwind, Recharts |
| Sharing | Cloudflare quick tunnel (`share.sh`) for a public demo link |

## Run it locally

```bash
bash setup.sh            # checks tools, installs deps, creates .env files
# edit backend/.env: TIMESCALE_SERVICE_URL, GEMINI_API_KEY
bash dev.sh              # http://localhost:5173
```

No login needed for the demo: the header switch toggles between the demo renter and the demo landlord, and
"Try it with sample documents" on the Upload page loads a fictional applicant. Six fictional Miami listings are
seeded on first start. With Auth0 configured, real accounts pick a role on first sign-in.

Demo documents live in `samples/` (fictional applicant, fictional providers). Upload the three genuine ones for a clean
score, then add `TAMPERED_rent_receipts_2024.pdf` to watch the verification layer catch it.

## Share a public link

With the app running (`bash dev.sh`), run this in a second terminal:

```bash
bash share.sh            # prints https://<random-words>.trycloudflare.com
```

Anyone with the link can use the demo while the laptop is awake. Login is offered only on hosts listed in
`VITE_AUTH0_HOSTS` (Auth0 must allow them as callback URLs); everywhere else the app runs in demo mode.

## Privacy

Documents are used only to calculate the score. Landlords see the score report, never the files, and only when the
renter applies or sends a link. Any document can be removed, or everything reset, at any time.

## Tests

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q
```

41 tests, no database or API key needed. They cover the scoring rules, category guardrails in six languages, every
verification check, home matching, and the whole demo story: the sample PDFs are read with the offline parser, the
genuine set scores 92 with all four checks passing, and the tampered receipts are caught and cap the score at 45.
GitHub Actions runs them on every push.

## Offline demo

Sample listing photos and walkthrough videos are downloaded once into `backend/media_cache/` when the backend starts,
then served locally from `/api/media`, so the tours keep playing if the venue Wi-Fi drops.

## Project layout

```
backend/app
  main.py            FastAPI app, CORS, schema init on startup
  schema.sql         Tiger Data schema: hypertable + continuous aggregate
  services/gemini.py Extraction prompt + schema, explanation generator
  services/scoring.py  Explainable 0-100 score
  services/verification.py  Cross-document checks
  routers/           documents, score/cashflow, share/report, marketplace (listings, matching, applications)
  services/local_parser.py  Text-layer statement parser, used when Gemini is unavailable
  routers/media.py   Local cache for listing photos and walkthrough videos
backend/tests        pytest suite (runs offline)
frontend/src
  i18n/              6 languages, all UI strings
  pages/             Landing, Upload, Dashboard, Report (public), Homes, HomeDetail, MyApplications, Landlord
  components/ScoreParts.tsx  dial, factors, checks, charts
samples/             demo PDFs + generator
```
