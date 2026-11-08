import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useT } from "../i18n";
import type { Dict } from "../i18n/translations";
import { Cover } from "../components/ListingMedia";
import { ScoreRing } from "../components/ScoreParts";
import { gapText, market, tipText, usd, type Home, type HomesResp } from "../lib/market";
import { labelFor } from "../components/ScoreParts";

export function IncomePrompt({ onSaved, initial }: { onSaved: () => void; initial?: number | null }) {
  const { t } = useT();
  const [v, setV] = useState(initial ? String(initial) : "");
  const [busy, setBusy] = useState(false);
  return (
    <form className="group-card p-6" onSubmit={async (e) => { e.preventDefault(); setBusy(true); try { await market.updateMe({ us_monthly_income: Number(v) }); onSaved(); } finally { setBusy(false); } }}>
      <h3 className="t-heading">{t("income_title")}</h3>
      <p className="t-body mt-1 max-w-[40rem] text-secondary">{t("income_body")}</p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <label className="flex items-center rounded-full bg-fill px-4 py-2.5">
          <span className="t-body text-secondary">$</span>
          <input type="number" min={0} step={50} required value={v} onChange={(e) => setV(e.target.value)} placeholder="4,500"
                 className="t-body w-32 bg-transparent px-1 outline-none" aria-label={t("income_title")} />
          <span className="t-caption text-secondary">/ {t("per_month")}</span>
        </label>
        <button className="btn" disabled={busy || !v}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}{t("save")}</button>
      </div>
      <p className="t-caption mt-2 text-tertiary">{t("income_note")}</p>
    </form>
  );
}

const GROUPS: { key: Home["match"]; title: keyof Dict; body: keyof Dict }[] = [
  { key: "within_reach", title: "group_reach", body: "group_reach_b" },
  { key: "almost", title: "group_almost", body: "group_almost_b" },
  { key: "not_yet", title: "group_notyet", body: "group_notyet_b" },
  { key: "no_score", title: "group_noscore", body: "group_noscore_b" },
];

export default function Homes() {
  const { t } = useT();
  const [data, setData] = useState<HomesResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [editIncome, setEditIncome] = useState(false);
  const load = () => market.homes().then(setData).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  if (err) return <p className="t-body mx-auto max-w-xl px-6 py-24 text-center text-red">{err}</p>;
  if (!data) return <div className="py-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin text-secondary" /></div>;
  const limited = data.score != null && data.score < 35;

  return (
    <div className="bg-grouped min-h-full">
      <div className="mx-auto max-w-5xl space-y-8 px-6 py-10 md:py-14">
        <header className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="t-title">{t("homes_title")}</h1>
            <p className="t-body-lg mt-2 max-w-[38rem] text-secondary">{t("homes_body")}</p>
          </div>
          {data.score != null && (
            <div className="flex items-center gap-4">
              <ScoreRing score={data.score} band={data.band || "Fair"} size={84} />
              <div className="t-caption text-secondary">
                <div>{t("income_label")}</div>
                <div className="t-body font-semibold text-label">{data.us_monthly_income ? `${usd(data.us_monthly_income)} / ${t("per_month")}` : "—"}</div>
                <button className="btn-plain px-0 text-[0.8125rem]" onClick={() => setEditIncome(true)}>{t("edit")}</button>
              </div>
            </div>
          )}
        </header>

        {(data.score != null && (!data.us_monthly_income || editIncome)) && (
          <IncomePrompt initial={data.us_monthly_income} onSaved={() => { setEditIncome(false); load(); }} />
        )}

        {data.tip && (
          <div className={`group-card flex flex-wrap items-start gap-4 p-6 ${limited ? "shadow-[0_0_0_2px_var(--color-orange)]" : ""}`}>
            <div className="min-w-0 flex-1">
              <div className="t-caption font-semibold text-secondary">{limited ? t("plan_title_limited") : t("plan_title")}</div>
              <p className="t-body-lg mt-1 font-medium">{tipText(t, data.tip)}</p>
              <p className="t-caption mt-1 text-secondary">{labelFor(t, "f_", data.tip.factor, data.tip.label)}: {data.tip.points}/{data.tip.max_points}</p>
            </div>
            <Link to="/upload" className="btn-tint">{t("add_documents")}</Link>
          </div>
        )}

        {GROUPS.map((g) => {
          const list = data.homes.filter((h) => h.match === g.key);
          if (!list.length) return null;
          return (
            <section key={g.key}>
              <h2 className="t-heading px-1">{t(g.title)} <span className="text-tertiary">{list.length}</span></h2>
              <p className="t-caption mt-1 px-1 text-secondary">{t(g.body)}</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {list.map((h) => <HomeCard key={h.id} h={h} gap={gapText(t, h, data.score, data.us_monthly_income)} />)}
              </div>
            </section>
          );
        })}
        {data.score == null && <div className="text-center"><Link to="/upload" className="btn">{t("cta_upload")}</Link></div>}
      </div>
    </div>
  );
}

export function HomeCard({ h, to, gap }: { h: Home; to?: string; gap?: string | null }) {
  const { t } = useT();
  const dim = h.match === "not_yet";
  return (
    <Link to={to ?? `/homes/${h.id}`} className={`group-card group block overflow-hidden transition-transform active:scale-[.99] ${dim ? "opacity-75" : ""}`}>
      <div className="relative aspect-[5/3] overflow-hidden">
        <Cover h={h} className="h-full w-full transition-transform duration-500 group-hover:scale-[1.03]" />
        {h.tour_url && <span className="pill absolute bottom-3 left-3 bg-black/55 text-white backdrop-blur">▶ {t("tour")}</span>}
        {h.my_application && (
          <span className={`pill absolute left-3 top-3 ${h.my_application === "approved" ? "pill-pass" : h.my_application === "declined" ? "pill-fail" : "pill-skip"} bg-white/90`}>
            {t(`app_${h.my_application}` as keyof Dict)}
          </span>
        )}
      </div>
      <div className="p-4">
        <div className="flex items-baseline justify-between gap-2">
          <span className="num text-[1.25rem] font-semibold tracking-[-0.02em]">{usd(h.monthly_rent)}<span className="t-caption font-normal text-secondary"> / {t("per_month")}</span></span>
          <span className="t-caption text-secondary">{t("min_score")} {h.min_score}</span>
        </div>
        <p className="t-body mt-1 font-semibold leading-snug">{h.title}</p>
        <p className="t-caption text-secondary">
          {h.neighborhood} · {h.bedrooms === 0 ? t("studio") : `${h.bedrooms} ${t("bd")}`} · {h.bathrooms} {t("ba")}{h.size_sqft ? ` · ${h.size_sqft} sq ft` : ""}
        </p>
        {gap && <p className={`t-caption mt-2 font-medium ${h.match === "almost" ? "text-[#b36b00]" : "text-secondary"}`}>{gap}</p>}
      </div>
    </Link>
  );
}
