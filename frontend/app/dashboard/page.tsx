"use client";

import { useEffect, useState } from "react";
import { Award, Bot, CheckCircle2, Circle, CircleDot, Hammer, Lightbulb, Lock, Send } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button } from "@/components/ui";

interface Outline {
  title: string; description: string; ros_distro: string;
  sources: Record<string, string>;
  competencies: { id: string; title: string }[];
  sections: { id: string; title: string; chapters: number[] }[];
  chapters: { number: number; title: string; summary: string; status: string; topics: string[]; final_project: string;
              book_chapter: { title: string } | null;
              runtime: "windows" | "linux" | "linux_rt_host";
              competencies: string[];
              readings: { source: string; chapters: string; note: string }[];
              labs: string[];
              lessons: { id: string; title: string; difficulty: string; estimated_minutes: number }[] }[];
}

const RUNTIME: Record<Outline["chapters"][number]["runtime"], { label: string; tone: "neutral" | "warn" | "accent" }> = {
  windows: { label: "Runs on this PC", tone: "neutral" },
  linux: { label: "Linux VM", tone: "accent" },
  linux_rt_host: { label: "Bare-metal RT host", tone: "warn" },
};

// "Mastering ROS 2 ... (Joseph & Cacace, 2025)" → "Mastering ROS 2 ..."
const shortSource = (s: string) => s.replace(/\s*\(.*$/, "").replace(/\s+—.*$/, "");

export default function Dashboard() {
  const [user, setUser] = useState<any>(null);
  const [outline, setOutline] = useState<Outline | null>(null);
  const [progress, setProgress] = useState<any>(null);

  useEffect(() => {
    api("/api/me").then(setUser);
    api<Outline>("/api/courses").then(setOutline);
    api("/api/progress").then(setProgress);
  }, []);

  if (!outline || !progress || !user) return <div className="p-8 text-muted">Loading…</div>;
  const chapters = Object.fromEntries(outline.chapters.map((c) => [c.number, c]));
  const competency = Object.fromEntries(outline.competencies.map((c) => [c.id, c.title]));
  const coverage = outline.competencies.map((comp) => {
    const chs = outline.chapters.filter((c) => c.competencies.includes(comp.id));
    return { ...comp, total: chs.length, available: chs.filter((c) => c.status === "available").length };
  });
  const s = progress.stats;
  const stat = (icon: React.ReactNode, label: string, value: React.ReactNode) => (
    <div className="rounded-lg border border-line bg-panel p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted">{icon}{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  );

  return (
    <main className="mx-auto max-w-6xl p-4 sm:p-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Bot className="text-accent" />
          <div>
            <h1 className="text-lg font-semibold">{outline.title}</h1>
            <p className="text-xs text-muted">Welcome back, {user.display_name} · ROS 2 {outline.ros_distro}</p>
          </div>
        </div>
        <div className="flex gap-2">
          {progress.current_lesson && (
            <Button variant="primary" onClick={() => (window.location.href = `/lesson?id=${progress.current_lesson}`)}>Continue</Button>
          )}
        </div>
      </header>

      <section className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {stat(<CheckCircle2 size={13} />, "Lessons completed", s.lessons_completed)}
        {stat(<Hammer size={13} />, "Builds (successful)", `${s.build_attempts} (${s.successful_builds})`)}
        {stat(<Send size={13} />, "Submissions passed", `${s.passed_submissions} / ${s.submissions}`)}
        {stat(<Lightbulb size={13} />, "Hints used", s.hints_used)}
        {stat(<Award size={13} />, "Skills mastered", progress.skills.length)}
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="space-y-6">
          {outline.sections.map((sec) => (
            <section key={sec.id}>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{sec.title}</h2>
              <div className="space-y-2">
                {sec.chapters.map((n) => {
                  const ch = chapters[n];
                  const planned = ch.status === "planned";
                  return (
                    <div key={n} className="rounded-lg border border-line bg-panel p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="text-[15px] font-medium">{n}. {ch.title}</div>
                          {ch.readings.length > 0 && (
                            <div className="text-xs text-muted">
                              Read: {ch.readings.map((r) => [shortSource(outline.sources[r.source]), r.chapters && `ch. ${r.chapters}`]
                                .filter(Boolean).join(" ")).join(" · ")}
                            </div>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          <Badge tone={RUNTIME[ch.runtime].tone}>{RUNTIME[ch.runtime].label}</Badge>
                          {planned ? <Badge><Lock size={10} /> Planned</Badge> : <Badge tone="accent">Available</Badge>}
                        </div>
                      </div>
                      <p className="mt-2 text-[13px] text-ink2">{ch.summary}</p>
                      {ch.competencies.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {ch.competencies.map((c) => <Badge key={c}>{competency[c]}</Badge>)}
                        </div>
                      )}
                      {planned && ch.labs.length > 0 && (
                        <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs text-ink2">
                          {ch.labs.map((l) => <li key={l}>{l}</li>)}
                        </ul>
                      )}
                      {ch.lessons.length > 0 && (
                        <ul className="mt-3 space-y-1">
                          {ch.lessons.map((l) => {
                            const p = progress.lessons[l.id];
                            const icon = p?.status === "completed" ? <CheckCircle2 size={15} className="text-good" />
                              : p ? <CircleDot size={15} className="text-accent" /> : <Circle size={15} className="text-muted" />;
                            return (
                              <li key={l.id}>
                                <a href={`/lesson?id=${l.id}`} className="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-panel2">
                                  {icon}
                                  <span className="flex-1">{l.title}</span>
                                  <span className="text-xs text-muted">{l.difficulty} · {l.estimated_minutes} min</span>
                                </a>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                      {planned && <p className="mt-2 text-xs text-muted">Final project: {ch.final_project}</p>}
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border border-line bg-panel p-4">
            <h3 className="mb-2 text-sm font-semibold">Job skills coverage</h3>
            <ul className="space-y-2">
              {coverage.map((c) => (
                <li key={c.id} className="text-[13px]">
                  <div className="flex justify-between gap-2">
                    <span>{c.title}</span>
                    <span className="text-xs text-muted">{c.available}/{c.total} ch.</span>
                  </div>
                  <div className="mt-1 h-1.5 rounded bg-panel2">
                    <div className="h-1.5 rounded bg-accent" style={{ width: `${c.total ? (100 * c.available) / c.total : 0}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-line bg-panel p-4">
            <h3 className="mb-2 text-sm font-semibold">Project portfolio</h3>
            {progress.portfolio.length === 0 ? (
              <p className="text-xs text-muted">Completed lesson projects appear here, with the submission that passed.</p>
            ) : (
              <ul className="space-y-2">
                {progress.portfolio.map((p: any) => (
                  <li key={p.lesson_id} className="text-[13px]">
                    <a className="hover:underline" href={`/lesson?id=${p.lesson_id}`}>{p.title}</a>
                    <div className="text-xs text-muted">package <code>{p.package}</code> · submission #{p.submission_id}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="rounded-lg border border-line bg-panel p-4">
            <h3 className="mb-2 text-sm font-semibold">Skills</h3>
            {progress.skills.length === 0 ? <p className="text-xs text-muted">Skills are awarded when a lesson&apos;s final submission passes.</p> : (
              <div className="flex flex-wrap gap-1.5">
                {progress.skills.map((s: any) => <Badge key={s.skill} tone="good">{s.skill}</Badge>)}
              </div>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
