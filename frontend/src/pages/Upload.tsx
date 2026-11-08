import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Loader2, Trash2 } from "lucide-react";
import { useT } from "../i18n";
import { api, type Doc } from "../lib/api";
import { docTypeLabel } from "../components/ScoreParts";

type Job = { id: number; name: string; status: "processing" | "done" | "error"; error?: string; started: number };

export default function Upload() {
  const { t } = useT();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [drag, setDrag] = useState(false);
  const [, tick] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const seq = useRef(0);

  const refresh = useCallback(() => api.listDocs().then(setDocs).catch(() => {}), []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (!jobs.some((j) => j.status === "processing")) return;
    const h = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(h);
  }, [jobs]);

  // Files are read in parallel: the wait is the slowest file, not the sum.
  const handleFiles = (files: FileList | File[]) => {
    const list = Array.from(files);
    const started = list.map((f) => ({ id: ++seq.current, name: f.name, status: "processing" as const, started: Date.now() }));
    setJobs((j) => [...started, ...j]);
    list.forEach((f, i) => {
      const id = started[i].id;
      api.upload(f)
        .then(() => setJobs((j) => j.map((x) => (x.id === id ? { ...x, status: "done" } : x))))
        .catch((e) => setJobs((j) => j.map((x) => (x.id === id ? { ...x, status: "error", error: String((e as Error).message) } : x))))
        .finally(refresh);
    });
  };
  const SAMPLES = ["kivupay_mobile_money_statement.pdf", "banque_umurage_releve_de_compte.pdf", "rent_payment_receipts_2024.pdf"];
  const useSamples = async () => {
    const files = await Promise.all(SAMPLES.map(async (n) => new File([await (await fetch(`/samples/${n}`)).blob()], n, { type: "application/pdf" })));
    handleFiles(files);
  };
  const processing = jobs.filter((j) => j.status === "processing").length;
  const [hint1, ...hintRest] = t("upload_hint").split(". ");

  return (
    <div className="bg-grouped min-h-full">
      <div className="mx-auto max-w-2xl px-6 py-12">
        <h1 className="t-title">{t("upload_title")}</h1>

        <button
          type="button"
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
          onClick={() => inputRef.current?.click()}
          className={`group-card mt-6 block w-full p-10 text-center transition-[box-shadow,transform] active:scale-[.995] ${drag ? "shadow-[0_0_0_2px_var(--color-blue)]" : ""}`}
        >
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-blue/10 text-blue"><FileText className="h-6 w-6" /></span>
          <span className="t-body mt-4 block font-semibold">{hint1}.</span>
          <span className="t-caption mt-1 block text-secondary">{hintRest.join(". ")}</span>
          <input ref={inputRef} type="file" multiple accept="application/pdf,image/*" className="hidden"
                 onChange={(e) => { if (e.target.files) handleFiles(e.target.files); e.target.value = ""; }} />
        </button>

        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 px-1">
          <button type="button" className="btn-plain px-0" onClick={useSamples} disabled={processing > 0}>{t("upload_samples")}</button>
          <span className="t-caption text-tertiary">{t("upload_samples_hint")}</span>
        </div>

        {jobs.length > 0 && (
          <div className="group-card mt-4">
            {jobs.map((j) => (
              <div key={j.id} className="row flex items-center gap-3">
                {j.status === "processing" && <Loader2 className="h-4 w-4 animate-spin text-blue" />}
                {j.status === "done" && <span className="grid h-5 w-5 place-items-center rounded-full bg-green text-[0.7rem] font-bold text-white">✓</span>}
                {j.status === "error" && <span className="grid h-5 w-5 place-items-center rounded-full bg-red text-[0.7rem] font-bold text-white">✕</span>}
                <span className="t-body flex-1 truncate">{j.name}</span>
                <span className={`num t-caption ${j.status === "error" ? "text-red" : "text-secondary"}`}>
                  {j.status === "processing"
                    ? `${t("upload_processing")} ${Math.round((Date.now() - j.started) / 1000)}s`
                    : j.status === "done" ? t("upload_done") : (j.error || t("upload_error"))}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="mt-10 flex items-baseline justify-between px-1">
          <h2 className="t-heading">{t("docs_title")}</h2>
          {docs.length > 0 && (
            <button className="btn-plain t-caption" onClick={async () => { await api.reset(); setJobs([]); refresh(); }}>{t("docs_reset")}</button>
          )}
        </div>
        {docs.length === 0 ? (
          <p className="t-body mt-3 px-1 text-secondary">{t("docs_empty")}</p>
        ) : (
          <div className="group-card mt-3">
            {docs.map((d) => (
              <div key={d.id} className="row flex items-center gap-3">
                <div className="min-w-0 flex-1">
                  <p className="t-body font-semibold">{d.source_name || d.filename}</p>
                  <p className="t-caption text-secondary">
                    {docTypeLabel(t, d.doc_type)}, {d.tx_count} {t("docs_transactions")}{d.currency ? `, ${d.currency}` : ""}{d.language ? `, ${d.language.toUpperCase()}` : ""}
                    {d.period_start && <span className="num"> · {d.period_start} – {d.period_end}</span>}
                  </p>
                </div>
                <button className="rounded-full p-2 text-tertiary hover:bg-fill hover:text-red" title={t("docs_remove")} onClick={async () => { await api.deleteDoc(d.id); refresh(); }}>
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {docs.length > 0 && processing === 0 && (
          <div className="mt-8"><Link to="/dashboard" className="btn">{t("view_score")}</Link></div>
        )}
      </div>
    </div>
  );
}
