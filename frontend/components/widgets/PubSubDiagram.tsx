"use client";

import { useState } from "react";
import { Plus, Minus } from "lucide-react";

type Rel = "reliable" | "best_effort";
interface Ep { name: string; rel: Rel }

/** Conceptual, editable publish/subscribe model. Not live data (clearly labelled). */
export function PubSubDiagram({ config }: { config: any }) {
  const [pubs, setPubs] = useState<Ep[]>((config.publishers ?? ["publisher"]).map((n: string) => ({ name: n, rel: "reliable" as Rel })));
  const [subs, setSubs] = useState<Ep[]>((config.subscribers ?? ["subscriber"]).map((n: string) => ({ name: n, rel: "reliable" as Rel })));
  const topic: string = config.topic ?? "/topic";
  const type: string = config.type ?? "";

  const compatible = (p: Ep, s: Ep) => !(p.rel === "best_effort" && s.rel === "reliable");
  const W = 520, rowH = 46;
  const H = Math.max(pubs.length, subs.length, 1) * rowH + 40;
  const y = (i: number, n: number) => H / 2 + (i - (n - 1) / 2) * rowH;
  const tx = W / 2, ty = H / 2;

  const toggle = (list: Ep[], set: (l: Ep[]) => void, i: number) =>
    set(list.map((e, j) => (j === i ? { ...e, rel: e.rel === "reliable" ? "best_effort" : "reliable" } : e)));

  return (
    <div className="my-3 rounded-lg border border-line bg-[#0f1012] p-3">
      <div className="mb-2 flex items-center justify-between text-[11px] text-muted">
        <span>Concept model — not live data. Click an endpoint to toggle its reliability.</span>
        <span className="flex gap-1">
          <button className="rounded border border-line px-1.5 hover:bg-panel2" onClick={() => setSubs([...subs, { name: `subscriber_${subs.length + 1}`, rel: "reliable" }])}>
            <Plus size={11} className="inline" /> subscriber
          </button>
          {subs.length > 1 && (
            <button className="rounded border border-line px-1.5 hover:bg-panel2" onClick={() => setSubs(subs.slice(0, -1))}><Minus size={11} className="inline" /></button>
          )}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Publishers and subscribers on ${topic}`}>
        {pubs.map((p, i) => (
          <line key={`pl${i}`} x1={120} y1={y(i, pubs.length)} x2={tx - 70} y2={ty} stroke="var(--series-1)" strokeWidth={2} className="flowing" />
        ))}
        {subs.map((s, i) => {
          const ok = pubs.some((p) => compatible(p, s));
          return (
            <g key={`sl${i}`}>
              <line x1={tx + 70} y1={ty} x2={W - 120} y2={y(i, subs.length)} stroke={ok ? "var(--good)" : "var(--bad)"} strokeWidth={2}
                className={ok ? "flowing" : undefined} strokeDasharray={ok ? undefined : "3 5"} />
              {!ok && <text x={(tx + 70 + W - 120) / 2} y={(ty + y(i, subs.length)) / 2 - 6} fill="var(--bad)" fontSize={10} textAnchor="middle">incompatible QoS</text>}
            </g>
          );
        })}
        <rect x={tx - 70} y={ty - 18} width={140} height={36} rx={18} fill="#1d2633" stroke="var(--accent)" />
        <text x={tx} y={ty - 2} fill="var(--ink)" fontSize={12} textAnchor="middle" fontFamily="monospace">{topic}</text>
        <text x={tx} y={ty + 11} fill="var(--muted)" fontSize={9} textAnchor="middle" fontFamily="monospace">{type}</text>
        {pubs.map((p, i) => (
          <g key={`p${i}`} onClick={() => toggle(pubs, setPubs, i)} className="cursor-pointer">
            <rect x={4} y={y(i, pubs.length) - 16} width={116} height={32} rx={6} fill="var(--panel-2)" stroke="var(--line)" />
            <text x={62} y={y(i, pubs.length) - 1} fill="var(--ink)" fontSize={11} textAnchor="middle">{p.name}</text>
            <text x={62} y={y(i, pubs.length) + 11} fill={p.rel === "reliable" ? "var(--ink-2)" : "var(--warn)"} fontSize={9} textAnchor="middle">{p.rel.toUpperCase()}</text>
          </g>
        ))}
        {subs.map((s, i) => (
          <g key={`s${i}`} onClick={() => toggle(subs, setSubs, i)} className="cursor-pointer">
            <rect x={W - 120} y={y(i, subs.length) - 16} width={116} height={32} rx={6} fill="var(--panel-2)" stroke="var(--line)" />
            <text x={W - 62} y={y(i, subs.length) - 1} fill="var(--ink)" fontSize={11} textAnchor="middle">{s.name}</text>
            <text x={W - 62} y={y(i, subs.length) + 11} fill={s.rel === "reliable" ? "var(--ink-2)" : "var(--warn)"} fontSize={9} textAnchor="middle">{s.rel.toUpperCase()}</text>
          </g>
        ))}
      </svg>
      <div className="mt-1 text-[11px] text-muted">Publishers (left) → topic → subscribers (right). Rule: a RELIABLE subscriber needs a RELIABLE publisher.</div>
    </div>
  );
}
