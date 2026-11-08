export type Doc = {
  id: string; filename: string; doc_type: string; source_name: string | null; currency: string | null;
  language: string | null; period_start: string | null; period_end: string | null; tx_count: number; created_at: string;
};
export type Factor = { key: string; label: string; points: number; max_points: number; detail: string };
export type Check = { key: string; label: string; status: "pass" | "warn" | "fail" | "skip"; detail: string };
export type Score = {
  score: number; band: string; factors: Factor[]; checks: Check[]; months_covered: number; currency: string | null;
  avg_monthly_income: number | null; avg_monthly_income_usd: number | null; avg_rent: number | null;
  rent_to_income: number | null; on_time_rent_months: number; explanation: string | null;
};
export type Cashflow = {
  months: { month: string; inflow: number | null; outflow: number | null; rent_paid: number | null; saved: number | null; salary: number | null; tx_count: number; min_balance: number | null }[];
  balances: { date: string; balance: number; doc_type: string }[];
  categories: { category: string; total: number; n: number }[];
};
export type Report = {
  applicant_name: string; generated_for: string; views: number;
  documents: { doc_type: string; source_name: string | null; period_start: string | null; period_end: string | null; tx_count: number }[];
  score: Score;
};

let tokenGetter: (() => Promise<string | null>) | null = null;
export function setTokenGetter(fn: (() => Promise<string | null>) | null) { tokenGetter = fn; }

// Demo mode (no Auth0): pick which demo account the requests act as.
let demoRole: "renter" | "landlord" = (() => { try { return (localStorage.getItem("cv_demo_role") as "renter" | "landlord") || "renter"; } catch { return "renter"; } })();
export function getDemoRole() { return demoRole; }
export function setDemoRole(r: "renter" | "landlord") { demoRole = r; try { localStorage.setItem("cv_demo_role", r); } catch {} }

export async function authHeaders(): Promise<Record<string, string>> {
  const h: Record<string, string> = {};
  if (tokenGetter) {
    const tok = await tokenGetter();
    if (tok) { h.Authorization = `Bearer ${tok}`; return h; }
  }
  h["X-Demo-Role"] = demoRole;
  return h;
}
const headers = authHeaders;

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail ?? msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  listDocs: async () => handle<Doc[]>(await fetch("/api/documents", { headers: await headers() })),
  upload: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return handle<Doc>(await fetch("/api/documents", { method: "POST", body: fd, headers: await headers() }));
  },
  deleteDoc: async (id: string) => handle<{ ok: true }>(await fetch(`/api/documents/${id}`, { method: "DELETE", headers: await headers() })),
  reset: async () => handle<{ ok: true }>(await fetch("/api/documents", { method: "DELETE", headers: await headers() })),
  score: async (lang: string, explain = true) =>
    handle<Score>(await fetch(`/api/score?lang=${lang}&explain=${explain}`, { headers: await headers() })),
  cashflow: async () => handle<Cashflow>(await fetch("/api/cashflow", { headers: await headers() })),
  createShare: async (label: string) =>
    handle<{ token: string; url: string }>(await fetch(`/api/share?label=${encodeURIComponent(label)}`, { method: "POST", headers: await headers() })),
  listShares: async () => handle<{ token: string; url: string; label: string; views: number; created_at: string }[]>(await fetch("/api/share", { headers: await headers() })),
  report: async (token: string, lang: string) => handle<Report>(await fetch(`/api/report/${token}?lang=${lang}`)),
};

export function fmtMoney(n: number | null | undefined, currency?: string | null, digits = 0) {
  if (n == null) return "—";
  const v = new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(n);
  return currency ? `${v} ${currency}` : v;
}
