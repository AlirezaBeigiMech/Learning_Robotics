"use client";

import clsx from "clsx";
import { useState } from "react";
import { CheckCircle2, CircleAlert, EyeOff, Loader2, XCircle } from "lucide-react";
import { Submission } from "@/lib/api";
import { useLesson } from "@/lib/lesson";
import { Badge, Empty } from "../ui";

export function TestResults() {
  const { submissions, lesson } = useLesson();
  const [selId, setSelId] = useState<number | null>(null);
  const sel: Submission | undefined = submissions.find((s) => s.id === selId) ?? submissions[0];
  if (!sel) return <Empty title="No test runs yet">Use a step&apos;s Check button or Test ▸ in the toolbar. Tests run your real nodes in an isolated grader.</Empty>;
  const cpTitle = (id: string) => lesson?.checkpoints.find((c) => c.id === id)?.title ?? id;
  const r = sel.results;
  const running = sel.status === "queued" || sel.status === "running";

  return (
    <div className="flex h-full">
      <div className="w-44 shrink-0 overflow-y-auto border-r border-line">
        {submissions.map((s) => (
          <button key={s.id} onClick={() => setSelId(s.id)}
            className={clsx("block w-full border-b border-line px-3 py-2 text-left text-xs", s.id === sel.id ? "bg-panel2" : "hover:bg-panel2")}>
            <div className="flex items-center gap-1.5">
              {s.status === "passed" ? <CheckCircle2 size={12} className="text-good" /> : s.status === "failed" ? <XCircle size={12} className="text-bad" />
                : s.status === "error" ? <CircleAlert size={12} className="text-warn" /> : <Loader2 size={12} className="animate-spin text-accent" />}
              <span className="truncate">{cpTitle(s.checkpoint_id)}</span>
            </div>
            <div className="mt-0.5 text-[10px] text-muted">#{s.id} · {new Date(s.created_at + (s.created_at.endsWith("Z") ? "" : "Z")).toLocaleTimeString()}</div>
          </button>
        ))}
      </div>
      <div className="min-w-0 flex-1 overflow-y-auto p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold">{cpTitle(sel.checkpoint_id)}</span>
          <Badge tone={sel.status === "passed" ? "good" : sel.status === "failed" ? "bad" : sel.status === "error" ? "warn" : "accent"}>{sel.status}</Badge>
          {r.summary && <span className="text-xs text-muted">{r.summary.passed}/{r.summary.total} passed{r.summary.duration_s ? ` · ${r.summary.duration_s}s` : ""}</span>}
        </div>
        {running && (
          <p className="mt-3 flex items-center gap-2 text-xs text-muted"><Loader2 size={13} className="animate-spin" />
            Building a snapshot of your package and running the tests in an isolated ROS domain. This takes 20–90 s.</p>
        )}
        {r.error && <p className="mt-3 text-xs text-warn">{r.error}</p>}
        {r.build && !r.build.ok && (
          <div className="mt-3">
            <div className="text-xs font-semibold text-bad">Build failed{r.build.timed_out ? " (timeout)" : ""}. No tests were run.</div>
            {(r.build as any).diagnostics?.length > 0 && (
              <ul className="mt-1 space-y-0.5 font-mono text-[11px]">
                {(r.build as any).diagnostics.slice(0, 12).map((d: any, i: number) => (
                  <li key={i} className={d.severity === "error" ? "text-bad" : "text-warn"}>{d.path}:{d.line}:{d.column} {d.message}</li>
                ))}
              </ul>
            )}
            <details className="mt-1"><summary className="cursor-pointer text-[11px] text-muted">full build log</summary>
              <pre className="mt-1 max-h-80 overflow-auto rounded bg-[#0c0d0f] p-2 font-mono text-[11px] text-ink2">{r.build.log_tail}</pre>
            </details>
          </div>
        )}
        <div className="mt-3 space-y-2">
          {(r.tests ?? []).map((t) => (
            <div key={t.id} className={clsx("rounded-md border p-2.5", t.status === "passed" ? "border-line" : "border-[#5a2a2a] bg-[#1f1515]")}>
              <div className="flex items-start gap-2">
                {t.status === "passed" ? <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-good" /> : <XCircle size={15} className="mt-0.5 shrink-0 text-bad" />}
                <div className="min-w-0 flex-1">
                  <div className="text-[13px]">{t.title} {t.hidden && <Badge className="ml-1"><EyeOff size={10} /> hidden</Badge>}</div>
                  {t.status !== "passed" && (
                    <div className="mt-1 space-y-0.5 text-xs">
                      {t.expected && <div><span className="text-muted">Expected: </span>{t.expected}</div>}
                      {t.observed && <div><span className="text-muted">Observed: </span><span className="whitespace-pre-wrap font-mono text-[11px]">{t.observed}</span></div>}
                      {t.message && <div className="whitespace-pre-wrap font-mono text-[11px] text-bad">{t.message}</div>}
                      {t.suggestion && <div className="text-warn">Suggestion: {t.suggestion}</div>}
                    </div>
                  )}
                  {t.status === "passed" && t.observed && <div className="mt-0.5 text-[11px] text-muted">observed: {t.observed}</div>}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
