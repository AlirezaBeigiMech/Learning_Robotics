"use client";

import clsx from "clsx";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { AlertTriangle, Radio, X } from "lucide-react";
import { api } from "@/lib/api";
import { useLesson } from "@/lib/lesson";
import { useRuntime } from "@/lib/runtime";
import { forwardKinematics, jointRange, movableJoints, parseUrdf, posesFromTf, RobotModel } from "@/lib/urdf";
import { Badge, Empty } from "../ui";
import { RobotScene, SceneOptions } from "./RobotScene";

interface Preview {
  ok: boolean; urdf?: string; error?: string;
  diagnostics?: { severity: string; message: string }[];
  summary?: { name: string; links: number; joints: number; movable: number; roots: string[] };
}

const isRobotFile = (p: string) => /\.(urdf|xacro)$/.test(p);
const fmt = (v: number, d = 3) => (Math.abs(v) < 5e-4 && d >= 3 ? "0" : v.toFixed(d));
const deg = (r: number) => `${((r * 180) / Math.PI).toFixed(1)}°`;

export function RobotViewer() {
  const { lesson, editorFile } = useLesson();
  const { robotDescription, tf, jointStates, jointGuiEnabled, send, connected, simClock } = useRuntime();
  const [source, setSource] = useState<"preview" | "live">("preview");
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [lastGood, setLastGood] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState<Record<string, number>>({});
  const [opts, setOpts] = useState<SceneOptions>({ visual: true, collision: false, frames: false });
  const [selected, setSelected] = useState<string | null>(null);
  const posesRef = useRef<Map<string, THREE.Matrix4>>(new Map());
  const trailRef = useRef<THREE.Vector3[]>([]);
  const [fixedFrame, setFixedFrame] = useState<string>("auto");
  const sendTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // the agent watches /robot_description, /tf, /tf_static and /joint_states while this view is used
  useEffect(() => { if (connected) send({ cmd: "robot_watch", enable: true }); }, [connected, send]);

  // which file to preview: the robot file open in the editor, else the lesson package's main model
  useEffect(() => {
    if (editorFile && isRobotFile(editorFile.path)) { setPreviewPath(editorFile.path); return; }
    if (previewPath || !lesson) return;
    api<{ entries: { path: string; type: string }[] }>("/api/workspace/tree").then((t) => {
      const pkg = lesson.workspace.package;
      const models = t.entries.filter((e) => e.type === "file" && e.path.startsWith(`${pkg}/urdf/`) && /\.urdf(\.xacro)?$/.test(e.path));
      if (models[0]) setPreviewPath(models[0].path);
    });
  }, [editorFile, lesson, previewPath]);

  // expand with the real xacro tool (unsaved editor content included), debounced
  const liveContent = editorFile && editorFile.path === previewPath ? editorFile.content : undefined;
  useEffect(() => {
    if (!previewPath || source !== "preview") return;
    const t = setTimeout(async () => {
      setBusy(true);
      try {
        const r = await api<Preview>("/api/robot/preview", { body: { path: previewPath, content: liveContent } });
        setPreview(r);
        if (r.ok && r.urdf && (r.summary?.links ?? 0) > 0) setLastGood(r.urdf);
      } catch (e: any) {
        setPreview({ ok: false, error: e.message });
      } finally {
        setBusy(false);
      }
    }, 500);
    return () => clearTimeout(t);
  }, [previewPath, liveContent, source]);

  const model: RobotModel | null = useMemo(() => {
    const xml = source === "live" ? robotDescription?.urdf : lastGood;
    if (!xml) return null;
    try { return parseUrdf(xml); } catch { return null; }
  }, [source, robotDescription?.urdf, lastGood]);

  const joints = useMemo(() => (model ? movableJoints(model).filter((j) => !j.mimic) : []), [model]);

  // Live fixed frame, like RViz's: "odom" (or "map") when it exists, so a mobile robot moves across the grid
  const tfFrames = useMemo(() => new Set((tf?.frames ?? []).flatMap((f) => [f.child, f.parent])), [tf]);
  const frameChoices = useMemo(() => {
    const c = ["map", "odom", "world"].filter((f) => tfFrames.has(f));
    if (model && !c.includes(model.roots[0])) c.push(model.roots[0]);
    return c;
  }, [tfFrames, model]);
  const fixed = fixedFrame !== "auto" && frameChoices.includes(fixedFrame) ? fixedFrame
    : frameChoices.find((f) => f === "map" || f === "odom") ?? model?.roots[0] ?? "";

  // poses: forward kinematics of the file (preview) or live TF (what ROS publishes)
  const missingTf = useMemo(() => {
    if (!model) { posesRef.current = new Map(); return []; }
    const links = [...model.links.keys()];
    if (source === "preview") {
      posesRef.current = forwardKinematics(model, q);
      trailRef.current = [];
      return [];
    }
    posesRef.current = posesFromTf(tf?.frames ?? [], links, fixed);
    // trajectory trail of the robot's root link in the fixed frame
    const root = posesRef.current.get(model.roots[0]);
    if (root) {
      const p = new THREE.Vector3().setFromMatrixPosition(root);
      const last = trailRef.current[trailRef.current.length - 1];
      if (!last || last.distanceTo(p) > 0.01) trailRef.current = [...trailRef.current.slice(-800), p];
    }
    return links.filter((l) => !posesRef.current.has(l));
  }, [model, source, q, tf, fixed]);
  useEffect(() => { trailRef.current = []; }, [fixed, source, model?.name]);
  const simAlive = simClock && Date.now() - simClock.receivedAt < 3000;

  // re-frame when a different model appears, and once more when every link finally has a pose (Live: TF arrives late)
  const fitKey = model ? `${source}:${model.name}:${model.links.size}:${missingTf.length === 0}` : "none";

  const setJoint = (name: string, v: number) => {
    const next = { ...q, [name]: v };
    setQ(next);
    if (source === "live" && jointGuiEnabled) {
      if (sendTimer.current) clearTimeout(sendTimer.current);
      sendTimer.current = setTimeout(() => send({ cmd: "joint_gui", enable: true, positions: next }), 60);
    }
  };

  const togglePublish = () => {
    if (jointGuiEnabled) { send({ cmd: "joint_gui", enable: false }); return; }
    const init: Record<string, number> = {};
    for (const j of joints) init[j.name] = jointStates?.positions[j.name] ?? q[j.name] ?? 0;
    setQ(init);
    send({ cmd: "joint_gui", enable: true, positions: init });
  };

  const sel = selected && model ? model.links.get(selected) : null;
  const selJoint = selected && model ? model.parentJoint.get(selected) : null;
  const selPose = selected ? posesRef.current.get(selected) : null;
  const othersPublishing = (jointStates?.publishers ?? []).filter((p) => p !== "/academy_joint_gui");
  // A real driver (Gazebo's joint_state_broadcaster, hardware, joint_state_publisher) owns /joint_states: two
  // publishers make TF flicker between real and slider values, so the slider publisher steps aside.
  const othersKey = othersPublishing.join(",");
  useEffect(() => {
    if (jointGuiEnabled && othersKey) send({ cmd: "joint_gui", enable: false });
  }, [jointGuiEnabled, othersKey, send]);
  const errors = (preview?.diagnostics ?? []).filter((d) => d.severity === "error");
  const warnings = (preview?.diagnostics ?? []).filter((d) => d.severity !== "error");

  return (
    <div className="flex h-full flex-col">
      {/* source + display options */}
      <div className="flex h-9 shrink-0 items-center gap-2 border-b border-line px-2 text-xs">
        <div className="flex overflow-hidden rounded border border-line">
          {(["preview", "live"] as const).map((s) => (
            <button key={s} onClick={() => setSource(s)}
              className={clsx("px-2 py-1", source === s ? "bg-accent text-white" : "text-ink2 hover:bg-panel2")}>
              {s === "preview" ? "Preview (file)" : "Live (ROS)"}
            </button>
          ))}
        </div>
        <span className="truncate text-[11px] text-muted" title={source === "preview" ? previewPath ?? "" : ""}>
          {source === "preview" ? `${previewPath ?? "no model file"}${busy ? " · xacro…" : ""}` : "/robot_description + TF"}
        </span>
        <span className="flex-1" />
        {source === "live" && frameChoices.length > 1 && (
          <label className="flex items-center gap-1 text-ink2" title="Fixed frame: the frame everything is drawn in (as in RViz)">
            frame
            <select value={fixedFrame} onChange={(e) => setFixedFrame(e.target.value)}
              className="rounded border border-line bg-bg px-1 py-0.5 font-mono text-[11px]">
              <option value="auto">auto ({fixed})</option>
              {frameChoices.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>
        )}
        {(["visual", "collision", "frames"] as const).map((k) => (
          <label key={k} className="flex items-center gap-1 text-ink2">
            <input type="checkbox" checked={opts[k]} onChange={(e) => setOpts({ ...opts, [k]: e.target.checked })} />{k}
          </label>
        ))}
      </div>

      {/* status banners: never pretend */}
      {source === "preview" && preview && !preview.ok && (
        <div className="max-h-24 shrink-0 overflow-auto border-b border-[#5a2a2a] bg-[#2b1a1a] px-3 py-1.5 font-mono text-[11px] text-bad">
          {preview.error}{lastGood && <span className="text-muted"> — showing the last valid model</span>}
        </div>
      )}
      {source === "preview" && preview?.ok && (errors.length > 0 || warnings.length > 0) && (
        <details className="shrink-0 border-b border-line bg-[#1d180c] px-3 py-1 text-[11px]">
          <summary className={clsx("cursor-pointer", errors.length ? "text-bad" : "text-warn")}>
            <AlertTriangle size={11} className="mr-1 inline" />{errors.length} error(s), {warnings.length} warning(s) in the model
          </summary>
          {[...errors, ...warnings].map((d, i) => (
            <div key={i} className={d.severity === "error" ? "text-bad" : "text-warn"}>• {d.message}</div>
          ))}
        </details>
      )}
      {source === "live" && !robotDescription && (
        <div className="shrink-0 border-b border-line bg-[#111a26] px-3 py-1.5 text-[11px] text-ink2">
          Nothing is publishing <code>/robot_description</code> yet. Build, then run your package&apos;s <code>display.launch.py</code>.
        </div>
      )}
      {source === "live" && model && missingTf.length > 0 && (
        <div className="shrink-0 border-b border-line bg-[#1d180c] px-3 py-1.5 text-[11px] text-warn">
          No TF for {missingTf.length} link(s): {missingTf.slice(0, 6).join(", ")}{missingTf.length > 6 ? "…" : ""}. Moving joints need values on
          <code> /joint_states</code>{jointGuiEnabled ? "." : " — enable “Publish /joint_states”."}
        </div>
      )}

      <div className="relative min-h-0 flex-1">
        {model ? (
          <RobotScene model={model} posesRef={posesRef} trailRef={trailRef} options={opts} selected={selected} onPick={setSelected} fitKey={fitKey} />
        ) : (
          <Empty title={source === "live" ? "No live robot" : "No model to preview"}>
            {source === "live" ? "The live view shows exactly what robot_state_publisher publishes." : "Open a .urdf or .xacro file in the editor."}
          </Empty>
        )}
        {model && (
          <div className="pointer-events-none absolute left-2 top-2 rounded bg-black/50 px-2 py-1 text-[10.5px] text-ink2">
            {source === "preview" ? "Preview: your file, kinematics computed in the browser" : `Live: links placed from TF in "${fixed}", like RViz`} ·{" "}
            {model.name}: {model.links.size} links, {model.joints.length} joints
            {source === "live" && simAlive && (
              <div className="mt-0.5 text-good">Simulated time (/clock) · sim time {simClock!.simTime.toFixed(1)} s · RTF {simClock!.rtf?.toFixed(2) ?? "…"}</div>
            )}
          </div>
        )}
        {sel && (
          <div className="absolute right-2 top-2 max-h-[85%] w-72 overflow-auto rounded-md border border-line bg-panel/95 p-2.5 text-[11.5px] shadow-xl">
            <button className="float-right text-muted hover:text-ink" onClick={() => setSelected(null)}><X size={13} /></button>
            <div className="font-mono text-[13px]">{sel.name}</div>
            {selPose && (() => {
              const p = new THREE.Vector3().setFromMatrixPosition(selPose);
              const e = new THREE.Euler().setFromRotationMatrix(selPose, "ZYX");
              return <div className="mt-1 text-muted">pose in {model!.roots[0]}: xyz ({fmt(p.x)}, {fmt(p.y)}, {fmt(p.z)}) rpy ({deg(e.x)}, {deg(e.y)}, {deg(e.z)})</div>;
            })()}
            {selJoint && (
              <div className="mt-2">
                <div className="font-semibold text-ink2">parent joint <span className="font-mono">{selJoint.name}</span></div>
                <div>{selJoint.type}: {selJoint.parent} → {selJoint.child}</div>
                <div>origin xyz ({selJoint.xyz.map((v) => fmt(v)).join(", ")}) rpy ({selJoint.rpy.map((v) => fmt(v)).join(", ")})</div>
                {selJoint.type !== "fixed" && <div>axis ({selJoint.axis.join(", ")})</div>}
                {selJoint.limit && selJoint.type !== "continuous" && selJoint.type !== "fixed" && (
                  <div>limits [{selJoint.limit.lower}, {selJoint.limit.upper}] effort {selJoint.limit.effort} velocity {selJoint.limit.velocity}</div>
                )}
                {selJoint.mimic && <div className="text-warn">mimics {selJoint.mimic.joint} ×{selJoint.mimic.multiplier}</div>}
              </div>
            )}
            {[["visual", sel.visuals], ["collision", sel.collisions]].map(([label, shapes]: any) => (
              <div key={label} className="mt-2">
                <div className="font-semibold text-ink2">{label}</div>
                {shapes.length === 0 ? <div className="text-muted">none</div> : shapes.map((s: any, i: number) => (
                  <div key={i}>
                    {s.geometry.type}{" "}
                    {s.geometry.size ? s.geometry.size.join(" × ") : s.geometry.type === "cylinder" ? `r ${s.geometry.radius}, length ${s.geometry.length}`
                      : s.geometry.radius ? `r ${s.geometry.radius}` : s.geometry.filename}
                    <span className="text-muted"> @ ({s.xyz.map((v: number) => fmt(v)).join(", ")})</span>
                    {s.geometry.type === "mesh" && <span className="text-warn"> (meshes not drawn yet)</span>}
                  </div>
                ))}
              </div>
            ))}
            <div className="mt-2">
              <div className="font-semibold text-ink2">inertial</div>
              {sel.inertial ? (
                <>
                  <div>mass {sel.inertial.mass} kg @ ({sel.inertial.xyz.map((v) => fmt(v)).join(", ")})</div>
                  <div className="font-mono text-[10.5px]">ixx {sel.inertial.ixx.toExponential(3)} iyy {sel.inertial.iyy.toExponential(3)} izz {sel.inertial.izz.toExponential(3)}</div>
                </>
              ) : <div className="text-muted">none</div>}
            </div>
          </div>
        )}
      </div>

      {/* joints */}
      {model && joints.length > 0 && (
        <div className="max-h-[38%] shrink-0 overflow-y-auto border-t border-line px-3 py-2">
          <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
            <span className="font-semibold text-ink2">Joints</span>
            {source === "live" && (
              <button onClick={togglePublish}
                className={clsx("flex items-center gap-1 rounded border px-2 py-0.5", jointGuiEnabled ? "border-good text-good" : "border-line text-ink2 hover:bg-panel2")}>
                <Radio size={11} /> {jointGuiEnabled ? "Publishing /joint_states (/academy_joint_gui)" : "Publish /joint_states"}
              </button>
            )}
            {source === "live" && othersPublishing.length > 0 && <Badge tone="warn">also published by {othersPublishing.join(", ")}</Badge>}
            {source === "preview" && <span className="text-[11px] text-muted">sliders move the preview only</span>}
          </div>
          {joints.map((j) => {
            const [lo, hi] = jointRange(j);
            const live = jointStates?.positions[j.name];
            const value = source === "live" && !jointGuiEnabled ? live ?? 0 : q[j.name] ?? 0;
            const disabled = source === "live" && !jointGuiEnabled;
            return (
              <div key={j.name} className="flex items-center gap-2 py-0.5 text-[11.5px]">
                <span className="w-40 truncate font-mono" title={`${j.type}, axis ${j.axis.join(" ")}`}>{j.name}</span>
                <input type="range" min={lo} max={hi} step="any" value={value} disabled={disabled}
                  onChange={(e) => setJoint(j.name, Number(e.target.value))} className="min-w-0 flex-1 accent-[#3987e5]" />
                <span className="w-16 text-right font-mono text-ink2">{j.type === "prismatic" ? `${(value * 1000).toFixed(0)} mm` : deg(value)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
