/** SVG diagram of the evidence path: capture → govern → report. Scrolls on small screens. */
const NODES = [
  { label: "Image capture", sub: "Borescope image", fill: "#eef2ff", stroke: "#4f46e5" },
  { label: "Metadata", sub: "Instrument · tray · time", fill: "#eef2ff", stroke: "#4f46e5" },
  { label: "Assistive analysis", sub: "Suggested findings", fill: "#f0f9ff", stroke: "#0284c7" },
  { label: "Baseline lineage", sub: "Approved comparison", fill: "#f0f9ff", stroke: "#0284c7" },
  { label: "Human review", sub: "Decision + rationale", fill: "#fffbeb", stroke: "#d97706" },
  { label: "Audit trail", sub: "Hash-chained record", fill: "#ecfdf5", stroke: "#059669" },
  { label: "Reports", sub: "Trends · audit evidence", fill: "#f8fafc", stroke: "#64748b" },
];

export function EvidencePathDiagram() {
  const w = 170;
  const gap = 26;
  const h = 92;
  const totalW = NODES.length * w + (NODES.length - 1) * gap;
  return (
    <div className="overflow-x-auto" role="img" aria-label="Evidence path from image capture through human review, audit trail, and reporting">
      <svg viewBox={`0 0 ${totalW} 140`} width={totalW} height="140" className="max-w-none">
        {NODES.map((n, i) => {
          const x = i * (w + gap);
          return (
            <g key={n.label}>
              {i < NODES.length - 1 && (
                <line
                  x1={x + w}
                  y1={24 + h / 2}
                  x2={x + w + gap}
                  y2={24 + h / 2}
                  stroke="#cbd5e1"
                  strokeWidth="2"
                  markerEnd="url(#arrow)"
                />
              )}
              <rect x={x} y={24} width={w} height={h} rx="10" fill={n.fill} stroke={n.stroke} strokeWidth="1.5" />
              <text x={x + w / 2} y={24 + 36} textAnchor="middle" fontSize="14" fontWeight="600" fill="#0f172a">
                {n.label}
              </text>
              <text x={x + w / 2} y={24 + 58} textAnchor="middle" fontSize="11.5" fill="#475569">
                {n.sub}
              </text>
              <text x={x + w / 2} y={18} textAnchor="middle" fontSize="11" fontWeight="700" fill={n.stroke}>
                {i + 1}
              </text>
            </g>
          );
        })}
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8" />
          </marker>
        </defs>
      </svg>
    </div>
  );
}
