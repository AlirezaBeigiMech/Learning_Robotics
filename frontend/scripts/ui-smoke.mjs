// Browser smoke test of the real UI (headless Microsoft Edge via playwright-core).
// Registers a student, opens the pub/sub lesson, edits + builds + runs real code through the UI,
// and screenshots each panel. Usage: node scripts/ui-smoke.mjs [baseUrl] [outDir]
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
const OUT = process.argv[3] ?? "ui-smoke";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } });
const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("pageerror", (e) => errors.push(String(e)));
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });
const step = (s) => console.log("•", s);

// no sign-in: the root URL opens the dashboard directly
await page.goto(`${BASE}/`);
await page.waitForURL("**/dashboard");
if ((await page.getByText(/Sign in|Create account|Sign out/).count()) !== 0) throw new Error("sign-in UI still present");
await page.getByText("Building a ROS 2 Publisher and Subscriber").first().waitFor();
await shot("1-dashboard");
step("dashboard rendered");

await page.getByText("Building a ROS 2 Publisher and Subscriber").first().click();
await page.waitForURL("**/lesson?id=ch02_pubsub");
await page.getByText("Topics, nodes and discovery").first().waitFor();
await page.getByText("● live").waitFor({ timeout: 30000 });
await shot("2-lesson-concept");
step("lesson rendered, runtime socket live");

// open the publisher file via the step's focus link (step 3)
await page.getByRole("button", { name: /Write the publisher/ }).click();
await page.getByText("Open topics_lab/src/number_publisher.cpp").click();
await page.locator(".monaco-editor").waitFor({ timeout: 30000 });
await page.waitForTimeout(1500);
// replace the editor content with a working C++ publisher (typed through Monaco's model)
await page.evaluate(() => {
  const m = window.monaco?.editor.getModels().find((x) => x.uri.path.endsWith("number_publisher.cpp"));
  m.setValue([
    "#include <chrono>", "#include <memory>", '#include "rclcpp/rclcpp.hpp"', '#include "std_msgs/msg/int32.hpp"',
    "using namespace std::chrono_literals;", "",
    "class NumberPublisher : public rclcpp::Node {", "public:",
    '  NumberPublisher() : Node("number_publisher") {',
    '    pub_ = create_publisher<std_msgs::msg::Int32>("numbers", 10);',
    "    timer_ = create_wall_timer(100ms, [this]() { std_msgs::msg::Int32 m; m.data = n_++; pub_->publish(m); });",
    "  }", "private:", "  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr pub_;", "  rclcpp::TimerBase::SharedPtr timer_;",
    "  int n_ = 0;", "};", "",
    "int main(int argc, char ** argv) {", "  rclcpp::init(argc, argv);", "  rclcpp::spin(std::make_shared<NumberPublisher>());",
    "  rclcpp::shutdown();", "  return 0;", "}", "",
  ].join("\n"));
});
await shot("3-editor");
step("monaco loaded (offline bundle) and file edited");

await page.getByRole("button", { name: "Build", exact: true }).click();
await page.getByText(/Build succeeded/).waitFor({ timeout: 120000 });
step("build via UI succeeded");
await page.getByRole("button", { name: /^Run/ }).click();
await page.getByText("ros2 run topics_lab number_publisher").click();
await page.getByRole("button", { name: "ROS Graph", exact: true }).click();
await page.locator(".react-flow__node").filter({ hasText: "/number_publisher" }).waitFor({ timeout: 40000 });
await page.waitForTimeout(1500);
await shot("4-graph");
step("live graph shows /number_publisher");

await page.locator(".react-flow__node").filter({ hasText: "/numbers" }).click();
await page.getByText("measured rate").waitFor();
await page.waitForTimeout(5000);
await shot("5-topic-inspector");
const rate = await page.locator("text=measured rate").locator("..").innerText();
step(`topic inspector: ${rate.replace(/\n/g, " ")}`);

await page.getByRole("button", { name: "Terminal", exact: true }).click();
await page.waitForTimeout(4000);
await page.locator(".xterm-helper-textarea").focus();
await page.keyboard.type("ros2 node list --no-daemon --spin-time 3\r");
await page.waitForTimeout(7000);
await shot("6-terminal");
const termText = await page.locator(".xterm-rows").innerText();
step(`terminal shows node list: ${termText.includes("/number_publisher")}`);

await page.getByRole("button", { name: /Run it and find it in the graph/ }).click();
await page.getByRole("button", { name: /Verify in live graph/ }).click();
await page.getByText("Verified in the live ROS graph.").waitFor({ timeout: 15000 });
step("step verification against live graph");

await page.getByRole("button", { name: /Write the publisher/ }).click();
await page.getByRole("button", { name: /Check: Publisher behaviour/ }).click();
await page.getByText(/passed|failed/, { exact: false }).first().waitFor();
await page.locator("text=/^\\d+\\/4 passed/").waitFor({ timeout: 180000 });
await page.waitForTimeout(500);
await shot("7-test-results");
step(`grader result: ${await page.locator("text=/^\\d+\\/4 passed/").first().innerText()}`);

// hints persist for the single local student, so reveal whichever level is next
const before = await page.getByText(/^Hint \d \/ 5$/).count();
await page.getByRole("button", { name: /^Hint \d$|Show reference solution/ }).click();
await page.waitForFunction((n) => document.body.innerText.match(/Hint \d \/ 5/g)?.length > n, before);
await shot("8-hint");
step("progressive hint revealed");

await page.getByRole("button", { name: /^Stop/ }).click();
console.log(errors.length ? `console errors:\n  ${errors.join("\n  ")}` : "no console errors");
await browser.close();
