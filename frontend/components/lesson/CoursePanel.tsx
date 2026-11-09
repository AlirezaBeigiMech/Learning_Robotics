"use client";

import clsx from "clsx";
import { useEffect, useState } from "react";
import { AlertTriangle, BookOpen, CheckCircle2, ChevronLeft, ChevronRight, Circle, FileCode2, FlaskConical, Lightbulb, Radar, Target } from "lucide-react";
import { api, Progress } from "@/lib/api";
import { useLesson } from "@/lib/lesson";
import { Badge, Button } from "../ui";
import { LessonMarkdown } from "./Markdown";

interface Hint { level: number; text: string; solution?: Record<string, string> }

export function CoursePanel() {
  const { lesson, progress, setProgress, requestOpen, submit, grading, submissions, setLabTab } = useLesson();
  const [stepIdx, setStepIdx] = useState(0);
  const [hints, setHints] = useState<Record<string, Hint[]>>({});
  const [verify, setVerify] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!lesson) return;
    const i = lesson.steps.findIndex((s) => s.id === progress?.current_step);
    setStepIdx(i >= 0 ? i : 0);
    api<Record<string, Hint[]>>(`/api/progress/lessons/${lesson.id}/hints`).then(setHints);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lesson?.id]);

  if (!lesson || !progress) return null;
  const step = lesson.steps[stepIdx];
  const done = new Set(progress.steps_completed);
  const stepHints = hints[step.id] ?? [];
  const nextHintLevel = stepHints.length + 1;
  const cp = step.completion.checkpoint ? lesson.checkpoints.find((c) => c.id === step.completion.checkpoint) : null;
  const lastForCp = cp ? submissions.find((s) => s.checkpoint_id === cp.id) : null;

  const goto = (i: number) => {
    setStepIdx(i);
    setVerify(null);
    api<Progress>(`/api/progress/lessons/${lesson.id}/current`, { body: { step_id: lesson.steps[i].id } }).then(setProgress);
    if (lesson.steps[i].focus_file) requestOpen(lesson.steps[i].focus_file!);
  };

  const doVerify = async () => {
    setBusy(true);
    try {
      const r = await api<{ completed: boolean; reason: string; progress: Progress }>(
        `/api/progress/lessons/${lesson.id}/steps/${step.id}/complete`, { body: {} });
      setVerify({ ok: r.completed, text: r.reason });
      setProgress(r.progress);
    } finally {
      setBusy(false);
    }
  };

  const takeHint = async () => {
    const h = await api<Hint>(`/api/progress/lessons/${lesson.id}/steps/${step.id}/hint`, { body: { level: nextHintLevel } });
    setHints({ ...hints, [step.id]: [...stepHints, h] });
    setProgress({ ...progress, hints_used: { ...progress.hints_used, [step.id]: h.level } });
  };

  const kindIcon = { read: BookOpen, code: FileCode2, run: Radar, observe: Radar, debug: FlaskConical, submit: Target }[step.kind] ?? BookOpen;
  const KindIcon = kindIcon;

  return (
    <div className="flex h-full flex-col bg-panel">
      <div className="border-b border-line p-3">
        <a href="/dashboard" className="text-xs text-muted hover:text-ink2">← Course · Chapter {lesson.chapter}</a>
        <h1 className="mt-1 text-[15px] font-semibold leading-snug">{lesson.title}</h1>
        <div className="mt-1 flex flex-wrap gap-1">
          <Badge>{lesson.difficulty}</Badge>
          <Badge>{lesson.estimated_minutes} min</Badge>
          {progress.status === "completed" && <Badge tone="good"><CheckCircle2 size={11} /> completed</Badge>}
        </div>
        {lesson.missing_requirements?.length > 0 && (
          <div className="mt-2 rounded border border-[#5c4614] bg-[#33270d] p-2 text-xs text-ink2">
            <div className="flex items-center gap-1 font-medium text-warn"><AlertTriangle size={12} /> Not installed on this computer</div>
            <p className="mt-1">This lesson runs a separate desktop simulator. Building works without it, but launching and grading do not.</p>
            <ul className="ml-4 mt-1 list-disc space-y-0.5">
              {lesson.missing_requirements.map((r) => (
                <li key={r.id}>
                  <a href={r.url} target="_blank" rel="noreferrer" className="text-accent underline">{r.name}</a>: {r.where}
                </li>
              ))}
            </ul>
            <p className="mt-1 text-muted">Then restart the academy.</p>
          </div>
        )}
        <details className="mt-2 text-xs text-ink2">
          <summary className="cursor-pointer text-muted">Objectives, prerequisites & book reference</summary>
          <ul className="ml-4 mt-1 list-disc space-y-0.5">{lesson.objectives.map((o) => <li key={o}>{o}</li>)}</ul>
          <p className="mt-1 text-muted">Prerequisites: {lesson.prerequisites.join(", ") || "none"} · ROS deps: {lesson.ros_dependencies.join(", ")}</p>
          <p className="text-muted">Book: ch. {lesson.book_reference.chapter} — {lesson.book_reference.sections.join("; ")}</p>
        </details>
      </div>

      <ol className="max-h-[34%] shrink-0 overflow-y-auto border-b border-line py-1">
        {lesson.steps.map((s, i) => (
          <li key={s.id}>
            <button onClick={() => goto(i)} className={clsx("flex w-full items-center gap-2 px-3 py-1 text-left text-[13px]",
              i === stepIdx ? "bg-panel2 text-ink" : "text-ink2 hover:bg-panel2")}>
              {done.has(s.id) ? <CheckCircle2 size={14} className="shrink-0 text-good" /> : <Circle size={14} className="shrink-0 text-muted" />}
              <span className="w-4 shrink-0 text-muted">{i + 1}</span>
              <span className="truncate">{s.title}</span>
            </button>
          </li>
        ))}
      </ol>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="mb-2 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted">
          <KindIcon size={12} /> Step {stepIdx + 1} · {step.kind}
          {done.has(step.id) && <Badge tone="good" className="ml-1">done</Badge>}
        </div>
        <LessonMarkdown source={step.markdown} />

        {step.focus_file && (
          <button className="mt-2 text-xs text-accent hover:underline" onClick={() => requestOpen(step.focus_file!)}>
            Open {step.focus_file}
          </button>
        )}

        {stepHints.length > 0 && (
          <div className="mt-4 space-y-2">
            {stepHints.map((h) => (
              <div key={h.level} className="rounded-md border border-[#4a3a17] bg-[#1d180c] p-2.5 text-[13px]">
                <div className="mb-1 text-[11px] font-semibold text-warn">Hint {h.level} / {step.hint_count}</div>
                <div className="text-ink2">{h.text}</div>
                {h.solution && Object.entries(h.solution).filter(([p]) => /\.(cpp|hpp|h|xml|xacro|urdf|txt|py)$/.test(p) && !p.endsWith("package.xml")).map(([p, src]) => (
                  <details key={p} className="mt-2">
                    <summary className="cursor-pointer font-mono text-xs text-ink2">{p}</summary>
                    <pre className="mt-1 max-h-72 overflow-auto rounded bg-[#0c0d0f] p-2 font-mono text-[11.5px]">{src}</pre>
                  </details>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-2 border-t border-line p-3">
        {verify && <div className={clsx("text-xs", verify.ok ? "text-good" : "text-warn")}>{verify.text}</div>}
        {cp && lastForCp && (lastForCp.status === "passed" || lastForCp.status === "failed") && (
          <button className="text-xs text-muted hover:text-ink2" onClick={() => setLabTab("tests")}>
            Last check: <span className={lastForCp.status === "passed" ? "text-good" : "text-bad"}>{lastForCp.status}</span>{" "}
            ({lastForCp.results.summary?.passed ?? 0}/{lastForCp.results.summary?.total ?? 0}) — view results
          </button>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {step.completion.type === "manual" && !done.has(step.id) && (
            <Button size="sm" variant="primary" onClick={doVerify} disabled={busy}>Mark as done</Button>
          )}
          {(step.completion.type === "graph" || step.completion.type === "graph_qos_mismatch") && (
            <Button size="sm" variant="primary" onClick={doVerify} disabled={busy}>
              <Radar size={13} /> Verify in live graph
            </Button>
          )}
          {cp && (
            <Button size="sm" variant="primary" disabled={grading} onClick={() => submit(cp.id)}>
              <FlaskConical size={13} /> {grading ? "Grading…" : cp.final ? "Submit project" : `Check: ${cp.title}`}
            </Button>
          )}
          {step.hint_count > 1 && nextHintLevel <= step.hint_count && (
            <Button size="sm" variant="ghost" onClick={takeHint}>
              <Lightbulb size={13} /> {nextHintLevel === step.hint_count ? "Show reference solution" : `Hint ${nextHintLevel}`}
            </Button>
          )}
          <span className="flex-1" />
          <Button size="sm" variant="ghost" disabled={stepIdx === 0} onClick={() => goto(stepIdx - 1)}><ChevronLeft size={14} /></Button>
          <Button size="sm" variant="ghost" disabled={stepIdx === lesson.steps.length - 1} onClick={() => goto(stepIdx + 1)}><ChevronRight size={14} /></Button>
        </div>
      </div>
    </div>
  );
}
