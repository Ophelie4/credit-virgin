import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import HomeArt from "./HomeArt";

type M = { palette: number; property_type?: string | null; photo_urls?: string[] | null; tour_url?: string | null; title?: string };

/** Card cover: first photo if the listing has photos, otherwise the illustration. */
export function Cover({ h, className = "" }: { h: M; className?: string }) {
  const src = h.photo_urls?.[0];
  if (!src) return <HomeArt palette={h.palette} type={h.property_type} className={className} />;
  return <img src={src} alt="" loading="lazy" className={`object-cover ${className}`} />;
}

/** Listing hero: the walkthrough video (muted, looping, plays when on screen), then a photo gallery. */
export function TourHero({ h, tourLabel }: { h: M; tourLabel: string }) {
  const photos = h.photo_urls ?? [];
  const [active, setActive] = useState<number | "tour">(h.tour_url ? "tour" : 0);
  const [playing, setPlaying] = useState(true);
  const vid = useRef<HTMLVideoElement>(null);
  const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    const v = vid.current;
    if (!v) return;
    if (reduce) { v.pause(); setPlaying(false); return; }
    const io = new IntersectionObserver(([e]) => { e.isIntersecting ? v.play().catch(() => {}) : v.pause(); }, { threshold: 0.4 });
    io.observe(v);
    return () => io.disconnect();
  }, [active, reduce]);

  if (!photos.length && !h.tour_url) return <HomeArt palette={h.palette} type={h.property_type} className="h-56 w-full md:h-72" />;

  return (
    <div>
      <div className="relative aspect-video w-full overflow-hidden bg-black">
        {active === "tour" && h.tour_url ? (
          <>
            <video ref={vid} src={h.tour_url} poster={photos[0]} muted loop playsInline autoPlay={!reduce}
                   onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} className="h-full w-full object-cover" aria-label={tourLabel} />
            <span className="pill absolute left-4 top-4 bg-black/55 text-white backdrop-blur">{tourLabel}</span>
            <button onClick={() => { const v = vid.current; if (v) (v.paused ? v.play() : v.pause()); }}
                    className="absolute bottom-4 right-4 grid h-10 w-10 place-items-center rounded-full bg-black/55 text-white backdrop-blur"
                    aria-label={playing ? "Pause" : "Play"}>
              {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </button>
          </>
        ) : (
          <img src={photos[active as number]} alt="" className="h-full w-full object-cover" />
        )}
      </div>
      {(photos.length > 1 || h.tour_url) && (
        <div className="flex gap-2 overflow-x-auto p-3">
          {h.tour_url && (
            <button onClick={() => setActive("tour")} className={`relative h-14 w-24 shrink-0 overflow-hidden rounded-[10px] ${active === "tour" ? "shadow-[0_0_0_3px_var(--color-blue)]" : ""}`}>
              <img src={photos[0]} alt="" className="h-full w-full object-cover" />
              <span className="absolute inset-0 grid place-items-center bg-black/35 text-white"><Play className="h-4 w-4" /></span>
            </button>
          )}
          {photos.map((p, i) => (
            <button key={p} onClick={() => setActive(i)} className={`h-14 w-24 shrink-0 overflow-hidden rounded-[10px] ${active === i ? "shadow-[0_0_0_3px_var(--color-blue)]" : ""}`}>
              <img src={p} alt="" loading="lazy" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
