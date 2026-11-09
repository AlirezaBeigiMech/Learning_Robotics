// Browser walkthrough of Chapter 3 (headless Edge): live xacro preview, 3D viewer, launch, sliders → TF.
// Usage: node scripts/ui-smoke-ch03.mjs [baseUrl] [outDir]
import { chromium } from "playwright-core";
import { mkdirSync, readFileSync } from "node:fs";

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
const OUT = process.argv[3] ?? "ui-smoke-ch03";
mkdirSync(OUT, { recursive: true });
const SOLUTION = readFileSync(new URL("../../courses/mastering_ros2/chapter_03/lessons/ch03_pan_tilt/solution/pan_tilt_description/urdf/pan_tilt.urdf", import.meta.url), "utf8");

const browser = await chromium.launch({ channel: "msedge", headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } });
const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("pageerror", (e) => errors.push(String(e)));
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });
const step = (s) => console.log("•", s);

await page.goto(`${BASE}/`);
await page.waitForURL("**/dashboard");
// start from the starter files (the single student's current package is backed up by the server)
await page.request.post(`${BASE}/api/workspace/lessons/ch03_pan_tilt/open`, { headers: { "X-Academy-Client": "1" }, data: { level: "guided" } });
await page.request.post(`${BASE}/api/workspace/lessons/ch03_pan_tilt/reset`, { headers: { "X-Academy-Client": "1" }, data: { level: "guided" } });
await page.goto(`${BASE}/lesson?id=ch03_pan_tilt`);
await page.getByText("● live").waitFor({ timeout: 30000 });
step("chapter 3 lesson open");

await page.getByRole("button", { name: /Origins and rotations/ }).click();
await page.getByText("Concept model: Child frame relative to parent").waitFor();
await page.locator("text=Concept model: Child frame").scrollIntoViewIfNeeded();
await shot("1-transform-playground");
step("transform playground widget rendered");

await page.getByRole("button", { name: /Complete the pan-tilt URDF/ }).click();
await page.getByText("Open pan_tilt_description/urdf/pan_tilt.urdf").click();
await page.locator(".monaco-editor").waitFor({ timeout: 30000 });
await page.getByRole("button", { name: "Robot", exact: true }).click();
await page.getByText(/1 links, 1 joints/).waitFor({ timeout: 30000 });
step("preview of the starter (1 link)");
await page.waitForTimeout(800);
await page.evaluate((src) => {
  const m = window.monaco.editor.getModels().find((x) => x.uri.path.endsWith("pan_tilt.urdf"));
  m.setValue(src);
}, SOLUTION);
await page.getByText(/4 links, 3 joints/).waitFor({ timeout: 30000 });
step("preview updated from UNSAVED editor content (4 links)");
await page.waitForTimeout(1200);
await shot("2-preview");
await page.getByLabel("collision").check();
await page.getByLabel("frames").check();
await page.waitForTimeout(800);
await shot("3-preview-collision-frames");
// click the middle of the scene to inspect a link
const canvas = page.locator("canvas").last();
const box = await canvas.boundingBox();
await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.45);
await page.waitForTimeout(600);
await shot("4-inspect");
step("collision/frames toggles + inspection panel");

await page.getByRole("button", { name: "Build", exact: true }).click();
await page.getByText(/Build succeeded/).waitFor({ timeout: 120000 });
await page.getByRole("button", { name: /^Run/ }).click();
await page.getByText("ros2 launch pan_tilt_description display.launch.xml").click();
await page.getByRole("button", { name: "Live (ROS)" }).click();
await page.getByText(/No TF for 3 link/).waitFor({ timeout: 40000 });
step("live: robot_description received; TF missing for moving links (honest banner)");
await page.getByRole("button", { name: "Publish /joint_states" }).click();
await page.getByText(/Publishing \/joint_states/).waitFor({ timeout: 15000 });
const sliders = page.locator('input[type="range"]');
await sliders.nth(0).fill("1.2");
await sliders.nth(1).fill("-0.6");
await page.waitForTimeout(2500);
await shot("5-live-sliders");
const banner = await page.getByText(/No TF for/).count();
step(`live robot placed from TF after publishing joint states (missing-TF banner gone: ${banner === 0})`);

await page.getByRole("button", { name: "TF Tree", exact: true }).click();
await page.getByText(/transforms · 1 root/).waitFor({ timeout: 15000 });
await shot("6-tf-tree");
step("TF tree: single root, dynamic frames with rates");

await page.getByRole("button", { name: "ROS Graph", exact: true }).click();
await page.locator(".react-flow__node").filter({ hasText: "/academy_joint_gui" }).waitFor({ timeout: 20000 });
await page.waitForTimeout(1000);
await shot("7-graph");
step("graph shows /academy_joint_gui → /joint_states → /robot_state_publisher");

await page.getByRole("button", { name: /^Stop/ }).click();
console.log(errors.length ? `console errors:\n  ${errors.join("\n  ")}` : "no console errors");
await browser.close();
