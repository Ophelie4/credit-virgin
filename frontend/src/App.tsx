import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { LogIn, LogOut } from "lucide-react";
import { LANGUAGES, useT, type Lang } from "./i18n";
import { getDemoRole, setDemoRole, setTokenGetter } from "./lib/api";
import { market, type Me, type Role } from "./lib/market";
import Landing from "./pages/Landing";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import Report from "./pages/Report";
import Homes from "./pages/Homes";
import HomeDetail from "./pages/HomeDetail";
import MyApplications from "./pages/MyApplications";
import { LandlordHome, LandlordInbox, ListingForm } from "./pages/Landlord";

/* ---------------------------------------------------------------- session */
type Session = { me: Me | null; refresh: () => Promise<void>; signedIn: boolean; switchDemo: (r: Role) => void };
const SessionCtx = createContext<Session>({ me: null, refresh: async () => {}, signedIn: false, switchDemo: () => {} });
export const useSession = () => useContext(SessionCtx);

function Logo() {
  return <Link to="/" className="text-[1.0625rem] font-semibold tracking-[-0.02em]">Credit Virgin</Link>;
}

export function LanguagePicker() {
  const { lang, setLang, t } = useT();
  return (
    <select value={lang} onChange={(e) => setLang(e.target.value as Lang)} className="t-caption rounded-full bg-fill px-3 py-1.5 font-medium" aria-label={t("language")}>
      {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
    </select>
  );
}

/** Segmented control to view the demo as a renter or a landlord (when not signed in). */
function DemoSwitch() {
  const { t } = useT();
  const { me, switchDemo } = useSession();
  const role = me?.role ?? getDemoRole();
  return (
    <div className="flex rounded-full bg-fill p-0.5" role="group" aria-label={t("view_as")}>
      {(["renter", "landlord"] as Role[]).map((r) => (
        <button key={r} onClick={() => switchDemo(r)} aria-pressed={role === r}
                className={`t-caption rounded-full px-3 py-1 font-medium transition-colors ${role === r ? "bg-white text-label shadow-[0_1px_3px_rgba(0,0,0,.12)]" : "text-secondary"}`}>
          {t(r === "renter" ? "role_renter" : "role_landlord")}
        </button>
      ))}
    </div>
  );
}

function AuthButton({ authEnabled }: { authEnabled: boolean }) {
  const { t } = useT();
  const { isAuthenticated, loginWithRedirect, logout, user } = useAuth0();
  if (!authEnabled) return null;
  if (isAuthenticated) {
    return (
      <button className="btn-tint py-1.5 text-[0.875rem]" onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })} title={t("nav_logout")}>
        {user?.picture && <img src={user.picture} alt="" className="h-5 w-5 rounded-full" />}
        <span className="hidden md:inline">{user?.given_name ?? user?.name ?? ""}</span>
        <LogOut className="h-4 w-4" />
      </button>
    );
  }
  return <button className="btn py-1.5 text-[0.875rem]" onClick={() => loginWithRedirect()}><LogIn className="h-4 w-4" /> {t("nav_login")}</button>;
}

/* ---------------------------------------------------------------- welcome (pick a role) */
function Welcome() {
  const { t } = useT();
  const { refresh } = useSession();
  const nav = useNavigate();
  const pick = async (role: Role) => { await market.updateMe({ role }); await refresh(); nav(role === "landlord" ? "/landlord" : "/upload"); };
  return (
    <div className="bg-grouped min-h-full">
      <div className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h1 className="t-title">{t("welcome_title")}</h1>
        <p className="t-body-lg mt-3 text-secondary">{t("welcome_body")}</p>
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {(["renter", "landlord"] as Role[]).map((r) => (
            <button key={r} onClick={() => pick(r)} className="group-card p-8 text-left transition-transform active:scale-[.98]">
              <div className="t-heading">{t(r === "renter" ? "welcome_renter" : "welcome_landlord")}</div>
              <p className="t-body mt-2 text-secondary">{t(r === "renter" ? "welcome_renter_b" : "welcome_landlord_b")}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- app */
export default function App({ authEnabled }: { authEnabled: boolean }) {
  const { t } = useT();
  const loc = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, getAccessTokenSilently } = useAuth0();
  const [me, setMe] = useState<Me | null>(null);
  const signedIn = authEnabled && isAuthenticated;

  useEffect(() => {
    setTokenGetter(signedIn ? () => getAccessTokenSilently().then((x) => x ?? null).catch(() => null) : null);
  }, [signedIn, getAccessTokenSilently]);

  const refresh = useCallback(async () => {
    try { setMe(await market.me()); } catch { setMe(null); }
  }, []);
  useEffect(() => { if (!authEnabled || !isLoading) refresh(); }, [refresh, signedIn, isLoading, authEnabled]);

  const switchDemo = (r: Role) => { setDemoRole(r); refresh(); navigate(r === "landlord" ? "/landlord" : "/homes"); };

  const isReport = loc.pathname.startsWith("/r/");
  const role = me?.role;
  const link = ({ isActive }: { isActive: boolean }) =>
    `t-caption shrink-0 rounded-full px-3 py-1.5 font-medium transition-colors ${isActive ? "bg-label text-white" : "text-secondary hover:text-label"}`;
  const links = role === "landlord"
    ? [["/landlord", t("nav_listings")], ["/landlord/applications", t("nav_applications")]]
    : [["/upload", t("nav_upload")], ["/dashboard", t("nav_dashboard")], ["/homes", t("nav_homes")], ["/applications", t("nav_applications")]];

  const needsRole = signedIn && me && !me.role && loc.pathname !== "/welcome" && !isReport && loc.pathname !== "/";
  // Send each role to its own side instead of showing a permission error.
  const renterOnly = ["/homes", "/applications", "/upload", "/dashboard"].some((p) => loc.pathname === p || loc.pathname.startsWith("/homes/"));
  const landlordOnly = loc.pathname.startsWith("/landlord");
  const wrongSide = role === "landlord" && renterOnly ? "/landlord" : role === "renter" && landlordOnly ? "/homes" : null;

  return (
    <SessionCtx.Provider value={{ me, refresh, signedIn, switchDemo }}>
      <div className="flex min-h-screen flex-col">
        <header className="material sticky top-0 z-20">
          <div className="mx-auto flex h-12 max-w-5xl items-center justify-between gap-3 px-6">
            <Logo />
            {!isReport && (
              <nav className="hidden items-center gap-1 md:flex">
                {links.map(([to, label]) => <NavLink key={to} to={to} end={to === "/landlord"} className={link}>{label}</NavLink>)}
              </nav>
            )}
            <div className="flex items-center gap-2">
              {!isReport && !signedIn && <DemoSwitch />}
              <LanguagePicker />
              {!isReport && <AuthButton authEnabled={authEnabled} />}
            </div>
          </div>
          {!isReport && (
            <nav className="flex gap-1 overflow-x-auto px-4 pb-2 md:hidden">
              {links.map(([to, label]) => <NavLink key={to} to={to} end={to === "/landlord"} className={link}>{label}</NavLink>)}
            </nav>
          )}
        </header>

        <main className="flex-1">
          {needsRole ? <Navigate to="/welcome" replace /> : wrongSide ? <Navigate to={wrongSide} replace /> : (
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/welcome" element={<Welcome />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/homes" element={<Homes />} />
              <Route path="/homes/:id" element={<HomeDetail />} />
              <Route path="/applications" element={<MyApplications />} />
              <Route path="/landlord" element={<LandlordHome />} />
              <Route path="/landlord/new" element={<ListingForm />} />
              <Route path="/landlord/listings/:id" element={<ListingForm />} />
              <Route path="/landlord/applications" element={<LandlordInbox />} />
              <Route path="/r/:token" element={<Report />} />
            </Routes>
          )}
        </main>

        <footer className="bg-grouped"><div className="t-caption mx-auto max-w-5xl px-6 py-6 text-tertiary">{t("footer")} · creditvirgin.tech</div></footer>
      </div>
    </SessionCtx.Provider>
  );
}
