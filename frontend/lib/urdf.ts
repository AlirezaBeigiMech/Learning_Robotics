// Minimal URDF model + forward kinematics for the browser viewer.
// Convention (same as robot_state_publisher): rpy = fixed-axis roll(X), pitch(Y), yaw(Z) => R = Rz*Ry*Rx.
import * as THREE from "three";

export interface Geometry {
  type: "box" | "cylinder" | "sphere" | "mesh";
  size?: [number, number, number];
  radius?: number;
  length?: number;
  filename?: string;
}
export interface Shape { origin: THREE.Matrix4; xyz: number[]; rpy: number[]; geometry: Geometry; color?: string }
export interface Inertial { mass: number; xyz: number[]; rpy: number[]; ixx: number; iyy: number; izz: number; ixy: number; ixz: number; iyz: number }
export interface Link { name: string; visuals: Shape[]; collisions: Shape[]; inertial?: Inertial }
export interface Joint {
  name: string; type: string; parent: string; child: string; xyz: number[]; rpy: number[]; origin: THREE.Matrix4;
  axis: number[]; limit?: { lower: number; upper: number; effort: number; velocity: number };
  mimic?: { joint: string; multiplier: number; offset: number };
}
export interface RobotModel {
  name: string; links: Map<string, Link>; joints: Joint[]; roots: string[];
  parentJoint: Map<string, Joint>; childJoints: Map<string, Joint[]>;
}

const nums = (s: string | null | undefined, n: number, dflt = 0): number[] => {
  const v = (s ?? "").trim().split(/\s+/).filter(Boolean).map(Number);
  return Array.from({ length: n }, (_, i) => (Number.isFinite(v[i]) ? v[i] : dflt));
};

export function originMatrix(xyz: number[], rpy: number[]): THREE.Matrix4 {
  const m = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rpy[0], rpy[1], rpy[2], "ZYX"));
  m.setPosition(xyz[0], xyz[1], xyz[2]);
  return m;
}

function parseOrigin(el: Element | null) {
  const xyz = nums(el?.getAttribute("xyz"), 3);
  const rpy = nums(el?.getAttribute("rpy"), 3);
  return { xyz, rpy, origin: originMatrix(xyz, rpy) };
}

function rgbaToCss(rgba: string | null): string | undefined {
  if (!rgba) return undefined;
  const [r, g, b] = nums(rgba, 4, 1);
  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}

function parseShape(el: Element, materials: Map<string, string>): Shape | null {
  const g = el.querySelector(":scope > geometry")?.firstElementChild;
  if (!g) return null;
  let geometry: Geometry;
  switch (g.tagName) {
    case "box": geometry = { type: "box", size: nums(g.getAttribute("size"), 3) as [number, number, number] }; break;
    case "cylinder": geometry = { type: "cylinder", radius: Number(g.getAttribute("radius")), length: Number(g.getAttribute("length")) }; break;
    case "sphere": geometry = { type: "sphere", radius: Number(g.getAttribute("radius")) }; break;
    case "mesh": geometry = { type: "mesh", filename: g.getAttribute("filename") ?? "" }; break;
    default: return null;
  }
  const mat = el.querySelector(":scope > material");
  const color = rgbaToCss(mat?.querySelector("color")?.getAttribute("rgba") ?? null) ?? (mat ? materials.get(mat.getAttribute("name") ?? "") : undefined);
  return { ...parseOrigin(el.querySelector(":scope > origin")), geometry, color };
}

export function parseUrdf(xml: string): RobotModel {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  const err = doc.querySelector("parsererror");
  if (err) throw new Error(err.textContent ?? "XML parse error");
  const robot = doc.querySelector("robot");
  if (!robot) throw new Error("No <robot> element");
  const materials = new Map<string, string>();
  robot.querySelectorAll(":scope > material").forEach((m) => {
    const c = rgbaToCss(m.querySelector("color")?.getAttribute("rgba") ?? null);
    if (c) materials.set(m.getAttribute("name") ?? "", c);
  });
  const links = new Map<string, Link>();
  robot.querySelectorAll(":scope > link").forEach((l) => {
    const inertialEl = l.querySelector(":scope > inertial");
    let inertial: Inertial | undefined;
    if (inertialEl) {
      const o = parseOrigin(inertialEl.querySelector("origin"));
      const i = inertialEl.querySelector("inertia");
      const a = (k: string) => Number(i?.getAttribute(k) ?? 0);
      inertial = { mass: Number(inertialEl.querySelector("mass")?.getAttribute("value") ?? 0), xyz: o.xyz, rpy: o.rpy,
                   ixx: a("ixx"), iyy: a("iyy"), izz: a("izz"), ixy: a("ixy"), ixz: a("ixz"), iyz: a("iyz") };
    }
    links.set(l.getAttribute("name") ?? "", {
      name: l.getAttribute("name") ?? "",
      visuals: [...l.querySelectorAll(":scope > visual")].map((v) => parseShape(v, materials)).filter((s): s is Shape => !!s),
      collisions: [...l.querySelectorAll(":scope > collision")].map((v) => parseShape(v, materials)).filter((s): s is Shape => !!s),
      inertial,
    });
  });
  const joints: Joint[] = [...robot.querySelectorAll(":scope > joint")].map((j) => {
    const lim = j.querySelector("limit");
    const mim = j.querySelector("mimic");
    return {
      name: j.getAttribute("name") ?? "", type: j.getAttribute("type") ?? "fixed",
      parent: j.querySelector("parent")?.getAttribute("link") ?? "", child: j.querySelector("child")?.getAttribute("link") ?? "",
      ...parseOrigin(j.querySelector("origin")),
      axis: j.querySelector("axis") ? nums(j.querySelector("axis")!.getAttribute("xyz"), 3) : [1, 0, 0],
      limit: lim ? { lower: Number(lim.getAttribute("lower") ?? 0), upper: Number(lim.getAttribute("upper") ?? 0),
                     effort: Number(lim.getAttribute("effort") ?? 0), velocity: Number(lim.getAttribute("velocity") ?? 0) } : undefined,
      mimic: mim ? { joint: mim.getAttribute("joint") ?? "", multiplier: Number(mim.getAttribute("multiplier") ?? 1),
                     offset: Number(mim.getAttribute("offset") ?? 0) } : undefined,
    };
  });
  const parentJoint = new Map<string, Joint>();
  const childJoints = new Map<string, Joint[]>();
  for (const j of joints) {
    parentJoint.set(j.child, j);
    childJoints.set(j.parent, [...(childJoints.get(j.parent) ?? []), j]);
  }
  const roots = [...links.keys()].filter((n) => !parentJoint.has(n));
  return { name: robot.getAttribute("name") ?? "robot", links, joints, roots, parentJoint, childJoints };
}

export const movableJoints = (m: RobotModel) => m.joints.filter((j) => j.type !== "fixed" && j.type !== "floating" && j.type !== "planar");

export function jointRange(j: Joint): [number, number] {
  if (j.type === "continuous" || !j.limit) return [-Math.PI, Math.PI];
  return [j.limit.lower, j.limit.upper];
}

function jointMotion(j: Joint, q: number): THREE.Matrix4 {
  const axis = new THREE.Vector3(...j.axis);
  if (axis.lengthSq() === 0) return new THREE.Matrix4();
  axis.normalize();
  if (j.type === "revolute" || j.type === "continuous") return new THREE.Matrix4().makeRotationAxis(axis, q);
  if (j.type === "prismatic") return new THREE.Matrix4().makeTranslation(axis.x * q, axis.y * q, axis.z * q);
  return new THREE.Matrix4();
}

/** Pose of every link relative to the first root, computed from joint values (mimic joints resolved). */
export function forwardKinematics(m: RobotModel, q: Record<string, number>): Map<string, THREE.Matrix4> {
  const poses = new Map<string, THREE.Matrix4>();
  const value = (j: Joint) => (j.mimic ? (q[j.mimic.joint] ?? 0) * j.mimic.multiplier + j.mimic.offset : q[j.name] ?? 0);
  const visit = (link: string, pose: THREE.Matrix4, depth: number) => {
    poses.set(link, pose);
    if (depth > 200) return;
    for (const j of m.childJoints.get(link) ?? []) {
      visit(j.child, pose.clone().multiply(j.origin).multiply(jointMotion(j, value(j))), depth + 1);
    }
  };
  for (const r of m.roots) visit(r, new THREE.Matrix4(), 0);
  return poses;
}

export interface TfFrame { child: string; parent: string; static: boolean; t: number[]; q: number[]; age: number; rate: number | null; parents: string[] }

/** Pose of each link in `fixed` from live TF (as RViz does). Links without a TF path are absent. */
export function posesFromTf(frames: TfFrame[], links: string[], fixed: string): Map<string, THREE.Matrix4> {
  const byChild = new Map(frames.map((f) => [f.child, f]));
  const cache = new Map<string, THREE.Matrix4 | null>();
  const pose = (frame: string, depth = 0): THREE.Matrix4 | null => {
    if (frame === fixed) return new THREE.Matrix4();
    if (cache.has(frame)) return cache.get(frame)!;
    const f = byChild.get(frame);
    let result: THREE.Matrix4 | null = null;
    if (f && depth < 100) {
      const parent = pose(f.parent, depth + 1);
      if (parent) {
        const local = new THREE.Matrix4().compose(new THREE.Vector3(...f.t), new THREE.Quaternion(...f.q), new THREE.Vector3(1, 1, 1));
        result = parent.clone().multiply(local);
      }
    }
    cache.set(frame, result);
    return result;
  };
  const out = new Map<string, THREE.Matrix4>();
  for (const l of links) {
    const p = pose(l);
    if (p) out.set(l, p);
  }
  return out;
}
