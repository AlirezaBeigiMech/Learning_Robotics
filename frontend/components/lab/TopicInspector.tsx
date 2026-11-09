"use client";

import clsx from "clsx";
import { useEffect, useMemo, useState } from "react";
import { useLesson } from "@/lib/lesson";
import { useRuntime } from "@/lib/runtime";
import { Badge, Empty } from "../ui";
import { LineChart } from "./LineChart";

export function TopicInspector() {
  const graph = useRuntime((s) => s.graph);
  const echo = useRuntime((s) => s.echo);
  const send = useRuntime((s) => s.send);
  const { selectedTopic, selectTopic } = useLesson();
  const [view, setView] = useState<"chart" | "table">("chart");
  const [hiddenFields, setHiddenFields] = useState<Set<string>>(new Set());
  const topics = (graph?.topics ?? []).filter((t) => !t.system);
  const topic = graph?.topics.find((t) => t.name === selectedTopic);
  const e = selectedTopic ? echo[selectedTopic] : undefined;

  // subscribe to the selected topic; unsubscribe from the previous one
  useEffect(() => {
    if (!selectedTopic) return;
    send({ cmd: "echo", topic: selectedTopic });
    return () => send({ cmd: "stop_echo", topic: selectedTopic });
  }, [selectedTopic, send, !!topic]); // eslint-disable-line react-hooks/exhaustive-deps

  const fields = useMemo(() => {
    const s = new Set<string>();
    e?.series.slice(-20).forEach((p) => Object.keys(p.values).forEach((k) => s.add(k)));
    return [...s];
  }, [e?.series]);
  const shown = fields.filter((f) => !hiddenFields.has(f)).slice(0, 8);

  return (
    <div className="flex h-full">
      <div className="w-44 shrink-0 overflow-y-auto border-r border-line">
        <div className="px-3 py-2 text-[11px] uppercase tracking-wide text-muted">Topics (live)</div>
        {topics.length === 0 && <div className="px-3 text-xs text-muted">No topics yet.</div>}
        {topics.map((t) => (
          <button key={t.name} onClick={() => selectTopic(t.name)}
            className={clsx("block w-full truncate px-3 py-1 text-left font-mono text-xs", selectedTopic === t.name ? "bg-panel2 text-ink" : "text-ink2 hover:bg-panel2")}>
            {t.name}
          </button>
        ))}
      </div>
      <div className="min-w-0 flex-1 overflow-y-auto p-3">
        {!selectedTopic ? (
          <Empty title="Select a topic">Pick a topic on the left or click one in the ROS Graph. The inspector subscribes with a best-effort QoS, which never disturbs your nodes.</Empty>
        ) : (
          <>
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-mono text-sm">{selectedTopic}</span>
              <span className="font-mono text-xs text-muted">{topic?.types[0] ?? e?.msgType ?? "not in graph"}</span>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              <div className="rounded border border-line p-2"><div className="text-[11px] text-muted">measured rate</div><div className="text-lg font-semibold">{(e?.rate ?? 0).toFixed(1)} Hz</div></div>
              <div className="rounded border border-line p-2"><div className="text-[11px] text-muted">messages seen</div><div className="text-lg font-semibold">{e?.count ?? 0}</div></div>
              <div className="rounded border border-line p-2"><div className="text-[11px] text-muted">pubs / subs</div><div className="text-lg font-semibold">{topic?.publishers.length ?? 0} / {topic?.subscribers.length ?? 0}</div></div>
            </div>

            {topic && (
              <table className="mt-3 w-full text-[11.5px]">
                <thead><tr className="text-left text-muted"><th className="py-1">endpoint</th><th>node</th><th>reliability</th><th>durability</th></tr></thead>
                <tbody>
                  {[...topic.publishers.map((p) => ({ ...p, role: "pub" })), ...topic.subscribers.map((s) => ({ ...s, role: "sub" }))].map((ep, i) => (
                    <tr key={i} className="border-t border-line">
                      <td className="py-1"><Badge tone={ep.role === "pub" ? "accent" : "neutral"}>{ep.role}</Badge></td>
                      <td className="font-mono">{ep.node}</td>
                      <td className={clsx("font-mono", ep.qos.reliability === "best_effort" && "text-warn")}>{ep.qos.reliability}</td>
                      <td className="font-mono">{ep.qos.durability}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {topic?.qos_pairs.filter((q) => q.compatible !== "ok").map((q) => (
              <div key={q.publisher + q.subscriber} className="mt-2 rounded border border-[#5a2a2a] bg-[#2b1a1a] p-2 text-xs text-bad">
                {q.publisher} → {q.subscriber}: {q.reason || "incompatible QoS"}
              </div>
            ))}

            <div className="mt-3 flex items-center gap-2 text-xs">
              <span className="font-semibold text-ink2">Numeric fields</span>
              <span className="flex-1" />
              <button className={clsx(view === "chart" ? "text-ink" : "text-muted")} onClick={() => setView("chart")}>chart</button>
              <button className={clsx(view === "table" ? "text-ink" : "text-muted")} onClick={() => setView("table")}>table</button>
            </div>
            {fields.length > 1 && (
              <div className="mt-1 flex flex-wrap gap-2 text-[11px]">
                {fields.map((f) => (
                  <label key={f} className="flex items-center gap-1 font-mono">
                    <input type="checkbox" checked={!hiddenFields.has(f)} onChange={() => setHiddenFields((h) => { const n = new Set(h); n.has(f) ? n.delete(f) : n.add(f); return n; })} />{f}
                  </label>
                ))}
              </div>
            )}
            <div className="mt-1 rounded border border-line p-2">
              {view === "chart" ? <LineChart points={e?.series ?? []} fields={shown} /> : (
                <div className="max-h-48 overflow-auto font-mono text-[11px]">
                  <table className="w-full"><thead><tr className="text-left text-muted"><th>time</th>{shown.map((f) => <th key={f}>{f}</th>)}</tr></thead>
                    <tbody>{(e?.series ?? []).slice(-50).reverse().map((p, i) => (
                      <tr key={i}><td className="text-muted">{new Date(p.t * 1000).toLocaleTimeString()}</td>{shown.map((f) => <td key={f}>{p.values[f]}</td>)}</tr>
                    ))}</tbody></table>
                </div>
              )}
            </div>

            <div className="mt-3 text-xs font-semibold text-ink2">Latest messages</div>
            <div className="mt-1 space-y-1">
              {(e?.last ?? []).slice(0, 6).map((m, i) => (
                <pre key={i} className={clsx("overflow-x-auto rounded bg-[#0c0d0f] p-1.5 font-mono text-[11px]", i > 0 && "opacity-60")}>{JSON.stringify(m)}</pre>
              ))}
              {!e?.last.length && <div className="text-xs text-muted">No messages received yet (shown at most 10 per second).</div>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
