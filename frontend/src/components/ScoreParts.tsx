import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useT } from "../i18n";
import type { Dict } from "../i18n/translations";
import { fmtMoney, type Cashflow, type Check, type Factor, type Score } from "../lib/api";

export function labelFor(t: (k: keyof Dict) => string, prefix: "f_" | "c_", key: string, fallback: string) {
  const k = `${prefix}${key}` as keyof Dict;
  const v = t(k);
  return v === k ? fallback : v;
}

export function docTypeLabel(t: (k: keyof Dict) => string, docType: string) {
  const key = `doc_${docType}` as keyof Dict;
  const known = ["doc_mobile_money", "doc_bank_statement", "doc_rent_receipts", "doc_payslip", "doc_utility_bills"];
  return t(known.includes(key) ? key : "doc_other");
}

const toneColor = (score: number) => (score >= 65 ? "var(--color-green)" : score >= 50 ? "var(--color-orange)" : "var(--color-red)");

/** Activity-style ring with the score in the centre. */
export function ScoreRing({ score, band, size = 176 }: { score: number; band: string; size?: number }) {
  const { t } = useT();
  const [shown, setShown] = useState(0);
  useEffect(() => { const h = requestAnimationFrame(() => setShown(score)); return () => cancelAnimationFrame(h); }, [score]);
  const stroke = size * 0.085, r = (size - stroke) / 2, c = 2 * Math.PI * r;
  const color = toneColor(score);
  return (
    <div className="relative inline-grid place-items-center" style={{ width: size, height: size }} role="img"
         aria-label={`${t("score_title")}: ${score} ${t("score_of")}, ${t(`band_${band}` as keyof Dict)}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className="ring-track" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} stroke={color} strokeLinecap="round"
                strokeDasharray={c} strokeDashoffset={c * (1 - Math.max(0, Math.min(100, shown)) / 100)} className="ring-fill" />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="num font-bold leading-none tracking-[-0.04em]" style={{ fontSize: size * 0.33 }}>{score}</div>
          <div className="t-caption mt-1 font-semibold" style={{ color }}>{t(`band_${band}` as keyof Dict)}</div>
        </div>
      </div>
    </div>
  );
}

export function Factors({ factors }: { factors: Factor[] }) {
  const { t } = useT();
  return (
    <section>
      <h3 className="t-heading mb-3 px-1">{t("factors_title")}</h3>
      <div className="group-card">
        {factors.map((f) => (
          <div key={f.key} className="row">
            <div className="flex items-baseline justify-between gap-4">
              <span className="t-body font-semibold">{labelFor(t, "f_", f.key, f.label)}</span>
              <span className="num t-body text-secondary"><span className="font-semibold text-label">{f.points}</span>/{f.max_points}</span>
            </div>
            <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-fill">
              <div className="h-full rounded-full bg-blue" style={{ width: `${(f.points / f.max_points) * 100}%` }} />
            </div>
            <p className="t-caption mt-2 text-secondary">{f.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

const STATUS = {
  pass: { key: "check_pass", color: "var(--color-green)", glyph: "✓" },
  warn: { key: "check_warn", color: "var(--color-orange)", glyph: "!" },
  fail: { key: "check_fail", color: "var(--color-red)", glyph: "✕" },
  skip: { key: "check_skip", color: "var(--color-tertiary)", glyph: "–" },
} as const;

export function Checks({ checks }: { checks: Check[] }) {
  const { t } = useT();
  return (
    <section>
      <h3 className="t-heading mb-3 px-1">{t("checks_title")}</h3>
      <div className="group-card">
        {checks.map((c) => {
          const s = STATUS[c.status];
          return (
            <div key={c.key} className="row grid grid-cols-[1.75rem_1fr] gap-x-3">
              <span className="mt-0.5 grid h-6 w-6 place-items-center rounded-full text-[0.8rem] font-bold text-white" style={{ background: s.color }} aria-hidden>{s.glyph}</span>
              <div>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="t-body font-semibold">{labelFor(t, "c_", c.key, c.label)}</span>
                  <span className={`pill pill-${c.status}`}>{t(s.key as keyof Dict)}</span>
                </div>
                <p className="t-caption mt-1 text-secondary">{c.detail}</p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function Stats({ s }: { s: Score }) {
  const { t } = useT();
  const items: { l: string; v: string; unit?: string; sub?: string }[] = [
    { l: t("stats_income"), v: fmtMoney(s.avg_monthly_income), unit: s.currency ?? undefined, sub: s.avg_monthly_income_usd ? `≈ $${fmtMoney(s.avg_monthly_income_usd)}` : undefined },
    { l: t("stats_rent"), v: fmtMoney(s.avg_rent), unit: s.currency ?? undefined },
    { l: t("stats_rent_ratio"), v: s.rent_to_income != null ? `${Math.round(s.rent_to_income * 100)}` : "—", unit: s.rent_to_income != null ? "%" : undefined },
    { l: t("stats_months"), v: String(s.months_covered) },
    { l: t("stats_on_time"), v: String(s.on_time_rent_months) },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {items.map((i) => (
        <div key={i.l} className="group-card px-4 py-3.5">
          <div className="t-caption text-secondary">{i.l}</div>
          <div className="num mt-1 whitespace-nowrap text-[1.5rem] font-semibold leading-none tracking-[-0.02em]">
            {i.v}{i.unit && <span className="t-caption ml-1 font-medium text-secondary">{i.unit}</span>}
          </div>
          {i.sub && <div className="t-caption mt-1 text-tertiary">{i.sub}</div>}
        </div>
      ))}
    </div>
  );
}

export function Explanation({ text, score, loading = true }: { text: string | null; score?: Score; loading?: boolean }) {
  const { t } = useT();
  // If the model couldn't write a summary, say something true from the numbers instead of shimmering forever.
  const fallback = score && !text && !loading
    ? `${t("score_title")}: ${score.score} ${t("score_of")} (${t(`band_${score.band}` as keyof Dict)}). ` +
      score.factors.slice().sort((a, b) => b.points / b.max_points - a.points / a.max_points)[0]?.detail
    : null;
  text = text || fallback;
  return (
    <div>
      <div className="t-caption font-semibold text-secondary">{t("explain_title")}</div>
      {text ? (
        <p className="t-body-lg mt-2 max-w-[36rem] font-medium">{text}</p>
      ) : (
        <div className="mt-3 space-y-2" aria-hidden>
          <div className="h-4 w-[88%] animate-pulse rounded-md bg-fill" />
          <div className="h-4 w-[70%] animate-pulse rounded-md bg-fill" />
          <div className="h-4 w-[52%] animate-pulse rounded-md bg-fill" />
        </div>
      )}
    </div>
  );
}

export function CashflowCharts({ data }: { data: Cashflow }) {
  const { t } = useT();
  const months = data.months.map((m) => ({ month: m.month.slice(2), in: Number(m.inflow ?? 0), out: Number(m.outflow ?? 0), rent: Number(m.rent_paid ?? 0) }));
  const balances = data.balances.map((b) => ({ date: b.date, balance: Number(b.balance) }));
  const short = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}k` : String(n));
  const axis = { tickLine: false, axisLine: false, fontSize: 12, stroke: "#6e6e73" } as const;
  const tip = { contentStyle: { borderRadius: 12, border: "0.5px solid rgba(60,60,67,.18)", boxShadow: "0 8px 24px -8px rgba(0,0,0,.2)", fontSize: 13 } };
  const Legend = () => (
    <div className="t-caption mt-2 flex gap-4 text-secondary">
      {[["bg-green", t("chart_in")], ["bg-label", t("chart_out")], ["bg-blue", t("chart_rent")]].map(([c, l]) => (
        <span key={l} className="inline-flex items-center gap-1.5"><span className={`h-2 w-2 rounded-full ${c}`} />{l}</span>
      ))}
    </div>
  );
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="group-card p-5">
        <h3 className="t-heading">{t("chart_cashflow")}</h3>
        <div className="mt-4 h-52">
          <ResponsiveContainer>
            <BarChart data={months} barGap={3} barCategoryGap="30%">
              <CartesianGrid vertical={false} stroke="rgba(60,60,67,.1)" />
              <XAxis dataKey="month" {...axis} />
              <YAxis tickFormatter={short} {...axis} width={38} />
              <Tooltip formatter={(v: number) => fmtMoney(v)} cursor={{ fill: "rgba(60,60,67,.06)" }} {...tip} />
              <Bar dataKey="in" name={t("chart_in")} fill="var(--color-green)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="out" name={t("chart_out")} fill="var(--color-label)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="rent" name={t("chart_rent")} fill="var(--color-blue)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <Legend />
      </div>
      <div className="group-card p-5">
        <h3 className="t-heading">{t("chart_balance")}</h3>
        <div className="mt-4 h-52">
          <ResponsiveContainer>
            <LineChart data={balances}>
              <CartesianGrid vertical={false} stroke="rgba(60,60,67,.1)" />
              <XAxis dataKey="date" {...axis} minTickGap={40} tickFormatter={(d: string) => d.slice(5)} />
              <YAxis tickFormatter={short} {...axis} width={38} />
              <Tooltip formatter={(v: number) => fmtMoney(v)} {...tip} />
              <Line type="monotone" dataKey="balance" stroke="var(--color-blue)" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
