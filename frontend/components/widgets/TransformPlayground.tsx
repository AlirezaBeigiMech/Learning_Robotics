"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { originMatrix } from "@/lib/urdf";

const KEYS = ["x", "y", "z", "roll", "pitch", "yaw"] as const;

/** Concept widget: a child frame placed by a URDF <origin>, with its homogeneous matrix. */
export function TransformPlayground({ config }: { config: any }) {
  const host = useRef<HTMLDivElement>(null);
  const child = useRef<THREE.Group | null>(null);
  const dirty = useRef(true); // render on demand, like the robot viewer
  const [v, setV] = useState<Record<(typeof KEYS)[number], number>>({ x: 0.3, y: 0, z: 0.1, roll: 0, pitch: 0, yaw: Math.PI / 4 });
  const m = useMemo(() => originMatrix([v.x, v.y, v.z], [v.roll, v.pitch, v.yaw]), [v]);

  useEffect(() => {
    const el = host.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0x0c0d0f);
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 20);
    camera.up.set(0, 0, 1);
    camera.position.set(0.8, -0.9, 0.6);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0.15, 0, 0.05);
    const grid = new THREE.GridHelper(1.2, 12, 0x3a3c42, 0x232428);
    grid.rotation.x = Math.PI / 2;
    scene.add(grid, new THREE.AxesHelper(0.25));
    const g = new THREE.Group();
    g.matrixAutoUpdate = false;
    g.add(new THREE.AxesHelper(0.18));
    const box = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.04, 0.02), new THREE.MeshBasicMaterial({ color: 0x3987e5, transparent: true, opacity: 0.5 }));
    g.add(box);
    scene.add(g);
    child.current = g;
    const resize = () => {
      const w = el.clientWidth, h = el.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      dirty.current = true;
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    let raf = 0;
    controls.addEventListener("change", () => { dirty.current = true; });
    const loop = () => {
      raf = requestAnimationFrame(loop);
      controls.update();
      if (!dirty.current || el.clientWidth === 0) return;
      dirty.current = false;
      renderer.render(scene, camera);
    };
    loop();
    return () => { cancelAnimationFrame(raf); ro.disconnect(); controls.dispose(); renderer.dispose(); el.removeChild(renderer.domElement); };
  }, []);

  useEffect(() => { child.current?.matrix.copy(m); dirty.current = true; }, [m]);

  const e = m.elements; // column-major
  const rows = [0, 1, 2, 3].map((r) => [0, 1, 2, 3].map((c) => e[c * 4 + r]));
  const f = (n: number) => (Math.abs(n) < 5e-4 ? "0" : n.toFixed(3));

  return (
    <div className="my-3 rounded-lg border border-line bg-[#0f1012] p-3">
      <div className="mb-2 text-[11px] text-muted">Concept model: {config.title ?? "transform"}. Thick axes = parent frame, thin = child (red x, green y, blue z). Drag to orbit.</div>
      <div className="grid gap-3 sm:grid-cols-[1fr_1fr]">
        <div ref={host} className="h-48 overflow-hidden rounded" />
        <div className="space-y-1 text-[11.5px]">
          {KEYS.map((k) => {
            const angle = k === "roll" || k === "pitch" || k === "yaw";
            return (
              <label key={k} className="flex items-center gap-2">
                <span className="w-10 font-mono text-ink2">{k}</span>
                <input type="range" className="min-w-0 flex-1 accent-[#3987e5]" min={angle ? -Math.PI : -0.5} max={angle ? Math.PI : 0.5}
                  step={0.01} value={v[k]} onChange={(ev) => setV({ ...v, [k]: Number(ev.target.value) })} />
                <span className="w-14 text-right font-mono">{angle ? `${((v[k] * 180) / Math.PI).toFixed(0)}°` : `${v[k].toFixed(2)} m`}</span>
              </label>
            );
          })}
        </div>
      </div>
      <div className="mt-2 grid gap-3 sm:grid-cols-[auto_1fr]">
        <table className="font-mono text-[11px]">
          <tbody>{rows.map((r, i) => (
            <tr key={i}>{r.map((x, j) => <td key={j} className={j === 3 && i < 3 ? "px-1.5 text-[#3987e5]" : "px-1.5 text-ink2"}>{f(x)}</td>)}</tr>
          ))}</tbody>
        </table>
        <div className="text-[11px] text-muted">
          <div className="font-mono text-ink">&lt;origin xyz=&quot;{f(v.x)} {f(v.y)} {f(v.z)}&quot; rpy=&quot;{f(v.roll)} {f(v.pitch)} {f(v.yaw)}&quot;/&gt;</div>
          <div className="mt-1">The left 3×3 block is the rotation R = Rz(yaw)·Ry(pitch)·Rx(roll). The right column (blue) is the translation. A point p in
            the child frame is at R·p + t in the parent frame.</div>
        </div>
      </div>
    </div>
  );
}
