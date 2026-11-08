import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Loader2, Plus } from "lucide-react";
import { useT } from "../i18n";
import type { Dict } from "../i18n/translations";
import HomeArt from "../components/HomeArt";
import { Cover } from "../components/ListingMedia";
import { market, usd, type Home, type InboxItem, type PropertyIn } from "../lib/market";

/* ---------------------------------------------------------------- portfolio */
export function LandlordHome() {
  const { t } = useT();
  const [props, setProps] = useState<Home[] | null>(null);
  const [busy, setBusy] = useState(false);
  const load = () => market.myProperties().then(setProps).catch(() => setProps([]));
  useEffect(() => { load(); }, []);
  if (!props) return <div className="py-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin text-secondary" /></div>;
  const pending = props.reduce((n, p) => n + (p.pending_count || 0), 0);
  return (
    <div className="bg-grouped min-h-full">
      <div className="mx-auto max-w-5xl space-y-8 px-6 py-10 md:py-14">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="t-title">{t("ll_title")}</h1>
            <p className="t-body-lg mt-2 text-secondary">{t("ll_body")}</p>
          </div>
          <div className="flex gap-2">
            <Link to="/landlord/applications" className="btn-tint">{t("ll_inbox")}{pending > 0 && <span className="num rounded-full bg-red px-1.5 text-[0.75rem] text-white">{pending}</span>}</Link>
            <Link to="/landlord/new" className="btn"><Plus className="h-4 w-4" />{t("ll_new")}</Link>
          </div>
        </header>
        {props.length === 0 ? (
          <div className="group-card p-8 text-center">
            <p className="t-body-lg font-medium">{t("ll_empty")}</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <Link to="/landlord/new" className="btn">{t("ll_new")}</Link>
              <button className="btn-tint" disabled={busy} onClick={async () => { setBusy(true); await market.loadSamples(); await load(); setBusy(false); }}>
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}{t("ll_samples")}
              </button>
            </div>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {props.map((p) => (
              <Link key={p.id} to={`/landlord/listings/${p.id}`} className="group-card block overflow-hidden active:scale-[.99]">
                <div className="relative">
                  <Cover h={p} className="aspect-[5/3] w-full" />
                  {!!p.pending_count && <span className="pill absolute left-3 top-3 bg-white/90 text-label">{p.pending_count} {t("ll_new_apps")}</span>}
                </div>
                <div className="p-4">
                  <div className="flex items-baseline justify-between">
                    <span className="num text-[1.25rem] font-semibold">{usd(p.monthly_rent)}</span>
                    <span className="t-caption text-secondary">{t("min_score")} {p.min_score}</span>
                  </div>
                  <p className="t-body mt-1 font-semibold">{p.title}</p>
                  <p className="t-caption text-secondary">{p.neighborhood} · {p.application_count || 0} {t("ll_apps_total")}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- listing form */
const EMPTY: PropertyIn = {
  title: "", property_type: "apartment", neighborhood: "", city: "Miami", lat: null, lng: null, monthly_rent: 0,
  security_deposit: null, first_last_required: false, application_fee: null, bedrooms: 1, bathrooms: 1, size_sqft: null,
  lease_months: 12, available_from: null, furnished: false, pets_allowed: false, parking: false, utilities_included: [],
  amenities: [], description: "", palette: 0, photo_urls: [], tour_url: null, min_score: 50, max_rent_to_income: 0.4, status: "listed",
};
const AMENITIES = ["AC", "In-unit laundry", "Shared laundry", "Dishwasher", "Balcony", "Patio", "Pool", "Gym", "Rooftop", "Doorman", "Elevator", "Garage", "Private yard", "Near Metrorail", "Near Metrobus"];
const UTILITIES = ["water", "trash", "electricity", "gas", "internet"];
const NEIGHBORHOODS = ["Little Havana", "Wynwood", "Brickell", "Coconut Grove", "Miami Shores", "Little Haiti", "Edgewater", "North Miami", "Coral Gables", "Doral", "Allapattah", "Downtown"];

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="row block">
      <span className="t-caption font-semibold text-secondary">{label}</span>
      <div className="mt-1.5">{children}</div>
      {hint && <span className="t-caption mt-1 block text-tertiary">{hint}</span>}
    </label>
  );
}
const input = "t-body w-full rounded-[10px] bg-fill px-3 py-2 outline-none focus:shadow-[0_0_0_3px_rgba(0,113,227,.35)]";

export function ListingForm() {
  const { id } = useParams();
  const nav = useNavigate();
  const { t } = useT();
  const [p, setP] = useState<PropertyIn>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  // Two taps to delete: the first arms the button for a few seconds, so a misclick never removes a listing.
  const onDelete = async () => {
    if (!id) return;
    if (!confirmDelete) { setConfirmDelete(true); setTimeout(() => setConfirmDelete(false), 4000); return; }
    await market.deleteProperty(id); nav("/landlord");
  };
  useEffect(() => {
    if (!id) return;
    market.myProperties().then((all) => {
      const f = all.find((x) => x.id === id);
      if (f) { const { id: _i, landlord_id: _l, move_in_cost: _m, application_count: _a, pending_count: _p, ...rest } = f; setP({ ...EMPTY, ...rest }); }
    });
  }, [id]);
  const set = <K extends keyof PropertyIn>(k: K, v: PropertyIn[K]) => setP((x) => ({ ...x, [k]: v }));
  const num = (v: string) => (v === "" ? null : Number(v));
  const toggle = (k: "amenities" | "utilities_included", v: string) => set(k, p[k].includes(v) ? p[k].filter((x) => x !== v) : [...p[k], v]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { id ? await market.updateProperty(id, p) : await market.createProperty(p); nav("/landlord"); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  const needed = p.monthly_rent && p.max_rent_to_income ? p.monthly_rent / p.max_rent_to_income : 0;

  return (
    <div className="bg-grouped min-h-full">
      <form onSubmit={save} className="mx-auto max-w-2xl space-y-8 px-6 py-10 md:py-14">
        <header className="flex items-end justify-between gap-4">
          <h1 className="t-title">{id ? t("ll_edit") : t("ll_new")}</h1>
          <div className="w-40 overflow-hidden rounded-[12px]"><HomeArt palette={p.palette} type={p.property_type} className="aspect-[5/3] w-full" /></div>
        </header>

        <section><h3 className="t-heading mb-3 px-1">{t("s_basics")}</h3>
          <div className="group-card">
            <Field label={t("l_title")}><input className={input} required value={p.title} onChange={(e) => set("title", e.target.value)} placeholder={t("l_title_ph")} /></Field>
            <div className="grid sm:grid-cols-2">
              <Field label={t("l_type")}>
                <select className={input} value={p.property_type || ""} onChange={(e) => set("property_type", e.target.value)}>
                  {["studio", "apartment", "house", "room"].map((x) => <option key={x} value={x}>{t(`pt_${x}` as keyof Dict)}</option>)}
                </select>
              </Field>
              <Field label={t("l_neighborhood")}>
                <input className={input} list="nbh" value={p.neighborhood || ""} onChange={(e) => set("neighborhood", e.target.value)} />
                <datalist id="nbh">{NEIGHBORHOODS.map((n) => <option key={n} value={n} />)}</datalist>
              </Field>
            </div>
            <Field label={t("l_description")}><textarea className={`${input} resize-none`} rows={3} value={p.description || ""} onChange={(e) => set("description", e.target.value)} /></Field>
            <Field label={t("l_style")}>
              <div className="flex gap-2">{[0, 1, 2, 3, 4, 5].map((i) => (
                <button type="button" key={i} onClick={() => set("palette", i)} className={`h-10 w-14 overflow-hidden rounded-[8px] ${p.palette === i ? "shadow-[0_0_0_3px_var(--color-blue)]" : ""}`}>
                  <HomeArt palette={i} type={p.property_type} className="h-full w-full" />
                </button>))}</div>
            </Field>
          </div>
        </section>

        <section><h3 className="t-heading mb-3 px-1">{t("s_cost")}</h3>
          <div className="group-card">
            <div className="grid sm:grid-cols-2">
              <Field label={t("l_rent")}><input className={input} type="number" min={1} required value={p.monthly_rent || ""} onChange={(e) => set("monthly_rent", Number(e.target.value))} /></Field>
              <Field label={t("l_deposit")}><input className={input} type="number" min={0} value={p.security_deposit ?? ""} onChange={(e) => set("security_deposit", num(e.target.value))} /></Field>
              <Field label={t("l_fee")}><input className={input} type="number" min={0} value={p.application_fee ?? ""} onChange={(e) => set("application_fee", num(e.target.value))} /></Field>
              <Field label={t("l_lease")}><input className={input} type="number" min={1} value={p.lease_months ?? ""} onChange={(e) => set("lease_months", num(e.target.value))} /></Field>
            </div>
            <label className="row flex items-center justify-between"><span className="t-body">{t("l_firstlast")}</span>
              <input type="checkbox" className="h-5 w-5 accent-[var(--color-blue)]" checked={p.first_last_required} onChange={(e) => set("first_last_required", e.target.checked)} /></label>
            <Field label={t("l_available")}><input className={input} type="date" value={p.available_from || ""} onChange={(e) => set("available_from", e.target.value || null)} /></Field>
          </div>
        </section>

        <section><h3 className="t-heading mb-3 px-1">{t("s_space")}</h3>
          <div className="group-card">
            <div className="grid grid-cols-3">
              <Field label={t("l_beds")}><input className={input} type="number" min={0} value={p.bedrooms ?? ""} onChange={(e) => set("bedrooms", num(e.target.value))} /></Field>
              <Field label={t("l_baths")}><input className={input} type="number" min={0} step={0.5} value={p.bathrooms ?? ""} onChange={(e) => set("bathrooms", num(e.target.value))} /></Field>
              <Field label={t("l_size")}><input className={input} type="number" min={0} value={p.size_sqft ?? ""} onChange={(e) => set("size_sqft", num(e.target.value))} /></Field>
            </div>
            {(["furnished", "pets_allowed", "parking"] as const).map((k) => (
              <label key={k} className="row flex items-center justify-between"><span className="t-body">{t(`l_${k}` as keyof Dict)}</span>
                <input type="checkbox" className="h-5 w-5 accent-[var(--color-blue)]" checked={p[k]} onChange={(e) => set(k, e.target.checked)} /></label>
            ))}
            <Field label={t("amenities")}>
              <div className="flex flex-wrap gap-2">{AMENITIES.map((a) => (
                <button type="button" key={a} onClick={() => toggle("amenities", a)} className={`pill text-[0.875rem] ${p.amenities.includes(a) ? "bg-blue text-white" : "pill-skip text-label"}`}>{a}</button>))}</div>
            </Field>
            <Field label={t("utilities")}>
              <div className="flex flex-wrap gap-2">{UTILITIES.map((a) => (
                <button type="button" key={a} onClick={() => toggle("utilities_included", a)} className={`pill text-[0.875rem] ${p.utilities_included.includes(a) ? "bg-blue text-white" : "pill-skip text-label"}`}>{a}</button>))}</div>
            </Field>
          </div>
        </section>

        <section><h3 className="t-heading mb-3 px-1">{t("requirements")}</h3>
          <div className="group-card">
            <Field label={`${t("min_score")}: ${p.min_score}`} hint={t("l_minscore_hint")}>
              <input type="range" min={0} max={100} step={5} value={p.min_score} onChange={(e) => set("min_score", Number(e.target.value))} className="w-full accent-[var(--color-blue)]" />
            </Field>
            <Field label={`${t("rent_max_share")}: ${Math.round(p.max_rent_to_income * 100)}%`}
                   hint={needed ? `${t("l_rti_hint")} ${usd(needed)} / ${t("per_month")}` : undefined}>
              <input type="range" min={0.25} max={0.5} step={0.01} value={p.max_rent_to_income} onChange={(e) => set("max_rent_to_income", Number(e.target.value))} className="w-full accent-[var(--color-blue)]" />
            </Field>
          </div>
          <p className="t-caption mt-2 px-1 text-tertiary">{t("l_fair")}</p>
        </section>

        {err && <p className="t-body text-red">{err}</p>}
        <div className="flex flex-wrap gap-2">
          <button className="btn" disabled={busy}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}{id ? t("save") : t("ll_publish")}</button>
          <Link to="/landlord" className="btn-tint">{t("cancel")}</Link>
          {id && <button type="button" className={`ml-auto ${confirmDelete ? "btn bg-red" : "btn-plain text-red"}`} onClick={onDelete}>{confirmDelete ? t("ll_delete_confirm") : t("ll_delete")}</button>}
        </div>
      </form>
    </div>
  );
}

/* ---------------------------------------------------------------- inbox */
export function LandlordInbox() {
  const { t } = useT();
  const [items, setItems] = useState<InboxItem[] | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const load = () => market.inbox().then(setItems).catch(() => setItems([]));
  useEffect(() => { load(); }, []);
  if (!items) return <div className="py-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin text-secondary" /></div>;
  const decide = async (id: string, s: "approved" | "declined") => { await market.decide(id, s, notes[id] || ""); load(); };
  return (
    <div className="bg-grouped min-h-full">
      <div className="mx-auto max-w-3xl space-y-6 px-6 py-10 md:py-14">
        <h1 className="t-title">{t("ll_inbox")}</h1>
        {items.length === 0 && <p className="t-body text-secondary">{t("ll_inbox_empty")}</p>}
        {items.map((a) => {
          const meets = a.score_at_submit >= a.min_score;
          const tone = a.status === "approved" ? "pill-pass" : a.status === "declined" ? "pill-fail" : "pill-skip";
          return (
            <article key={a.id} className="group-card">
              <div className="row flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="t-heading">{a.renter_name}</p>
                  <p className="t-caption text-secondary">{a.title} · {usd(a.monthly_rent)} / {t("per_month")}</p>
                </div>
                <span className={`pill ${tone}`}>{t(`app_${a.status}` as keyof Dict)}</span>
              </div>
              <div className="row grid grid-cols-3 gap-3">
                <div><div className="t-caption text-secondary">{t("ll_their_score")}</div><div className="num text-[1.5rem] font-semibold">{a.score_at_submit}</div></div>
                <div><div className="t-caption text-secondary">{t("ll_your_min")}</div><div className="num text-[1.5rem] font-semibold">{a.min_score}</div></div>
                <div><div className="t-caption text-secondary">{t("income_label")}</div><div className="num text-[1.5rem] font-semibold">{a.us_monthly_income ? usd(a.us_monthly_income) : "—"}</div></div>
              </div>
              <div className="row">
                <span className={`pill ${meets ? "pill-pass" : "pill-warn"}`}>{meets ? t("ll_meets") : t("ll_below")}</span>
                {a.message && <p className="t-body mt-3">“{a.message}”</p>}
                {a.report_url && <a href={new URL(a.report_url).pathname} target="_blank" rel="noreferrer" className="btn-plain mt-2 px-0">{t("ll_open_report")}</a>}
              </div>
              {a.status === "pending" ? (
                <div className="row space-y-3">
                  <input className={input} placeholder={t("ll_note_placeholder")} value={notes[a.id] || ""} onChange={(e) => setNotes((n) => ({ ...n, [a.id]: e.target.value }))} />
                  <div className="flex gap-2">
                    <button className="btn" onClick={() => decide(a.id, "approved")}>{t("ll_approve")}</button>
                    <button className="btn-tint" onClick={() => decide(a.id, "declined")}>{t("ll_decline")}</button>
                  </div>
                </div>
              ) : a.landlord_note ? <div className="row t-caption text-secondary">{t("ll_your_note")}: “{a.landlord_note}”</div> : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}
