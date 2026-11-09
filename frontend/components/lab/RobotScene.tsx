"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RobotModel, Shape } from "@/lib/urdf";

export interface SceneOptions { visual: boolean; collision: boolean; frames: boolean }

function geometryOf(s: Shape): THREE.BufferGeometry | null {
  const g = s.geometry;
  if (g.type === "box" && g.size) return new THREE.BoxGeometry(...g.size);
  if (g.type === "cylinder" && g.radius && g.length) {
    // three.js cylinders run along Y; URDF cylinders along Z.
    return new THREE.CylinderGeometry(g.radius, g.radius, g.length, 40).rotateX(Math.PI / 2);
  }
  if (g.type === "sphere" && g.radius) return new THREE.SphereGeometry(g.radius, 32, 16);
  return null; // meshes are not rendered in this milestone
}

/**
 * Renders a robot model. Link poses are read every frame from `posesRef` (computed by the caller either
 * from forward kinematics of the file, or from live TF), so the scene never re-creates on joint motion.
 */
export function RobotScene({ model, posesRef, trailRef, options, selected, onPick, fitKey }: {
  model: RobotModel | null;
  posesRef: React.MutableRefObject<Map<string, THREE.Matrix4>>;
  trailRef?: React.MutableRefObject<THREE.Vector3[]>;
  options: SceneOptions;
  selected: string | null;
  onPick: (link: string | null) => void;
  fitKey: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const ctx = useRef<{ renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera;
                       controls: OrbitControls; robot: THREE.Group; links: Map<string, THREE.Group> } | null>(null);
  const pickRef = useRef(onPick);
  pickRef.current = onPick;

  // one renderer for the component's lifetime
  useEffect(() => {
    const el = host.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0x0c0d0f);
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.005, 100);
    camera.up.set(0, 0, 1); // ROS: z up
    camera.position.set(0.9, -0.9, 0.7);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0.2);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x303035, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(2, -3, 4);
    scene.add(sun);
    const grid = new THREE.GridHelper(4, 40, 0x3a3c42, 0x232428);
    grid.rotation.x = Math.PI / 2; // XY ground plane
    scene.add(grid);
    const world = new THREE.AxesHelper(0.12);
    scene.add(world);
    const robot = new THREE.Group();
    scene.add(robot);
    // driven path (Live mode): positions of the robot's root link in the fixed frame
    const trail = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0x3987e5 }));
    trail.frustumCulled = false;
    scene.add(trail);
    let trailLen = -1;
    let followFrom: THREE.Vector3 | null = null;
    let dirty = true; // render on demand (see loop below)
    ctx.current = { renderer, scene, camera, controls, robot, links: new Map() };

    const resize = () => {
      const w = el.clientWidth, h = el.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      dirty = true;
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();

    let down: { x: number; y: number } | null = null;
    const onDown = (e: PointerEvent) => (down = { x: e.clientX, y: e.clientY });
    const onUp = (e: PointerEvent) => {
      if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) return;
      const r = renderer.domElement.getBoundingClientRect();
      const ray = new THREE.Raycaster();
      ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
      const hit = ray.intersectObjects(robot.children, true).find((h) => h.object.visible && h.object.userData.link);
      pickRef.current(hit ? hit.object.userData.link : null);
    };
    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);

    // Render ON DEMAND: only when the camera moved, a pose/trail/model changed or the size changed, and never
    // while the tab is hidden. A continuous 60 fps loop wastes battery on laptops, and with software rendering
    // it starved the C++ compiler (a 25 s build took 3 min while the Robot tab was open).
    let raf = 0;
    let lastPoses: Map<string, THREE.Matrix4> | null = null;
    controls.addEventListener("change", () => { dirty = true; });
    const markDirty = () => { dirty = true; };
    window.addEventListener("academy-scene-dirty", markDirty);
    const loop = () => {
      raf = requestAnimationFrame(loop);
      if (el.clientWidth === 0 || el.clientHeight === 0) return; // hidden tab
      const c = ctx.current!;
      if (posesRef.current !== lastPoses || c.robot.userData.rebuilt) {
        lastPoses = posesRef.current;
        c.robot.userData.rebuilt = false;
        for (const [name, group] of c.links) {
          const pose = posesRef.current.get(name);
          group.visible = !!pose;
          if (pose) group.matrix.copy(pose);
        }
        dirty = true;
      }
      const pts = trailRef?.current ?? [];
      if (pts.length !== trailLen) {
        // follow the driving robot: shift camera and orbit target by the root link's motion, keeping the user's view angle
        const head = pts[pts.length - 1];
        if (head && followFrom && pts.length > trailLen) {
          const d = new THREE.Vector3(head.x - followFrom.x, head.y - followFrom.y, 0);
          c.camera.position.add(d);
          c.controls.target.add(d);
        }
        followFrom = head ? head.clone() : null;
        trailLen = pts.length;
        trail.geometry.setFromPoints(pts.map((p) => new THREE.Vector3(p.x, p.y, 0.002)));
        dirty = true;
      }
      controls.update(); // emits "change" while damping or after user input
      if (!dirty) return;
      dirty = false;
      renderer.render(scene, camera);
    };
    loop();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("academy-scene-dirty", markDirty);
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
      ctx.current = null;
    };
  }, [posesRef, trailRef]);

  // (re)build meshes when the model or display options change
  useEffect(() => {
    const c = ctx.current;
    if (!c) return;
    c.robot.traverse((o) => {
      if (o instanceof THREE.Mesh || o instanceof THREE.LineSegments) {
        o.geometry.dispose();
        (Array.isArray(o.material) ? o.material : [o.material]).forEach((m: THREE.Material) => m.dispose());
      }
    });
    c.robot.clear();
    c.links.clear();
    if (!model) return;
    const box = new THREE.Box3();
    for (const p of posesRef.current.values()) box.expandByPoint(new THREE.Vector3().setFromMatrixPosition(p));
    const size = Math.max(0.2, box.getSize(new THREE.Vector3()).length());
    for (const link of model.links.values()) {
      const group = new THREE.Group();
      group.matrixAutoUpdate = false;
      const isSel = link.name === selected;
      if (options.visual) {
        for (const v of link.visuals) {
          const geo = geometryOf(v);
          if (!geo) continue;
          const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
            color: v.color ?? "#9a9aa0", roughness: 0.6, metalness: 0.1,
            emissive: isSel ? new THREE.Color("#2a5db0") : new THREE.Color(0), transparent: options.collision, opacity: options.collision ? 0.45 : 1,
          }));
          mesh.matrixAutoUpdate = false;
          mesh.matrix.copy(v.origin);
          mesh.userData.link = link.name;
          group.add(mesh);
        }
      }
      if (options.collision) {
        for (const col of link.collisions) {
          const geo = geometryOf(col);
          if (!geo) continue;
          const lines = new THREE.LineSegments(new THREE.WireframeGeometry(geo), new THREE.LineBasicMaterial({ color: isSel ? 0xffc04d : 0xc98500 }));
          lines.matrixAutoUpdate = false;
          lines.matrix.copy(col.origin);
          lines.userData.link = link.name;
          group.add(lines);
          // invisible pick target
          const pick = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ visible: false }));
          pick.matrixAutoUpdate = false;
          pick.matrix.copy(col.origin);
          pick.userData.link = link.name;
          group.add(pick);
        }
      }
      if (options.frames || isSel) {
        const axes = new THREE.AxesHelper(Math.min(0.12, size * 0.08) * (isSel ? 1.6 : 1));
        (axes.material as THREE.Material).depthTest = false;
        axes.renderOrder = 2;
        group.add(axes);
      }
      c.robot.add(group);
      c.links.set(link.name, group);
    }
    c.robot.userData.rebuilt = true;
  }, [model, options.visual, options.collision, options.frames, selected, posesRef]);

  // frame the robot when a different model appears
  useEffect(() => {
    const c = ctx.current;
    if (!c || !model) return;
    const box = new THREE.Box3();
    for (const p of posesRef.current.values()) box.expandByPoint(new THREE.Vector3().setFromMatrixPosition(p));
    if (box.isEmpty()) return;
    const center = box.getCenter(new THREE.Vector3());
    const r = Math.max(0.25, box.getSize(new THREE.Vector3()).length());
    c.controls.target.copy(center);
    c.camera.position.set(center.x + r * 1.3, center.y - r * 1.3, center.z + r * 0.9);
    c.camera.updateProjectionMatrix();
    window.dispatchEvent(new Event("academy-scene-dirty"));
  }, [fitKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={host} className="h-full w-full" />;
}
