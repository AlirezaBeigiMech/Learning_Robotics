"use client";

import { useMemo, useRef, useState } from "react";

export interface Point { t: number; values: Record<string, number> }

/**
 * Live line chart for the numeric fields of a topic. One y-axis; series coloured in fixed categorical
 * order by field (colour follows the field, not its rank); 2 px lines; legend for >= 2 series;
 * crosshair + tooltip on hover.
 */
export function LineChart({ points, fields }: { points: Point[]; fields: string[] }) {
  const ref = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const W = 380, H = 170, L = 44, R = 8, T = 8, B = 20;

  const { t0, t1, lo, hi } = useMemo(() => {
    const ts = points.map((p) => p.t);
    const vs = points.flatMap((p) => fields.map((f) => p.values[f]).filter((v) => typeof v === "number"));
    let lo = Math.min(...vs), hi = Math.max(...vs);
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    if (lo === hi) { lo -= 1; hi += 1; }
    const pad = (hi - lo) * 0.08;
    return { t0: Math.min(...ts), t1: Math.max(...ts), lo: lo - pad, hi: hi + pad };
  }, [points, fields]);

  if (points.length < 2 || fields.length === 0) return <div className="py-6 text-center text-xs text-muted">Waiting for numeric samples…</div>;
  const x = (t: number) => L + ((t - t0) / Math.max(t1 - t0, 1e-6)) * (W - L - R);
  const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const ticks = [lo, (lo + hi) / 2, hi];
  const fmt = (v: number) => (Math.abs(v) >= 1000 ? v.toExponential(1) : Number(v.toPrecision(3)).toString());
  const hp = hover !== null ? points[hover] : null;

  const onMove = (e: React.MouseEvent) => {
    const r = ref.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const tt = t0 + ((px - L) / (W - L - R)) * (t1 - t0);
    let best = 0;
    points.forEach((p, i) => { if (Math.abs(p.t - tt) < Math.abs(points[best].t - tt)) best = i; });
    setHover(best);
  };

  return (
    <div className="relative">
      {fields.length >= 2 && (
        <div className="mb-1 flex flex-wrap gap-3 text-[11px] text-ink2">
          {fields.map((f, i) => (
            <span key={f} className="flex items-center gap-1"><span className="inline-block h-0.5 w-3" style={{ background: `var(--series-${(i % 8) + 1})` }} />{f}</span>
          ))}
        </div>
      )}
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} className="w-full" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#2a2c31" strokeWidth={1} />
            <text x={L - 6} y={y(v) + 3} textAnchor="end" fontSize={10} fill="var(--muted)">{fmt(v)}</text>
          </g>
        ))}
        <text x={W - R} y={H - 6} textAnchor="end" fontSize={10} fill="var(--muted)">last {(t1 - t0).toFixed(0)} s</text>
        {fields.map((f, i) => (
          <polyline key={f} fill="none" stroke={`var(--series-${(i % 8) + 1})`} strokeWidth={2} strokeLinejoin="round"
            points={points.filter((p) => typeof p.values[f] === "number").map((p) => `${x(p.t)},${y(p.values[f])}`).join(" ")} />
        ))}
        {hp && (
          <g>
            <line x1={x(hp.t)} x2={x(hp.t)} y1={T} y2={H - B} stroke="var(--muted)" strokeDasharray="3 3" />
            {fields.map((f, i) => typeof hp.values[f] === "number" && (
              <circle key={f} cx={x(hp.t)} cy={y(hp.values[f])} r={4} fill={`var(--series-${(i % 8) + 1})`} stroke="var(--bg)" strokeWidth={2} />
            ))}
          </g>
        )}
      </svg>
      {hp && (
        <div className="pointer-events-none absolute right-2 top-6 rounded border border-line bg-panel2 px-2 py-1 font-mono text-[11px]">
          <div className="text-muted">{new Date(hp.t * 1000).toLocaleTimeString()}</div>
          {fields.map((f) => <div key={f} className="text-ink">{f}: {hp.values[f]}</div>)}
        </div>
      )}
    </div>
  );
}
