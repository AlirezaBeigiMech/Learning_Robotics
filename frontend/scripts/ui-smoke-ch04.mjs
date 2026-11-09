// Browser walkthrough of Chapter 4 (headless Edge): Gazebo simulation driven from the UI.
// Usage: node scripts/ui-smoke-ch04.mjs [baseUrl] [outDir]
import { chromium } from "playwright-core";
import { mkdirSync, readFileSync } from "node:fs";

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
const OUT = process.argv[3] ?? "ui-smoke-ch04";
mkdirSync(OUT, { recursive: true });
const SOL = new URL("../../courses/mastering_ros2/chapter_04/lessons/ch04_diffbot_gazebo/solution/diffbot_sim/", import.meta.url);
const H = { "X-Academy-Client": "1" };

const browser = await chromium.launch({ channel: "msedge", headless: true, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } });
const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("pageerror", (e) => errors.push(String(e)));
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });
const step = (s) => console.log("•", s);

// start from the starter, then write the reference files through the API (the editor is covered by other walkthroughs)
await page.request.post(`${BASE}/api/workspace/lessons/ch04_diffbot_gazebo/open`, { headers: H, data: { level: "guided" } });
await page.request.post(`${BASE}/api/workspace/lessons/ch04_diffbot_gazebo/reset`, { headers: H, data: { level: "guided" } });
for (const rel of ["urdf/diffbot.ros2_control.xacro", "config/controllers.yaml", "src/drive_forward.cpp"]) {
  await page.request.put(`${BASE}/api/workspace/file`, { headers: H, data: { path: `diffbot_sim/${rel}`, content: readFileSync(new URL(rel, SOL), "utf8") } });
}
await page.goto(`${BASE}/lesson?id=ch04_diffbot_gazebo`);
await page.getByText("● live").waitFor({ timeout: 30000 });
step("chapter 4 lesson open");

await page.getByRole("button", { name: "Build", exact: true }).click();
await page.getByText(/Build succeeded/).waitFor({ timeout: 180000 });
await page.getByRole("button", { name: /^Run/ }).click();
await page.getByText("ros2 launch diffbot_sim sim.launch.xml").click();
await page.getByRole("button", { name: "Controllers", exact: true }).click();
const ctrlRow = page.locator("tr", { has: page.locator("td", { hasText: /^diff_drive_controller$/ }) });
await ctrlRow.waitFor({ timeout: 90000 });
await ctrlRow.getByText("active", { exact: true }).waitFor({ timeout: 60000 });
await page.waitForTimeout(1500);
await shot("1-controllers");
step("controllers tab: controllers active in Gazebo");

await page.getByRole("button", { name: "Robot", exact: true }).click();
await page.getByRole("button", { name: "Live (ROS)" }).click();
await page.getByText(/Simulated time \(\/clock\)/).waitFor({ timeout: 30000 });
await page.waitForTimeout(2000);
await shot("2-sim-start");
step("live view of the simulation (fixed frame odom, sim clock shown)");

await page.getByRole("button", { name: /^Run/ }).click();
await page.getByText("ros2 run diffbot_sim drive_forward").click();
await page.waitForTimeout(12000);
await shot("3-sim-driven");
const status = await page.getByText(/Simulated time \(\/clock\)/).innerText();
step(`robot drove in simulation; status: ${status}`);

await page.getByRole("button", { name: /^Stop/ }).click();
console.log(errors.length ? `console errors:\n  ${errors.join("\n  ")}` : "no console errors");
await browser.close();
