import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { useT } from "../i18n";
import { ScoreRing } from "../components/ScoreParts";
import { useSession } from "../App";

export default function Landing() {
  const { t } = useT();
  const { switchDemo } = useSession();
  const steps = [
    [t("how_1_t"), t("how_1_b")],
    [t("how_2_t"), t("how_2_b")],
    [t("how_3_t"), t("how_3_b")],
  ];
  return (
    <div>
      <section className="mx-auto max-w-3xl px-6 pt-20 pb-12 text-center md:pt-28">
        <h1 className="t-display mx-auto max-w-[14ch]">{t("hero_title")}</h1>
        <p className="t-body-lg mx-auto mt-6 max-w-[38rem] text-secondary">{t("hero_body")}</p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link to="/upload" className="btn">{t("cta_upload")}</Link>
          <Link to="/dashboard" className="btn-plain">{t("cta_demo")} <ChevronRight className="h-4 w-4" /></Link>
        </div>
        <div className="mt-3">
          <button className="btn-plain t-caption" onClick={() => switchDemo("landlord")}>{t("cta_landlord")} <ChevronRight className="h-3.5 w-3.5" /></button>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-20">
        <Preview />
      </section>

      <section className="bg-grouped">
        <div className="mx-auto grid max-w-5xl gap-10 px-6 py-20 md:grid-cols-3">
          {steps.map(([h, b], i) => (
            <div key={i}>
              <h3 className="t-heading">{h}</h3>
              <p className="t-body mt-2 text-secondary">{b}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

/** A static preview of a report, in the style of a product shot. */
function Preview() {
  const { t } = useT();
  const checks = [
    ["c_balance_continuity", "pass"], ["c_rent_match", "pass"], ["c_internal_transfers", "pass"], ["c_salary_regularity", "pass"],
  ] as const;
  return (
    <div className="group-card overflow-hidden" aria-hidden>
      <div className="grid gap-8 p-8 md:grid-cols-[auto_1fr] md:items-center md:p-10">
        <ScoreRing score={84} band="Excellent" size={160} />
        <div>
          <div className="t-caption font-semibold text-secondary">{t("explain_title")}</div>
          <p className="t-body-lg mt-2 max-w-[34rem] font-medium">
            Rent paid on time for 12 of 12 months, income from one employer arriving like clockwork, and every running balance reconciled across two accounts.
          </p>
        </div>
      </div>
      <div className="grid gap-px bg-separator sm:grid-cols-2 lg:grid-cols-4">
        {checks.map(([k, s]) => (
          <div key={k} className="flex items-center gap-2.5 bg-bg px-6 py-4">
            <span className="grid h-5 w-5 place-items-center rounded-full bg-green text-[0.7rem] font-bold text-white">✓</span>
            <span className="t-caption font-semibold">{t(k)}</span>
            <span className="sr-only">{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
