import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { Loader2 } from "lucide-react";
import { useT } from "../i18n";
import { api, type Cashflow, type Score } from "../lib/api";
import { CashflowCharts, Checks, Explanation, Factors, ScoreRing, Stats } from "../components/ScoreParts";

export default function Dashboard() {
  const { t, lang } = useT();
  const [score, setScore] = useState<Score | null>(null);
  const [cash, setCash] = useState<Cashflow | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(true);

  useEffect(() => {
    let alive = true;
    setErr(null);
    api.score(lang, false).then((s) => alive && setScore((prev) => (prev?.explanation ? prev : s))).catch((e) => alive && setErr(e.message));
    api.cashflow().then((c) => alive && setCash(c)).catch(() => {});
    setExplaining(true);
    api.score(lang, true).then((s) => alive && setScore(s)).catch(() => {}).finally(() => alive && setExplaining(false));
    return () => { alive = false; };
  }, [lang]);

  if (err) return <p className="t-body mx-auto max-w-xl px-6 py-24 text-center text-red">{err}</p>;
  if (!score) return <div className="py-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin text-secondary" /></div>;

  if (score.months_covered === 0) {
    return (
      <div className="mx-auto max-w-xl px-6 py-24 text-center">
        <h1 className="t-title">{t("score_empty_t")}</h1>
        <p className="t-body-lg mt-3 text-secondary">{t("score_empty_b")}</p>
        <Link to="/upload" className="btn mt-8">{t("cta_upload")}</Link>
      </div>
    );
  }

  return (
    <div className="bg-grouped">
      <div className="mx-auto max-w-5xl space-y-8 px-6 py-10 md:py-14">
        <header className="group-card grid gap-8 p-8 md:grid-cols-[auto_1fr] md:items-center md:p-10">
          <ScoreRing score={score.score} band={score.band} />
          <Explanation text={score.explanation} score={score} loading={explaining} />
        </header>
        <Link to="/homes" className="group-card flex flex-wrap items-center justify-between gap-4 p-6 transition-transform active:scale-[.99]">
          <div>
            <div className="t-heading">{t("cta_homes")}</div>
            <p className="t-body mt-1 text-secondary">{t("cta_homes_b")}</p>
          </div>
          <span className="btn">{t("nav_homes")}</span>
        </Link>
        <Stats s={score} />
        <div className="grid gap-8 lg:grid-cols-2">
          <Checks checks={score.checks} />
          <Factors factors={score.factors} />
        </div>
        {cash && <CashflowCharts data={cash} />}
        <SharePanel />
      </div>
    </div>
  );
}

function SharePanel() {
  const { t } = useT();
  const [links, setLinks] = useState<{ token: string; url: string; label: string; views: number }[]>([]);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => { api.listShares().then(setLinks).catch(() => {}); }, []);

  const create = async () => {
    setBusy(true);
    try { await api.createShare("Landlord"); setLinks(await api.listShares()); } finally { setBusy(false); }
  };
  const latest = links[0];
  const copy = async () => {
    if (!latest) return;
    await navigator.clipboard.writeText(latest.url);
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="group-card grid gap-8 p-8 md:grid-cols-[1fr_auto] md:items-center">
      <div>
        <h3 className="t-heading">{t("share_title")}</h3>
        <p className="t-body mt-1.5 max-w-[34rem] text-secondary">{t("share_body")}</p>
        <div className="mt-5 flex flex-wrap items-center gap-2">
          {!latest ? (
            <button className="btn" onClick={create} disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />} {t("share_create")}
            </button>
          ) : (
            <>
              <button className="btn" onClick={copy}>{copied ? t("share_copied") : t("share_copy")}</button>
              <a className="btn-tint" href={latest.url} target="_blank" rel="noreferrer">{t("share_open")}</a>
              <span className="num t-caption text-secondary">{latest.views} {t("share_views")}</span>
            </>
          )}
        </div>
        {latest && <p className="t-caption mt-3 break-all font-mono text-tertiary">{latest.url}</p>}
      </div>
      {latest && (
        <div className="justify-self-center rounded-2xl bg-white p-3 shadow-[0_0_0_0.5px_var(--color-separator)]">
          <QRCodeSVG value={latest.url} size={128} fgColor="#1d1d1f" />
        </div>
      )}
    </section>
  );
}
