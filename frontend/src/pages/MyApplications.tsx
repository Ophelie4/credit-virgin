import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useT } from "../i18n";
import type { Dict } from "../i18n/translations";
import { Cover } from "../components/ListingMedia";
import { market, usd, type MyApp } from "../lib/market";

export default function MyApplications() {
  const { t } = useT();
  const [apps, setApps] = useState<MyApp[] | null>(null);
  useEffect(() => { market.myApplications().then(setApps).catch(() => setApps([])); }, []);
  if (!apps) return <div className="py-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin text-secondary" /></div>;
  return (
    <div className="bg-grouped min-h-full">
      <div className="mx-auto max-w-3xl px-6 py-10 md:py-14">
        <h1 className="t-title">{t("my_apps")}</h1>
        {apps.length === 0 ? (
          <div className="mt-6"><p className="t-body text-secondary">{t("my_apps_empty")}</p><Link to="/homes" className="btn mt-4">{t("browse_homes")}</Link></div>
        ) : (
          <div className="group-card mt-6">
            {apps.map((a) => {
              const tone = a.status === "approved" ? "pill-pass" : a.status === "declined" ? "pill-fail" : "pill-skip";
              return (
                <Link key={a.id} to={`/homes/${a.property_id}`} className="row flex items-center gap-4">
                  <Cover h={a} className="h-14 w-20 shrink-0 rounded-[10px]" />
                  <div className="min-w-0 flex-1">
                    <p className="t-body font-semibold">{a.title}</p>
                    <p className="t-caption text-secondary">{a.landlord_name} · {usd(a.monthly_rent)} / {t("per_month")} · {t("sent_score")} {a.score_at_submit}</p>
                    {a.landlord_note && <p className="t-caption mt-1">“{a.landlord_note}”</p>}
                  </div>
                  <span className={`pill ${tone}`}>{t(`app_${a.status}` as keyof Dict)}</span>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
