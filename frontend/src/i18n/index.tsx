import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { LANGUAGES, translations, type Dict, type Lang } from "./translations";

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: keyof Dict) => string };

const I18nContext = createContext<Ctx | null>(null);

function detect(): Lang {
  try {
    const saved = localStorage.getItem("cv_lang");
    if (saved && LANGUAGES.some((l) => l.code === saved)) return saved as Lang;
  } catch {}
  const nav = (navigator.language || "en").slice(0, 2);
  return (LANGUAGES.some((l) => l.code === nav) ? nav : "en") as Lang;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detect);
  const setLang = (l: Lang) => {
    setLangState(l);
    try { localStorage.setItem("cv_lang", l); } catch {}
  };
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const value = useMemo<Ctx>(() => ({
    lang, setLang, t: (k) => translations[lang][k] ?? translations.en[k] ?? k,
  }), [lang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useT outside I18nProvider");
  return ctx;
}

export { LANGUAGES };
export type { Lang };
