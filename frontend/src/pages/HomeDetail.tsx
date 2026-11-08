import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft, Loader2 } from "lucide-react";
import { useT } from "../i18n";
import type { Dict } from "../i18n/translations";
import { TourHero } from "../components/ListingMedia";
import { gapText, market, tipText, usd, type Home } from "../lib/market";
import { useSession } from "../App";

export function MapEmbed({ lat, lng, label }: { lat: number; lng: number; label: string }) {
  const d = 0.012;
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${lng - d}%2C${lat - d * 0.7}%2C${lng + d}%2C${lat + d * 0.7}&layer=mapnik&marker=${lat}%2C${lng}`;
  return <iframe title={label} src={src} className="h-64 w-full rounded-[14px] border-0" loading="lazy" />;
}

export default function HomeDetail() {
  const { id = "" } = useParams();
  const { t } = useT();
  const [h, setH] = useState<Home | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => market.home(id).then(setH).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [id]);

  if (err) return (
    <div className="mx-auto max-w-xl px-6 py-24 text-center">
      <p className="t-body text-red">{err}</p>
      <Link to="/homes" className="btn-tint mt-6"><ChevronLeft className="h-4 w-4" /> {t("homes_title")}</Link>
    </div>
  );
  if (!h) return <div className="py-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin text-secondary" /></div>;

  const send = async () => { setBusy(true); try { await market.apply(h.id, msg); await load(); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); } };
  const facts: [string, string][] = [
    [t("f_type"), h.bedrooms === 0 ? t("studio") : `${h.bedrooms} ${t("bd")} · ${h.bathrooms} ${t("ba")}`],
    [t("f_size"), h.size_sqft ? `${h.size_sqft} sq ft` : "—"],
    [t("f_lease"), h.lease_months ? `${h.lease_months} ${t("months")}` : "—"],
    [t("f_available"), h.available_from || t("now")],
  ];
  const flags = [h.furnished && t("a_furnished"), h.pets_allowed && t("a_pets"), h.parking && t("a_parking")].filter(Boolean) as string[];
  const cost: [string, number][] = [
    [t("c_first"), h.monthly_rent],
    ...(h.first_last_required ? [[t("c_last"), h.monthly_rent] as [string, number]] : []),
    ...(h.security_deposit ? [[t("c_deposit"), h.security_deposit] as [string, number]] : []),
    ...(h.application_fee ? [[t("c_fee"), h.application_fee] as [string, number]] : []),
  ];

  return (
    <div className="bg-grouped min-h-full">
      <div className="mx-auto max-w-5xl px-6 py-8 md:py-12">
        <Link to="/homes" className="btn-plain mb-4 px-0"><ChevronLeft className="h-4 w-4" /> {t("homes_title")}</Link>
        <div className="group-card overflow-hidden">
          <TourHero h={h} tourLabel={t("tour")} />
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_22rem]">
          <div className="space-y-8">
            <header>
              <p className="t-caption font-semibold text-secondary">{h.neighborhood}, {h.city}</p>
              <h1 className="t-title mt-1">{h.title}</h1>
              <p className="num mt-2 text-[1.75rem] font-semibold tracking-[-0.02em]">{usd(h.monthly_rent)}<span className="t-body font-normal text-secondary"> / {t("per_month")}</span></p>
              {h.description && <p className="t-body-lg mt-4 max-w-[40rem] text-secondary">{h.description}</p>}
            </header>

            <dl className="group-card grid grid-cols-2 gap-px overflow-hidden bg-separator md:grid-cols-4">
              {facts.map(([k, v]) => (
                <div key={k} className="bg-bg px-4 py-3.5"><dt className="t-caption text-secondary">{k}</dt><dd className="t-body mt-0.5 font-semibold">{v}</dd></div>
              ))}
            </dl>

            {(h.amenities.length > 0 || flags.length > 0 || h.utilities_included.length > 0) && (
              <section>
                <h3 className="t-heading mb-3 px-1">{t("amenities")}</h3>
                <div className="flex flex-wrap gap-2">
                  {[...flags, ...h.amenities].map((a) => <span key={a} className="pill pill-skip text-[0.875rem] text-label">{a}</span>)}
                  {h.utilities_included.length > 0 && <span className="pill pill-pass text-[0.875rem]">{t("utilities")}: {h.utilities_included.join(", ")}</span>}
                </div>
              </section>
            )}

            {h.lat && h.lng && (
              <section>
                <h3 className="t-heading mb-3 px-1">{t("location")}</h3>
                <MapEmbed lat={h.lat} lng={h.lng} label={h.neighborhood || "Map"} />
                <p className="t-caption mt-2 px-1 text-tertiary">{t("address_after")}</p>
              </section>
            )}
          </div>

          <aside className="space-y-4 lg:sticky lg:top-16 lg:self-start">
            <div className="group-card">
              <div className="row"><h3 className="t-heading">{t("move_in")}</h3></div>
              {cost.map(([k, v]) => (
                <div key={k} className="row flex justify-between"><span className="t-body text-secondary">{k}</span><span className="num t-body">{usd(v)}</span></div>
              ))}
              <div className="row flex justify-between"><span className="t-body font-semibold">{t("total")}</span><span className="num t-body font-semibold">{usd(h.move_in_cost)}</span></div>
            </div>

            <div className="group-card">
              <div className="row"><h3 className="t-heading">{t("requirements")}</h3></div>
              <div className="row flex justify-between"><span className="t-body text-secondary">{t("min_score")}</span><span className="num t-body font-semibold">{h.min_score}</span></div>
              <div className="row flex justify-between"><span className="t-body text-secondary">{t("rent_max_share")}</span><span className="num t-body font-semibold">{Math.round(h.max_rent_to_income * 100)}%</span></div>
              {h.score != null && <div className="row flex justify-between"><span className="t-body text-secondary">{t("your_score")}</span><span className="num t-body font-semibold">{h.score}</span></div>}
            </div>

            <ApplyPanel h={h} msg={msg} setMsg={setMsg} busy={busy} send={send} />

            {h.landlord_name && (
              <div className="group-card row">
                <div className="t-caption text-secondary">{t("listed_by")}</div>
                <div className="t-body font-semibold">{h.landlord_name}</div>
                {h.landlord_email && <a className="t-caption text-blue" href={`mailto:${h.landlord_email}`}>{h.landlord_email}</a>}
              </div>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}

function ApplyPanel({ h, msg, setMsg, busy, send }: { h: Home; msg: string; setMsg: (s: string) => void; busy: boolean; send: () => void }) {
  const { t } = useT();
  const { me } = useSession();
  const gap = gapText(t, h, h.score, me?.us_monthly_income);
  if (h.my_application) {
    const tone = h.my_application === "approved" ? "pill-pass" : h.my_application === "declined" ? "pill-fail" : "pill-skip";
    return (
      <div className="group-card p-5">
        <span className={`pill ${tone}`}>{t(`app_${h.my_application}` as keyof Dict)}</span>
        <p className="t-body mt-2">{h.my_application === "pending" ? t("app_pending_b") : h.my_application_note || ""}</p>
        {h.my_application === "approved" && h.landlord_email && <a className="btn mt-3" href={`mailto:${h.landlord_email}`}>{t("contact_landlord")}</a>}
      </div>
    );
  }
  if (h.match === "no_score") {
    return <div className="group-card p-5"><p className="t-body">{gap}</p><Link to="/upload" className="btn mt-3">{t("cta_upload")}</Link></div>;
  }
  if (h.match === "not_yet") {
    return <div className="group-card p-5"><span className="pill pill-skip">{t("group_notyet")}</span><p className="t-body mt-2 text-secondary">{gap}</p></div>;
  }
  return (
    <div className="group-card p-5">
      {h.match === "almost" ? (
        <>
          <span className="pill pill-warn">{t("group_almost")}</span>
          <p className="t-body mt-2">{gap}</p>
          {h.tip && <p className="t-caption mt-1 text-secondary">{tipText(t, h.tip)}</p>}
        </>
      ) : (
        <span className="pill pill-pass">{t("group_reach")}</span>
      )}
      <p className="t-caption mt-3 text-secondary">{t("apply_explain")}</p>
      <textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={3} placeholder={t("apply_placeholder")}
                className="t-body mt-3 w-full resize-none rounded-[12px] bg-fill px-3 py-2.5 outline-none focus:shadow-[0_0_0_3px_rgba(0,113,227,.35)]" />
      <button className={`${h.match === "almost" ? "btn-tint" : "btn"} mt-3 w-full justify-center`} onClick={send} disabled={busy}>
        {busy && <Loader2 className="h-4 w-4 animate-spin" />}{h.match === "almost" ? t("apply_anyway") : t("apply")}
      </button>
    </div>
  );
}
