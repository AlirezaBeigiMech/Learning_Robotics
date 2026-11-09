// Browser walkthrough of Chapter 5 (headless Edge): the Lua bridge in the editor and CoppeliaSim's live log, then
// Webots driven by the C++ driver and go_to_goal, seen in the Robot tab.
// Usage: node scripts/ui-smoke-ch05.mjs [baseUrl] [outDir]
import { chromium } from "playwright-core";
import { mkdirSync, readFileSync } from "node:fs";

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
const OUT = process.argv[3] ?? "ui-smoke-ch05";
mkdirSync(OUT, { recursive: true });
const LESSONS = new URL("../../courses/mastering_ros2/chapter_27/lessons/", import.meta.url);
const H = { "X-Academy-Client": "1" };

const browser = await chromium.launch({ channel: "msedge", headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } });
const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("pageerror", (e) => errors.push(String(e)));
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });
const step = (s) => console.log("•", s);

async function prepare(lesson, pkg, rels) {
  await page.request.post(`${BASE}/api/workspace/lessons/${lesson}/open`, { headers: H, data: { level: "guided" } });
  await page.request.post(`${BASE}/api/workspace/lessons/${lesson}/reset`, { headers: H, data: { level: "guided" } });
  for (const rel of rels) {
    const content = readFileSync(new URL(`${lesson}/solution/${pkg}/${rel}`, LESSONS), "utf8");
    await page.request.put(`${BASE}/api/workspace/file`, { headers: H, data: { path: `${pkg}/${rel}`, content } });
  }
}

// ---- CoppeliaSim: Lua in the editor, live log
await prepare("ch05_coppeliasim", "diffbot_coppelia", ["coppeliasim/diffbot_bridge.lua"]);
await page.goto(`${BASE}/lesson?id=ch05_coppeliasim`);
await page.getByText("● live").waitFor({ timeout: 30000 });
if (await page.getByText("Not installed on this computer").count()) throw new Error("CoppeliaSim reported missing");
await page.getByRole("button", { name: /From \/cmd_vel to the wheels/ }).click();
await page.getByText("Open diffbot_coppelia/coppeliasim/diffbot_bridge.lua").click();
await page.locator(".monaco-editor .view-line", { hasText: "simROS2 = require" }).first().waitFor({ timeout: 20000 });
await page.waitForTimeout(800);
await shot("1-lua-bridge");
step("chapter 5 lesson 1 open, Lua bridge in the editor");

await page.getByRole("button", { name: "Build", exact: true }).click();
await page.getByText(/Build succeeded/).waitFor({ timeout: 300000 });
await page.getByRole("button", { name: /^Run/ }).click();
await page.getByText("ros2 launch diffbot_coppelia sim.launch.xml").click();
await page.getByText("diffbot bridge ready", { exact: false }).first().waitFor({ timeout: 90000 });
await page.waitForTimeout(1500);
await shot("2-coppeliasim-log");
step("CoppeliaSim started headless; its log streams into the output panel");
await page.getByRole("button", { name: /^Stop/ }).click();
await page.waitForTimeout(3000);

// ---- Webots: driver + go_to_goal, Robot tab
await prepare("ch05_webots", "diffbot_webots", ["src/webots_driver.cpp", "src/go_to_goal.cpp"]);
await page.goto(`${BASE}/lesson?id=ch05_webots`);
await page.getByText("● live").waitFor({ timeout: 30000 });
await page.getByRole("button", { name: "Build", exact: true }).click();
await page.getByText(/Build succeeded/).waitFor({ timeout: 300000 });
step("C++ Webots driver built against the Webots C API");
await page.getByRole("button", { name: /^Run/ }).click();
await page.getByText("ros2 launch diffbot_webots sim.launch.xml").click();
await page.getByRole("button", { name: "Robot", exact: true }).click();
await page.getByRole("button", { name: "Live (ROS)" }).click();
await page.getByText(/Simulated time \(\/clock\)/).waitFor({ timeout: 90000 });
await page.waitForTimeout(2000);
await shot("3-webots-live");
step("Webots running; Robot tab live with simulated time");
await page.getByRole("button", { name: /^Run/ }).click();
await page.getByText("ros2 run diffbot_webots go_to_goal").click();
await page.getByText("Goal reached", { exact: false }).first().waitFor({ timeout: 90000 });
await page.waitForTimeout(2000);
await shot("4-webots-goal");
const status = await page.getByText(/Simulated time \(\/clock\)/).innerText();
step(`go_to_goal reached its goal in Webots; ${status}`);
await page.getByRole("button", { name: /^Stop/ }).click();
console.log(errors.length ? `console errors:\n  ${errors.join("\n  ")}` : "no console errors");
await browser.close();
