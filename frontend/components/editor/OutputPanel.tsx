"use client";

import clsx from "clsx";
import { useEffect, useMemo, useRef, useState } from "react";
import { Square, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useRuntime } from "@/lib/runtime";

/** Real stdout/stderr of builds and nodes, one tab per process. */
export function OutputPanel() {
  const { processes, output, clearOutput } = useRuntime();
  const list = useMemo(() => Object.values(processes).sort((a, b) => b.id - a.id), [processes]);
  const [sel, setSel] = useState<number | null>(null);
  const notices = output[-1] ?? [];
  const current = sel ?? list[0]?.id ?? null;
  const proc = current !== null ? processes[current] : null;
  const lines = current !== null ? output[current] ?? [] : [];
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => { if (list[0]) setSel(list[0].id); }, [list[0]?.id]); // eslint-disable-line
  useEffect(() => { box.current?.scrollTo({ top: box.current.scrollHeight }); }, [lines.length, current]);

  const dot = (p: { running: boolean; exit_code: number | null; stopped_by_user: boolean }) =>
    p.running ? "bg-good" : p.exit_code === 0 || p.stopped_by_user ? "bg-muted" : "bg-bad";

  return (
    <div className="flex h-full flex-col bg-bg">
      <div className="flex h-8 shrink-0 items-stretch overflow-x-auto border-b border-line bg-panel text-xs">
        <span className="flex items-center px-3 font-semibold uppercase tracking-wide text-muted">Output</span>
        {list.map((p) => (
          <button key={p.id} onClick={() => setSel(p.id)}
            className={clsx("flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3",
              current === p.id ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink2")}>
            <span className={clsx("h-2 w-2 rounded-full", dot(p))} />
            {p.label} <span className="text-muted">#{p.id}</span>
          </button>
        ))}
      </div>
      {notices.length > 0 && (
        <div className="border-b border-line bg-[#1d180c] px-3 py-1 font-mono text-[11.5px] text-warn">{notices[notices.length - 1]}</div>
      )}
      <div ref={box} className="min-h-0 flex-1 overflow-auto px-3 py-2 font-mono text-[12px] leading-[1.45]">
        {proc === null ? (
          <div className="text-muted">Build or run something — real process output appears here.</div>
        ) : (
          <>
            {lines.map((l, i) => (
              <div key={i} className={clsx("whitespace-pre-wrap break-all",
                /\b(ERROR|Error|Traceback|error:|FATAL)\b/.test(l) ? "text-bad" : /\bWARN(ING)?\b/.test(l) ? "text-warn" : "text-ink2")}>{l}</div>
            ))}
            {!proc.running && (
              <div className={clsx("mt-1", proc.exit_code === 0 || proc.stopped_by_user ? "text-muted" : "text-bad")}>
                [{proc.stopped_by_user ? "stopped" : `process exited with code ${proc.exit_code}`}]
              </div>
            )}
          </>
        )}
      </div>
      {proc && (
        <div className="flex h-7 shrink-0 items-center gap-2 border-t border-line bg-panel px-2 text-[11px] text-muted">
          <span>pid {proc.pid} · {proc.kind}</span>
          <span className="flex-1" />
          {proc.running && proc.kind === "run" && (
            <button className="flex items-center gap-1 text-bad hover:underline" onClick={() => api("/api/runtime/stop", { body: { process_id: proc.id } })}>
              <Square size={10} /> stop
            </button>
          )}
          <button className="flex items-center gap-1 hover:text-ink2" onClick={() => clearOutput(proc.id)}><Trash2 size={10} /> clear</button>
        </div>
      )}
    </div>
  );
}
