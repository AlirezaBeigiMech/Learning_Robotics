"use client";

import { create } from "zustand";
import { api, Lesson, Progress, Submission } from "./api";
import { useRuntime } from "./runtime";

export type LabTab = "graph" | "topics" | "terminal" | "tests" | "robot" | "tf" | "controllers";

interface LessonState {
  lesson: Lesson | null;
  progress: Progress | null;
  labTab: LabTab;
  selectedTopic: string | null;
  openFile: string | null; // request for the editor to open a file
  openFileNonce: number;
  submissions: Submission[];
  grading: boolean;
  workspaceVersion: number; // bump to make the editor reload the tree/files
  editorFile: { path: string; content: string } | null; // live editor buffer (for the robot preview)
  setEditorFile: (f: { path: string; content: string } | null) => void;
  saveAll: () => Promise<void>;
  setSaveAll: (fn: () => Promise<void>) => void;
  load: (id: string) => Promise<void>;
  setLabTab: (t: LabTab) => void;
  selectTopic: (t: string | null) => void;
  requestOpen: (path: string) => void;
  setProgress: (p: Progress) => void;
  refreshSubmissions: () => Promise<void>;
  submit: (checkpointId: string) => Promise<void>;
  bumpWorkspace: () => void;
}

export const useLesson = create<LessonState>((set, get) => ({
  lesson: null,
  progress: null,
  labTab: "graph",
  selectedTopic: null,
  openFile: null,
  openFileNonce: 0,
  submissions: [],
  grading: false,
  workspaceVersion: 0,
  editorFile: null,
  setEditorFile: (f) => set({ editorFile: f }),
  saveAll: async () => {},
  setSaveAll: (fn) => set({ saveAll: fn }),

  load: async (id) => {
    const lesson = await api<Lesson>(`/api/courses/lessons/${id}`);
    await api(`/api/workspace/lessons/${id}/open`, { body: { level: "guided" } });
    const progress = await api<Progress>(`/api/progress/lessons/${id}`);
    set({ lesson, progress, labTab: (lesson.lab_tabs[0] as LabTab) ?? "graph" });
    await get().refreshSubmissions();
  },
  setLabTab: (t) => set({ labTab: t }),
  selectTopic: (t) => set({ selectedTopic: t }),
  requestOpen: (path) => set((s) => ({ openFile: path, openFileNonce: s.openFileNonce + 1 })),
  setProgress: (p) => set({ progress: p }),
  bumpWorkspace: () => set((s) => ({ workspaceVersion: s.workspaceVersion + 1 })),

  refreshSubmissions: async () => {
    const id = get().lesson?.id;
    if (!id) return;
    const subs = await api<Submission[]>(`/api/assessment/submissions?lesson_id=${id}`);
    set({ submissions: subs, grading: subs.some((s) => s.status === "queued" || s.status === "running") });
  },

  submit: async (checkpointId) => {
    const lesson = get().lesson;
    if (!lesson) return;
    await get().saveAll();
    const sub = await api<Submission>("/api/assessment/submit", { body: { lesson_id: lesson.id, checkpoint_id: checkpointId } });
    set((s) => ({ submissions: [sub, ...s.submissions], grading: true, labTab: "tests" }));
    // The runtime socket pushes the final result; poll as a fallback.
    for (let i = 0; i < 200; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      const pushed = useRuntime.getState().submissions[sub.id];
      const cur = pushed && (pushed.status === "passed" || pushed.status === "failed" || pushed.status === "error")
        ? pushed : await api<Submission>(`/api/assessment/submissions/${sub.id}`);
      set((s) => ({ submissions: s.submissions.map((x) => (x.id === cur.id ? cur : x)) }));
      if (cur.status !== "queued" && cur.status !== "running") break;
    }
    set({ grading: false });
    set({ progress: await api<Progress>(`/api/progress/lessons/${lesson.id}`) });
  },
}));
