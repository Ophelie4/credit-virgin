/** Original illustration for a listing: sky, building and palm, tinted by the listing's palette. */
const PALETTES = [
  { sky: ["#ffd9b8", "#ffeede"], wall: "#f6b48f", trim: "#d9825b", accent: "#2f8f83" }, // sunset coral
  { sky: ["#cfe8ff", "#eef7ff"], wall: "#9cc9b4", trim: "#5e9c80", accent: "#f2a65a" }, // garden green
  { sky: ["#e4dcff", "#f4f0ff"], wall: "#8a83d6", trim: "#5e57b0", accent: "#ff9f6e" }, // wynwood violet
  { sky: ["#bfe3f5", "#e8f6fd"], wall: "#e9eef3", trim: "#9bb0c2", accent: "#2b8cc4" }, // brickell glass
  { sky: ["#d6f0d9", "#effaf0"], wall: "#f3e6cf", trim: "#c9a46b", accent: "#3f8f4f" }, // grove sand
  { sky: ["#ffe7c7", "#fff6e8"], wall: "#f4d8c4", trim: "#c47d55", accent: "#2e7fa8" }, // gables terracotta
];

export default function HomeArt({ palette = 0, type = "apartment", className = "" }: { palette?: number; type?: string | null; className?: string }) {
  const p = PALETTES[Math.abs(palette) % PALETTES.length];
  const id = `g${palette}${type}`;
  const tall = type === "apartment" && palette === 3;
  return (
    <svg viewBox="0 0 400 240" className={className} role="img" aria-hidden preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={p.sky[0]} /><stop offset="1" stopColor={p.sky[1]} />
        </linearGradient>
      </defs>
      <rect width="400" height="240" fill={`url(#${id})`} />
      <circle cx="330" cy="58" r="26" fill="#fff" opacity=".7" />
      <rect y="200" width="400" height="40" fill={p.trim} opacity=".18" />

      {type === "house" ? (
        <g>
          <rect x="120" y="110" width="170" height="92" fill={p.wall} rx="3" />
          <path d="M108 114 L205 58 L302 114 Z" fill={p.trim} />
          <rect x="190" y="150" width="30" height="52" fill={p.accent} rx="2" />
          <rect x="138" y="132" width="34" height="28" fill="#fff" opacity=".85" rx="2" />
          <rect x="238" y="132" width="34" height="28" fill="#fff" opacity=".85" rx="2" />
        </g>
      ) : tall ? (
        <g>
          <rect x="150" y="30" width="100" height="172" fill={p.wall} rx="3" />
          {Array.from({ length: 9 }).map((_, r) =>
            Array.from({ length: 4 }).map((__, c) => (
              <rect key={`${r}-${c}`} x={160 + c * 22} y={40 + r * 17} width="14" height="10" fill={p.accent} opacity={(r + c) % 3 ? 0.35 : 0.7} rx="1" />
            )))}
          <rect x="262" y="90" width="60" height="112" fill={p.trim} opacity=".55" rx="3" />
        </g>
      ) : (
        <g>
          <rect x={type === "studio" ? 150 : 125} y="82" width={type === "studio" ? 110 : 160} height="120" fill={p.wall} rx="3" />
          <rect x={type === "studio" ? 146 : 121} y="76" width={type === "studio" ? 118 : 168} height="10" fill={p.trim} rx="2" />
          {Array.from({ length: 3 }).map((_, r) =>
            Array.from({ length: type === "studio" ? 3 : 4 }).map((__, c) => (
              <rect key={`${r}-${c}`} x={(type === "studio" ? 164 : 140) + c * 35} y={98 + r * 30} width="22" height="18" fill="#fff" opacity=".85" rx="2" />
            )))}
          <rect x={type === "studio" ? 192 : 192} y="166" width="26" height="36" fill={p.accent} rx="2" />
        </g>
      )}

      {/* palm */}
      <g transform="translate(70 0)">
        <path d="M0 202 C4 160 8 130 4 98" stroke="#7a5a3a" strokeWidth="6" fill="none" strokeLinecap="round" />
        {[-60, -20, 20, 60, 150].map((a, i) => (
          <path key={i} d="M4 98 q24 -10 44 6" transform={`rotate(${a} 4 98)`} stroke={p.accent} strokeWidth="7" fill="none" strokeLinecap="round" />
        ))}
      </g>
    </svg>
  );
}
