import { authHeaders } from "./api";

export type Role = "renter" | "landlord";
export type Me = { id: string; role: Role | null; display_name: string | null; email: string | null; us_monthly_income: number | null };

export type Home = {
  id: string; landlord_id: string; title: string; property_type: string | null; neighborhood: string | null; city: string | null;
  lat: number | null; lng: number | null; monthly_rent: number; security_deposit: number | null; first_last_required: boolean;
  application_fee: number | null; bedrooms: number | null; bathrooms: number | null; size_sqft: number | null;
  lease_months: number | null; available_from: string | null; furnished: boolean; pets_allowed: boolean; parking: boolean;
  utilities_included: string[]; amenities: string[]; description: string | null; palette: number; photo_urls: string[]; tour_url: string | null; min_score: number;
  max_rent_to_income: number; status: string; move_in_cost: number;
  landlord_name?: string; landlord_email?: string | null;
  match?: "within_reach" | "almost" | "not_yet" | "no_score"; gap?: string | null;
  my_application?: string | null; my_application_note?: string | null;
  score?: number | null; tip?: Tip | null; application_count?: number; pending_count?: number;
};
export type Tip = { factor: string; label: string; points: number; max_points: number; tip: string };
export type HomesResp = { score: number | null; band: string | null; us_monthly_income: number | null; tip: Tip | null; homes: Home[] };
export type MyApp = { id: string; status: string; score_at_submit: number; landlord_note: string | null; created_at: string;
  decided_at: string | null; property_id: string; title: string; neighborhood: string | null; monthly_rent: number; palette: number; photo_urls: string[] | null; landlord_name: string };
export type InboxItem = { id: string; status: string; score_at_submit: number; message: string | null; landlord_note: string | null;
  created_at: string; property_id: string; title: string; monthly_rent: number; min_score: number; renter_name: string;
  us_monthly_income: number | null; report_url: string | null };
export type PropertyIn = Omit<Home, "id" | "landlord_id" | "move_in_cost" | "match" | "gap" | "landlord_name" | "landlord_email" |
  "my_application" | "my_application_note" | "score" | "tip" | "application_count" | "pending_count">;

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...(await authHeaders()), ...(init.headers || {}) } });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail ?? msg; } catch {}
    throw new Error(typeof msg === "string" ? msg : "Request failed");
  }
  return res.json();
}

export const market = {
  me: () => req<Me>("/api/me"),
  updateMe: (b: Partial<Pick<Me, "role" | "us_monthly_income" | "display_name" | "email">>) => req<Me>("/api/me", { method: "POST", body: JSON.stringify(b) }),
  homes: () => req<HomesResp>("/api/homes"),
  home: (id: string) => req<Home>(`/api/homes/${id}`),
  apply: (id: string, message: string) => req<{ ok: true; score: number }>(`/api/homes/${id}/apply`, { method: "POST", body: JSON.stringify({ message }) }),
  myApplications: () => req<MyApp[]>("/api/applications/mine"),
  myProperties: () => req<Home[]>("/api/properties/mine"),
  createProperty: (p: PropertyIn) => req<Home>("/api/properties", { method: "POST", body: JSON.stringify(p) }),
  updateProperty: (id: string, p: PropertyIn) => req<Home>(`/api/properties/${id}`, { method: "PATCH", body: JSON.stringify(p) }),
  deleteProperty: (id: string) => req<{ ok: true }>(`/api/properties/${id}`, { method: "DELETE" }),
  loadSamples: () => req<{ ok: true; created: number }>("/api/properties/load-samples", { method: "POST" }),
  inbox: () => req<InboxItem[]>("/api/landlord/applications"),
  decide: (id: string, status: "approved" | "declined", note: string) =>
    req<{ ok: true }>(`/api/applications/${id}/decision`, { method: "POST", body: JSON.stringify({ status, note }) }),
};

export const usd = (n: number | null | undefined) => (n == null ? "—" : `$${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n)}`);

type TFn = (k: any) => string;
/** Localised "what you need" line, computed from the numbers rather than server text. */
export function gapText(t: TFn, h: Home, score: number | null | undefined, income: number | null | undefined): string | null {
  if (h.match === "not_yet") {
    const needed = h.monthly_rent / h.max_rent_to_income;
    return t("gap_income").replace("{need}", usd(needed)).replace("{have}", usd(income ?? 0));
  }
  if (h.match === "almost" && score != null) return t("gap_points").replace("{n}", String(h.min_score - score));
  if (h.match === "no_score") return t("group_noscore_b");
  return null;
}
export const tipText = (t: TFn, tip: Tip) => { const k = `tip_${tip.factor}`; const v = t(k); return v === k ? tip.tip : v; };
