"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { Maximize2, Minimize2 } from "lucide-react";
import { useLesson, LabTab } from "@/lib/lesson";
import { useRuntime } from "@/lib/runtime";
import { CoursePanel } from "@/components/lesson/CoursePanel";
import { CodeWorkspace } from "@/components/editor/CodeWorkspace";
import { OutputPanel } from "@/components/editor/OutputPanel";
import { RosGraph } from "@/components/lab/RosGraph";
import { TopicInspector } from "@/components/lab/TopicInspector";
import { TerminalView } from "@/components/lab/TerminalView";
import { TestResults } from "@/components/lab/TestResults";
import { RobotViewer } from "@/components/lab/RobotViewer";
import { TfTree } from "@/components/lab/TfTree";
import { ControllerMonitor } from "@/components/lab/ControllerMonitor";
import { Tabs } from "@/components/ui";

const TAB_LABEL: Record<string, string> = { robot: "Robot", controllers: "Controllers", tf: "TF Tree", graph: "ROS Graph", topics: "Topic Inspector", terminal: "Terminal", tests: "Test Results" };

function LessonView() {
  const id = useSearchParams().get("id") ?? "";
  const { lesson, load, labTab, setLabTab } = useLesson();
  const { connect, connected } = useRuntime();
  const [error, setError] = useState("");
  const [maxed, setMaxed] = useState<"editor" | "lab" | null>(null);

  useEffect(() => {
    connect();
    load(id).catch((e) => setError(e.message));
  }, [id, load, connect]);

  if (error) return <div className="p-8 text-bad">{error}</div>;
  if (!lesson) return <div className="p-8 text-muted">Opening lesson and preparing your workspace…</div>;

  const tabs = lesson.lab_tabs.filter((t) => t in TAB_LABEL).map((t) => ({ id: t as LabTab, label: TAB_LABEL[t] }));
  const lab = (
    <div className="flex h-full flex-col bg-bg">
      <Tabs tabs={tabs} value={labTab} onChange={setLabTab} right={
        <>
          <span className={connected ? "text-[11px] text-good" : "text-[11px] text-warn"}>{connected ? "● live" : "○ offline"}</span>
          <button className="p-1 text-muted hover:text-ink" title={maxed === "lab" ? "Restore" : "Maximize"} onClick={() => setMaxed(maxed === "lab" ? null : "lab")}>
            {maxed === "lab" ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        </>
      } />
      <div className="min-h-0 flex-1">
        {/* the terminal stays mounted so its session survives tab switches */}
        <div className={labTab === "terminal" ? "h-full" : "hidden"}>{lesson.lab_tabs.includes("terminal") && <TerminalView />}</div>
        {/* the robot viewer stays mounted so its 3D scene and slider state survive tab switches */}
        <div className={labTab === "robot" ? "h-full" : "hidden"}>{lesson.lab_tabs.includes("robot") && <RobotViewer />}</div>
        {labTab === "tf" && <TfTree />}
        {labTab === "controllers" && <ControllerMonitor />}
        {labTab === "graph" && <RosGraph />}
        {labTab === "topics" && <TopicInspector />}
        {labTab === "tests" && <TestResults />}
      </div>
    </div>
  );
  const editor = (
    <div className="relative h-full">
      <PanelGroup direction="vertical" autoSaveId="academy-center">
        <Panel defaultSize={68} minSize={25}><CodeWorkspace /></Panel>
        <PanelResizeHandle className="h-1" />
        <Panel defaultSize={32} minSize={10}><OutputPanel /></Panel>
      </PanelGroup>
      <button className="absolute right-2 top-[46px] z-10 rounded p-1 text-muted hover:bg-panel2 hover:text-ink" title={maxed === "editor" ? "Restore" : "Maximize editor"}
        onClick={() => setMaxed(maxed === "editor" ? null : "editor")}>
        {maxed === "editor" ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
      </button>
    </div>
  );

  return (
    <div className="h-screen w-screen overflow-hidden">
      {maxed === "editor" ? editor : maxed === "lab" ? lab : (
        <PanelGroup direction="horizontal" autoSaveId="academy-main">
          <Panel defaultSize={24} minSize={16}><CoursePanel /></Panel>
          <PanelResizeHandle className="w-1" />
          <Panel defaultSize={44} minSize={25}>{editor}</Panel>
          <PanelResizeHandle className="w-1" />
          <Panel defaultSize={32} minSize={18}>{lab}</Panel>
        </PanelGroup>
      )}
    </div>
  );
}

export default function LessonPage() {
  return (
    <Suspense fallback={<div className="p-8 text-muted">Loading…</div>}>
      <LessonView />
    </Suspense>
  );
}
