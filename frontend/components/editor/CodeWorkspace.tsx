"use client";

import clsx from "clsx";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Editor, { loader, OnMount } from "@monaco-editor/react";
import {
  ChevronDown, ChevronRight, File, FilePlus, Folder, FolderPlus, Hammer, Pencil, Play, RefreshCw, RotateCcw, Save, Square, Trash2, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { useLesson } from "@/lib/lesson";
import { useRuntime } from "@/lib/runtime";
import { Button } from "../ui";
import { RCLCPP_SNIPPETS } from "./snippets";

loader.config({ paths: { vs: "/monaco/vs" } }); // bundled locally, works offline

interface Entry { path: string; type: "file" | "dir"; size: number | null }
interface OpenFile { path: string; content: string; saved: string }
interface Diag { line: number; column: number; severity: string; message: string; source: string }
interface Status { built: boolean; domain_id: number; executables: Record<string, { executables: string[]; launch_files: string[] }> }

const LANG: Record<string, string> = { py: "python", xml: "xml", cfg: "ini", yaml: "yaml", yml: "yaml", md: "markdown",
  cpp: "cpp", hpp: "cpp", h: "cpp", c: "c", txt: "plaintext", json: "json", launch: "xml", urdf: "xml", xacro: "xml", lua: "lua" };
const langOf = (p: string) => LANG[p.split(".").pop() ?? ""] ?? (p.endsWith("CMakeLists.txt") ? "cmake" : "plaintext");

let snippetsRegistered = false;

export function CodeWorkspace() {
  const { lesson, openFile, openFileNonce, setSaveAll, workspaceVersion, bumpWorkspace, submit, grading, setEditorFile } = useLesson();
  const processes = useRuntime((s) => s.processes);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [files, setFiles] = useState<OpenFile[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [building, setBuilding] = useState(false);
  const [menu, setMenu] = useState<"run" | "test" | null>(null);
  const [message, setMessage] = useState<{ tone: "good" | "bad" | "muted"; text: string } | null>(null);
  const monacoRef = useRef<any>(null);
  const filesRef = useRef(files);
  filesRef.current = files;

  const refreshTree = useCallback(async () => {
    const t = await api<{ entries: Entry[] }>("/api/workspace/tree");
    setEntries(t.entries);
  }, []);
  const refreshStatus = useCallback(async () => setStatus(await api<Status>("/api/runtime/status")), []);

  useEffect(() => { refreshTree(); refreshStatus(); }, [refreshTree, refreshStatus, workspaceVersion]);

  // compiler errors from the last build, by file; kept so files opened later still show them
  const compilerDiags = useRef<Record<string, Diag[]>>({});
  const applyDiagnostics = useCallback((path: string, diags: Diag[], owner = "academy") => {
    const monaco = monacoRef.current;
    if (!monaco) return;
    const model = monaco.editor.getModels().find((m: any) => m.uri.path.endsWith("/" + path) || m.uri.path === path);
    if (!model) return;
    monaco.editor.setModelMarkers(model, owner, diags.map((d) => ({
      startLineNumber: d.line, startColumn: d.column, endLineNumber: d.line, endColumn: d.column + 200,
      message: `${d.message} (${d.source})`,
      severity: d.severity === "error" ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
    })));
  }, []);

  const open = useCallback(async (path: string) => {
    if (filesRef.current.some((f) => f.path === path)) { setActive(path); return; }
    try {
      const r = await api<{ content: string }>(`/api/workspace/file?path=${encodeURIComponent(path)}`);
      setFiles((fs) => (fs.some((f) => f.path === path) ? fs : [...fs, { path, content: r.content, saved: r.content }]));
      setActive(path);
    } catch (e: any) {
      setMessage({ tone: "bad", text: e.message });
    }
  }, []);

  useEffect(() => { if (openFile) open(openFile); }, [openFile, openFileNonce, open]);

  const save = useCallback(async (path: string) => {
    const f = filesRef.current.find((x) => x.path === path);
    if (!f || f.content === f.saved) return;
    const r = await api<{ diagnostics: Diag[] }>("/api/workspace/file", { method: "PUT", body: { path, content: f.content } });
    setFiles((fs) => fs.map((x) => (x.path === path ? { ...x, saved: f.content } : x)));
    applyDiagnostics(path, r.diagnostics);
  }, [applyDiagnostics]);

  const saveAll = useCallback(async () => {
    for (const f of filesRef.current) if (f.content !== f.saved) await save(f.path);
  }, [save]);
  useEffect(() => setSaveAll(saveAll), [saveAll, setSaveAll]);

  // live syntax / package.xml diagnostics while typing
  const activeFile = files.find((f) => f.path === active);
  // share the live buffer (unsaved edits included) with the robot preview
  useEffect(() => {
    const t = setTimeout(() => setEditorFile(activeFile ? { path: activeFile.path, content: activeFile.content } : null), 300);
    return () => clearTimeout(t);
  }, [activeFile?.path, activeFile?.content, setEditorFile]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!activeFile) return;
    const t = setTimeout(() => {
      api<{ diagnostics: Diag[] }>("/api/workspace/diagnostics", { body: { path: activeFile.path, content: activeFile.content } })
        .then((r) => applyDiagnostics(activeFile.path, r.diagnostics)).catch(() => {});
    }, 600);
    return () => clearTimeout(t);
  }, [activeFile?.content, activeFile?.path, applyDiagnostics]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!active) return;
    const t = setTimeout(() => applyDiagnostics(active, compilerDiags.current[active] ?? [], "compiler"), 150);
    return () => clearTimeout(t);
  }, [active, applyDiagnostics]);

  const onMount: OnMount = (editor, monaco) => {
    monacoRef.current = monaco;
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      const p = editor.getModel()?.uri.path.replace(/^\//, "");
      if (p) save(p);
    });
    if (!snippetsRegistered) {
      snippetsRegistered = true;
      monaco.languages.registerCompletionItemProvider("cpp", {
        provideCompletionItems: (model: any, position: any) => {
          const word = model.getWordUntilPosition(position);
          const range = { startLineNumber: position.lineNumber, endLineNumber: position.lineNumber, startColumn: word.startColumn, endColumn: word.endColumn };
          return { suggestions: RCLCPP_SNIPPETS.map((s) => ({
            label: s.label, detail: s.detail, insertText: s.insert, range,
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          })) };
        },
      });
    }
  };

  // ---- runtime actions -------------------------------------------------------------------
  const build = async () => {
    setBuilding(true);
    setMessage({ tone: "muted", text: "Building with colcon…" });
    try {
      await saveAll();
      const r = await api<{ ok: boolean; exit_code: number | null; duration_ms: number; errors?: string[];
                           diagnostics?: (Diag & { path: string })[] }>("/api/runtime/build", { body: { lesson_id: lesson?.id } });
      // compiler errors/warnings become red/yellow underlines in the editor
      const byFile: Record<string, Diag[]> = {};
      for (const d of r.diagnostics ?? []) (byFile[d.path] ??= []).push(d);
      const touched = new Set([...Object.keys(compilerDiags.current), ...Object.keys(byFile)]);
      compilerDiags.current = byFile;
      touched.forEach((p) => applyDiagnostics(p, byFile[p] ?? [], "compiler"));
      const firstErr = (r.diagnostics ?? []).find((d) => d.severity === "error");
      if (firstErr) open(firstErr.path);
      setMessage(r.ok ? { tone: "good", text: `Build succeeded in ${(r.duration_ms / 1000).toFixed(1)} s` }
        : { tone: "bad", text: r.errors?.length ? r.errors[0]
            : firstErr ? `${firstErr.path}:${firstErr.line}: ${firstErr.message}` : `Build failed (exit ${r.exit_code}). See the Output panel.` });
    } catch (e: any) {
      setMessage({ tone: "bad", text: e.message });
    } finally {
      setBuilding(false);
      refreshStatus();
    }
  };

  const run = async (pkg: string, exe?: string, launch?: string) => {
    setMenu(null);
    try {
      await api("/api/runtime/run", { body: { package: pkg, executable: exe, launch_file: launch } });
      setMessage({ tone: "muted", text: `Started ${pkg}/${exe ?? launch}` });
    } catch (e: any) {
      setMessage({ tone: "bad", text: e.message });
    }
  };

  const runningCount = Object.values(processes).filter((p) => p.running && p.kind === "run").length;
  const dirty = files.some((f) => f.content !== f.saved);

  // ---- file tree ---------------------------------------------------------------------------
  const visible = useMemo(() => entries.filter((e) => {
    const parts = e.path.split("/");
    for (let i = 1; i < parts.length; i++) if (collapsed.has(parts.slice(0, i).join("/"))) return false;
    return true;
  }), [entries, collapsed]);

  const fileOp = async (fn: () => Promise<unknown>) => {
    try { await fn(); await refreshTree(); } catch (e: any) { setMessage({ tone: "bad", text: e.message }); }
  };
  const parentOf = (p: string | null) => {
    if (!p) return lesson?.workspace.package ?? "";
    const e = entries.find((x) => x.path === p);
    return e?.type === "dir" ? p : p.split("/").slice(0, -1).join("/");
  };

  return (
    <div className="flex h-full flex-col bg-bg">
      {/* toolbar */}
      <div className="flex h-10 shrink-0 items-center gap-1.5 border-b border-line bg-panel px-2">
        <Button size="sm" onClick={saveAll} disabled={!dirty} title="Save all (Ctrl+S saves the current file)"><Save size={13} /> Save</Button>
        <Button size="sm" variant="primary" onClick={build} disabled={building}><Hammer size={13} /> {building ? "Building…" : "Build"}</Button>
        <div className="relative">
          <Button size="sm" onClick={() => setMenu(menu === "run" ? null : "run")} disabled={!status?.built}><Play size={13} /> Run <ChevronDown size={12} /></Button>
          {menu === "run" && status && (
            <div className="absolute left-0 top-8 z-20 min-w-60 rounded-md border border-line bg-panel2 py-1 shadow-xl">
              {Object.entries(status.executables).flatMap(([pkg, x]) => [
                ...x.executables.map((exe) => (
                  <button key={`${pkg}/${exe}`} className="block w-full px-3 py-1.5 text-left font-mono text-xs hover:bg-[#2c2e33]" onClick={() => run(pkg, exe)}>
                    ros2 run {pkg} {exe}
                  </button>
                )),
                ...x.launch_files.map((lf) => (
                  <button key={`${pkg}/${lf}`} className="block w-full px-3 py-1.5 text-left font-mono text-xs hover:bg-[#2c2e33]" onClick={() => run(pkg, undefined, lf)}>
                    ros2 launch {pkg} {lf}
                  </button>
                )),
              ])}
              {Object.values(status.executables).every((x) => !x.executables.length && !x.launch_files.length) && (
                <div className="px-3 py-1.5 text-xs text-muted">No executables installed. Build first.</div>
              )}
            </div>
          )}
        </div>
        <Button size="sm" variant="danger" disabled={!runningCount} onClick={() => api("/api/runtime/stop", { body: {} })}>
          <Square size={12} /> Stop{runningCount ? ` (${runningCount})` : ""}
        </Button>
        <div className="relative">
          <Button size="sm" onClick={() => setMenu(menu === "test" ? null : "test")} disabled={grading}>Test <ChevronDown size={12} /></Button>
          {menu === "test" && lesson && (
            <div className="absolute left-0 top-8 z-20 min-w-60 rounded-md border border-line bg-panel2 py-1 shadow-xl">
              {lesson.checkpoints.map((c) => (
                <button key={c.id} className="block w-full px-3 py-1.5 text-left text-xs hover:bg-[#2c2e33]" onClick={() => { setMenu(null); submit(c.id); }}>
                  {c.title} <span className="text-muted">({c.final ? "final, hidden tests" : `${c.test_count} file`})</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <span className="flex-1" />
        {message && <span className={clsx("truncate text-xs", message.tone === "good" ? "text-good" : message.tone === "bad" ? "text-bad" : "text-muted")}>{message.text}</span>}
        <Button size="sm" variant="ghost" title="Restore the starter files (your current package is backed up)" onClick={async () => {
          if (!lesson || !confirm("Reset this lesson's package to the starter files? Your current version is moved to a backup folder.")) return;
          await api(`/api/workspace/lessons/${lesson.id}/reset`, { body: { level: "guided" } });
          setFiles([]); setActive(null); bumpWorkspace();
          setMessage({ tone: "muted", text: "Package reset to starter (backup kept)." });
        }}><RotateCcw size={13} /> Reset</Button>
        <Button size="sm" variant="ghost" title="Stop all processes, the terminal and the telemetry agent" onClick={async () => {
          await api("/api/runtime/restart", { body: {} });
          setMessage({ tone: "muted", text: "Runtime restarted." });
        }}><RefreshCw size={13} /> Restart</Button>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* explorer */}
        <div className="flex w-56 shrink-0 flex-col border-r border-line bg-panel">
          <div className="flex h-8 items-center justify-between px-2 text-[11px] uppercase tracking-wide text-muted">
            <span>ws / src</span>
            <span className="flex gap-0.5">
              <button title="New file" className="rounded p-1 hover:bg-panel2" onClick={() => {
                const name = prompt("New file path (relative to src):", parentOf(active) + "/");
                if (name) fileOp(async () => { await api("/api/workspace/file", { body: { path: name, content: "" } }); open(name); });
              }}><FilePlus size={13} /></button>
              <button title="New folder" className="rounded p-1 hover:bg-panel2" onClick={() => {
                const name = prompt("New folder path (relative to src):", parentOf(active) + "/");
                if (name) fileOp(() => api("/api/workspace/dir", { body: { path: name } }));
              }}><FolderPlus size={13} /></button>
              <button title="Refresh" className="rounded p-1 hover:bg-panel2" onClick={refreshTree}><RefreshCw size={12} /></button>
            </span>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto pb-2 text-[13px]">
            {visible.map((e) => {
              const depth = e.path.split("/").length - 1;
              const name = e.path.split("/").pop();
              const isDir = e.type === "dir";
              return (
                <div key={e.path} className={clsx("group flex cursor-pointer items-center gap-1 py-[3px] pr-1 hover:bg-panel2", active === e.path && "bg-panel2")}
                  style={{ paddingLeft: 6 + depth * 12 }}
                  onClick={() => (isDir ? setCollapsed((c) => { const n = new Set(c); n.has(e.path) ? n.delete(e.path) : n.add(e.path); return n; }) : open(e.path))}>
                  {isDir ? (collapsed.has(e.path) ? <ChevronRight size={12} /> : <ChevronDown size={12} />) : <span className="w-3" />}
                  {isDir ? <Folder size={13} className="text-[#c9a85a]" /> : <File size={13} className="text-muted" />}
                  <span className="flex-1 truncate">{name}</span>
                  <span className="hidden gap-0.5 group-hover:flex">
                    <button title="Rename" onClick={(ev) => { ev.stopPropagation(); const to = prompt("Rename to:", e.path); if (to && to !== e.path) fileOp(() => api("/api/workspace/rename", { body: { src: e.path, dst: to } })); }}><Pencil size={11} /></button>
                    <button title="Delete" onClick={(ev) => { ev.stopPropagation(); if (confirm(`Delete ${e.path}?`)) fileOp(async () => { await api(`/api/workspace/file?path=${encodeURIComponent(e.path)}`, { method: "DELETE" }); setFiles((fs) => fs.filter((f) => !f.path.startsWith(e.path))); }); }}><Trash2 size={11} /></button>
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* editor */}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-8 shrink-0 overflow-x-auto border-b border-line bg-panel">
            {files.map((f) => (
              <div key={f.path} onClick={() => setActive(f.path)}
                className={clsx("flex cursor-pointer items-center gap-1.5 border-r border-line px-3 text-xs",
                  active === f.path ? "bg-bg text-ink" : "text-muted hover:text-ink2")}>
                <span className="whitespace-nowrap">{f.path.split("/").pop()}{f.content !== f.saved && " ●"}</span>
                <button onClick={(ev) => {
                  ev.stopPropagation();
                  if (f.content !== f.saved && !confirm("Discard unsaved changes?")) return;
                  setFiles((fs) => fs.filter((x) => x.path !== f.path));
                  if (active === f.path) setActive(files.find((x) => x.path !== f.path)?.path ?? null);
                }}><X size={12} /></button>
              </div>
            ))}
          </div>
          <div className="min-h-0 flex-1">
            {activeFile ? (
              <Editor
                path={activeFile.path}
                language={langOf(activeFile.path)}
                value={activeFile.content}
                theme="vs-dark"
                onMount={onMount}
                onChange={(v) => setFiles((fs) => fs.map((x) => (x.path === activeFile.path ? { ...x, content: v ?? "" } : x)))}
                options={{ fontSize: 13, minimap: { enabled: false }, scrollBeyondLastLine: false, tabSize: 4, automaticLayout: true,
                           fontFamily: "Cascadia Code, Consolas, monospace", renderWhitespace: "selection" }}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted">Open a file from the explorer.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
