import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useT } from "../i18n";
import { api, type Report as ReportT } from "../lib/api";
import { Checks, Explanation, Factors, ScoreRing, Stats, docTypeLabel } from "../components/ScoreParts";

export default function Report() {
  const { token = "" } = useParams();
  const { t, lang } = useT();
  const [data, setData] = useState<ReportT | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    api.report(token, lang).then((d) => alive && setData(d)).catch(() => alive && setErr(true));
    return () => { alive = false; };
  }, [token, lang]);

  if (err) return <p className="t-body mx-auto max-w-xl px-6 py-24 text-center text-secondary">{t("report_expired")}</p>;
  if (!data) return <div className="py-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin text-secondary" /></div>;
  const s = data.score;

  return (
    <div className="bg-grouped">
      <div className="mx-auto max-w-4xl space-y-8 px-6 py-10 md:py-14 print:py-0">
        <header>
          <p className="t-caption font-semibold text-secondary">{t("report_title")}</p>
          <h1 className="t-title mt-1">{data.applicant_name}</h1>
          <p className="t-body mt-1 text-secondary">{t("report_for")} {data.generated_for}</p>
        </header>
        <section className="group-card grid gap-8 p-8 md:grid-cols-[auto_1fr] md:items-center">
          <ScoreRing score={s.score} band={s.band} />
          <Explanation text={s.explanation} score={s} loading={false} />
        </section>
        <Stats s={s} />
        <Checks checks={s.checks} />
        <Factors factors={s.factors} />
        <section>
          <h3 className="t-heading mb-3 px-1">{t("report_docs")}</h3>
          <div className="group-card">
            {data.documents.map((d, i) => (
              <div key={i} className="row flex flex-wrap items-baseline justify-between gap-2">
                <span className="t-body font-semibold">{docTypeLabel(t, d.doc_type)}{d.source_name ? `, ${d.source_name}` : ""}</span>
                <span className="num t-caption text-secondary">{d.period_start} – {d.period_end}, {d.tx_count} {t("docs_transactions")}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="px-1 text-secondary">
          <p className="t-caption font-semibold text-label">{t("report_about")}</p>
          <p className="t-caption mt-1 max-w-[60rem]">{t("report_about_body")}</p>
          <p className="t-caption mt-3 text-tertiary">{t("report_powered")} · creditvirgin.tech</p>
        </section>
      </div>
    </div>
  );
}
