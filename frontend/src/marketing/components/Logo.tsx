/** LumenAI wordmark — a lumen/aperture ring + type. Temporary, easily replaced. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg
        width="28"
        height="28"
        viewBox="0 0 32 32"
        role="img"
        aria-label="LumenAI logo"
        className="shrink-0"
      >
        <defs>
          <radialGradient id="lumen-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#eef2ff" />
            <stop offset="70%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="#4f46e5" />
          </radialGradient>
        </defs>
        <circle cx="16" cy="16" r="14" fill="none" stroke="#4f46e5" strokeWidth="2" />
        <circle cx="16" cy="16" r="6.5" fill="url(#lumen-core)" />
        {[0, 60, 120, 180, 240, 300].map((deg) => {
          const r = (deg * Math.PI) / 180;
          const x1 = 16 + Math.cos(r) * 9;
          const y1 = 16 + Math.sin(r) * 9;
          const x2 = 16 + Math.cos(r) * 12.5;
          const y2 = 16 + Math.sin(r) * 12.5;
          return <line key={deg} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#4f46e5" strokeWidth="1.6" strokeLinecap="round" />;
        })}
      </svg>
      <span className="text-lg font-semibold tracking-tight text-slate-900">
        Lumen<span className="text-primary">AI</span>
      </span>
    </span>
  );
}
