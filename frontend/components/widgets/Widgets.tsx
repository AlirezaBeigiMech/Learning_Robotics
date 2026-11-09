"use client";

import clsx from "clsx";
import { AlertTriangle, ArrowLeftRight, Info } from "lucide-react";
import ReactMarkdown from "react-markdown";

export function Callout({ config }: { config: any }) {
  const kind: string = config.kind ?? "note";
  const Icon = kind === "warning" ? AlertTriangle : kind === "compare" ? ArrowLeftRight : Info;
  return (
    <div className={clsx("my-3 rounded-lg border p-3",
      kind === "warning" ? "border-[#4a3a17] bg-[#211b0e]" : "border-[#21354f] bg-[#111a26]")}>
      <div className={clsx("mb-1 flex items-center gap-1.5 text-[13px] font-semibold", kind === "warning" ? "text-warn" : "text-accent")}>
        <Icon size={14} /> {config.title}
      </div>
      <div className="prose-lesson text-[13px] [&_p]:my-1">
        <ReactMarkdown>{config.body ?? ""}</ReactMarkdown>
      </div>
    </div>
  );
}

/** Publisher × subscriber reliability compatibility table (the DDS request/offer rule). */
export function QosMatrix({ config }: { config: any }) {
  const hl = config.highlight ?? {};
  const rows = ["reliable", "best_effort"];
  const ok = (pub: string, sub: string) => !(pub === "best_effort" && sub === "reliable");
  return (
    <div className="my-3 overflow-x-auto">
      <table className="text-[12px]">
        <thead>
          <tr>
            <th className="border border-line bg-panel2 px-2 py-1 text-left">publisher offers ↓ / subscriber requests →</th>
            {rows.map((s) => <th key={s} className="border border-line bg-panel2 px-2 py-1 font-mono">{s.toUpperCase()}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p}>
              <td className="border border-line px-2 py-1 font-mono">{p.toUpperCase()}</td>
              {rows.map((s) => {
                const active = hl.publisher === p && hl.subscriber === s;
                return (
                  <td key={s} className={clsx("border border-line px-2 py-1", active && "outline outline-2 -outline-offset-2 outline-accent")}>
                    {ok(p, s) ? <span className="text-good">✓ connects</span> : <span className="text-bad">✗ no messages</span>}
                    {active && <span className="ml-1 text-[10px] text-accent">(your fault)</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1 text-[11px] text-muted">Offered QoS must be at least as strong as requested QoS. The same rule applies to durability (TRANSIENT_LOCAL &gt; VOLATILE).</p>
    </div>
  );
}
