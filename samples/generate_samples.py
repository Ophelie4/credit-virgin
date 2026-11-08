"""Generate fictional demo documents for one applicant, 'Aline Uwase' (not a real person).

The three genuine documents agree with each other:
  - Banque Umurage (FR): salary in on the 28th, transfer to mobile wallet on the 29th, loan repayment, fees.
  - KivuPay wallet (EN): receives the bank transfer, pays rent, utilities, savings group, daily spending.
  - Rent receipts: 12 months, 120,000 RWF, paid on the 2nd via mobile money.
The tampered receipts claim 150,000 for Sep-Dec, which the wallet contradicts.

Run:  python3 generate_samples.py
"""
import datetime as dt
import random
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

random.seed(7)
OUT = Path(__file__).parent
ss = getSampleStyleSheet()
RENT, SALARY, TRANSFER = 120_000, 320_000, 300_000


def footer(c, d):
    c.saveState(); c.setFont("Helvetica", 7); c.setFillColor(colors.grey)
    c.drawString(40, 25, "SAMPLE DATA FOR SOFTWARE DEMO - fictional provider and customer - not a real statement")
    c.drawRightString(555, 25, "Page %d" % d.page); c.restoreState()


def fmt(n):
    return f"{n:,.0f}"


def build(path, title, sub, info, head, rows, accent, widths):
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=45)
    el = [Paragraph(f"<font size=18 color='{accent}'><b>{title}</b></font>", ss["Normal"]), Spacer(1, 8),
          Paragraph(sub, ss["Normal"]), Spacer(1, 8)]
    el += [Paragraph(l, ss["Normal"]) for l in info]
    el.append(Spacer(1, 12))
    t = Table([head] + rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(accent)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
        ("ALIGN", (-3, 0), (-1, -1), "RIGHT"), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey)]))
    el.append(t)
    doc.build(el, onFirstPage=footer, onLaterPages=footer)


def days(start, end):
    d = start
    while d < end:
        yield d
        d += dt.timedelta(days=1)


# 1) Bank statement, French, Jul-Dec 2024 (current account)
bal, rows = 410_000, []
for d in days(dt.date(2024, 7, 1), dt.date(2025, 1, 1)):
    ev = []
    if d.day == 3: ev.append(("Frais de tenue de compte", "d", 1_500))
    if d.day == 12: ev.append(("Remboursement pret - echeance mensuelle", "d", 38_500))
    if d.day == 28: ev.append(("Virement recu - salaire KIGALI FRESH MARKET LTD", "c", SALARY))
    if d.day == 29: ev.append(("Transfert vers portefeuille mobile KivuPay 07XX XXX 412", "d", TRANSFER))
    if d.day == 16 and d.month in (8, 11): ev.append(("Retrait guichet automatique", "d", 20_000))
    for desc, k, a in ev:
        bal += a if k == "c" else -a
        rows.append([d.strftime("%d/%m/%Y"), desc, fmt(a) if k == "d" else "", fmt(a) if k == "c" else "", fmt(bal)])
build(OUT / "banque_umurage_releve_de_compte.pdf", "Banque Umurage", "Releve de compte : 01 juillet 2024 - 31 decembre 2024",
      ["<b>Titulaire :</b> Aline Uwase", "<b>Compte courant :</b> XXXX-XXXX-0412", "<b>Devise :</b> Franc rwandais (RWF)",
       "<b>Solde d'ouverture :</b> 410 000"],
      ["Date", "Libelle", "Debit", "Credit", "Solde"], rows, "#1d3557", [60, 270, 60, 60, 65])
print("bank", len(rows), bal)

# 2) Mobile money wallet, English, Jul-Dec 2024
bal, rows, n = 320_000, [], 0
for d in days(dt.date(2024, 7, 1), dt.date(2025, 1, 1)):
    ev = []
    if d.day == 29: ev.append(("Transfer received from Banque Umurage - own account", "in", TRANSFER))
    if d.day == 2: ev.append(("Payment to landlord - J. Habimana (rent)", "out", RENT))
    if d.day == 5: ev.append(("Bill payment - electricity token", "out", random.choice([12_000, 15_000, 10_000])))
    if d.day == 6: ev.append(("Bill payment - water utility", "out", random.choice([6_500, 7_200, 8_000])))
    if d.day == 10: ev.append(("Transfer to savings group (ikimina)", "out", 30_000))
    if d.day == 15: ev.append(("Airtime and data bundle", "out", 5_000))
    if d.day == 20 and d.month in (8, 10, 12): ev.append(("School fees - sibling", "out", 25_000))
    if random.random() < 0.22:
        ev.append((random.choice(["Merchant payment - supermarket", "Merchant payment - pharmacy", "Moto taxi payment",
                                  "Merchant payment - restaurant", "Cash withdrawal - agent"]), "out",
                   random.choice([2_500, 4_000, 7_500, 9_000, 12_000])))
    for desc, k, a in ev:
        n += 1
        fee = 0 if k == "in" else (100 if a < 10_000 else 250)
        bal += a if k == "in" else -(a + fee)
        rows.append([d.strftime("%d/%m/%Y"), f"KP{240000 + n * 37}", desc, fmt(a) if k == "in" else "",
                     fmt(a) if k == "out" else "", fmt(fee), fmt(bal)])
assert bal > 0
build(OUT / "kivupay_mobile_money_statement.pdf", "KivuPay Mobile Money", "Account Statement: 01 July 2024 - 31 December 2024",
      ["<b>Customer:</b> Aline Uwase", "<b>Wallet number:</b> 07XX XXX 412", "<b>Currency:</b> Rwandan Franc (RWF)",
       "<b>Opening balance:</b> 320,000"],
      ["Date", "Ref", "Description", "Money in", "Money out", "Fee", "Balance"], rows, "#0b6e4f", [55, 50, 200, 55, 55, 35, 60])
print("wallet", len(rows), bal)


# 3) Rent receipts, Jan-Dec 2024 (genuine) and a tampered copy
def receipts(path, amounts, title_suffix=""):
    rows = [[f"02/{m:02d}/2024", f"REC-2024-{m:02d}", f"Rent for {dt.date(2024, m, 1).strftime('%B %Y')}", fmt(amounts[m - 1]),
             "Mobile money", "Paid on time"] for m in range(1, 13)]
    build(path, "Rent Payment Record" + title_suffix, "Tenant: Aline Uwase | Landlord: Jean Habimana | Kicukiro, Kigali",
          [f"<b>Monthly rent:</b> {fmt(amounts[-1])} RWF", "<b>Lease period:</b> January 2024 - December 2024"],
          ["Date paid", "Receipt no.", "Period", "Amount (RWF)", "Method", "Status"], rows, "#7b2d26", [60, 75, 130, 70, 80, 80])


receipts(OUT / "rent_payment_receipts_2024.pdf", [RENT] * 12)
receipts(OUT / "TAMPERED_rent_receipts_2024.pdf", [RENT] * 8 + [150_000] * 4)
print("receipts done")
