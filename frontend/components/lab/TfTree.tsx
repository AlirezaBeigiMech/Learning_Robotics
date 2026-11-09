"use client";

import clsx from "clsx";
import { useEffect, useMemo } from "react";
import * as THREE from "three";
import { useRuntime } from "@/lib/runtime";
import type { TfFrame } from "@/lib/urdf";
import { Badge, Empty } from "../ui";

const STALE_S = 2;

/** The live TF tree as published on /tf and /tf_static, with the problems tf2 users actually hit. */
export function TfTree() {
  const { tf, send, connected } = useRuntime();
  useEffect(() => { if (connected) send({ cmd: "robot_watch", enable: true }); }, [connected, send]);

  const { roots, children, byChild, problems } = useMemo(() => {
    const frames = tf?.frames ?? [];
    const byChild = new Map(frames.map((f) => [f.child, f]));
    const children = new Map<string, TfFrame[]>();
    for (const f of frames) children.set(f.parent, [...(children.get(f.parent) ?? []), f]);
    const roots = [...new Set(frames.map((f) => f.parent))].filter((p) => !byChild.has(p)).sort();
    const problems: string[] = [];
    if (roots.length > 1) problems.push(`The tree is split: ${roots.length} roots (${roots.join(", ")}). tf2 cannot transform between them.`);
    for (const f of frames) {
      if (f.parents.length > 1) problems.push(`'${f.child}' has been published with ${f.parents.length} different parents (${f.parents.join(", ")}).`);
    }
    return { roots, children, byChild, problems };
  }, [tf]);

  if (!tf || tf.frames.length === 0) {
    return <Empty title="No TF yet">Run a launch file that starts robot_state_publisher. Fixed joints arrive on /tf_static, moving joints on /tf once /joint_states are published.</Empty>;
  }
  const now = Date.now() / 1000;
  const age = (f: TfFrame) => f.age + (now - tf.t);

  const row = (frame: string, depth: number): React.ReactNode => {
    const f = byChild.get(frame);
    const stale = f && !f.static && age(f) > STALE_S;
    const e = f ? new THREE.Euler().setFromQuaternion(new THREE.Quaternion(...f.q), "ZYX") : null;
    return (
      <div key={frame}>
        <div className={clsx("flex items-baseline gap-2 border-b border-line/50 py-1 pr-2 text-[11.5px]", stale && "text-warn")} style={{ paddingLeft: 8 + depth * 14 }}>
          <span className="font-mono text-ink">{frame}</span>
          {f ? (
            <>
              <Badge tone={f.static ? "neutral" : "accent"}>{f.static ? "static" : f.rate ? `${f.rate} Hz` : "dynamic"}</Badge>
              {stale && <Badge tone="warn">stale {age(f).toFixed(0)} s</Badge>}
              <span className="ml-auto whitespace-nowrap font-mono text-[10.5px] text-muted">
                xyz ({f.t.map((v) => v.toFixed(3)).join(", ")}) rpy ({[e!.x, e!.y, e!.z].map((v) => ((v * 180) / Math.PI).toFixed(1)).join(", ")})°
              </span>
            </>
          ) : <Badge>root</Badge>}
        </div>
        {(children.get(frame) ?? []).sort((a, b) => a.child.localeCompare(b.child)).map((c) => row(c.child, depth + 1))}
      </div>
    );
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-8 shrink-0 items-center gap-3 border-b border-line px-3 text-xs text-muted">
        <span>{tf.frames.length} transforms · {roots.length} root{roots.length === 1 ? "" : "s"}</span>
        <span className="text-[10px]">live from /tf and /tf_static · each row is the child frame expressed in its parent</span>
      </div>
      {problems.length > 0 && (
        <div className="shrink-0 space-y-0.5 border-b border-[#5a2a2a] bg-[#2b1a1a] px-3 py-1.5 text-[11px] text-bad">
          {problems.map((p) => <div key={p}>• {p}</div>)}
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-auto">{roots.map((r) => row(r, 0))}</div>
    </div>
  );
}
