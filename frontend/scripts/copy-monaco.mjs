// Serve Monaco from our own origin so the editor works offline (no CDN).
import { cpSync, existsSync, rmSync } from "node:fs";
const src = "node_modules/monaco-editor/min/vs";
const dst = "public/monaco/vs";
if (existsSync(src)) {
  rmSync(dst, { recursive: true, force: true });
  cpSync(src, dst, { recursive: true });
  console.log("monaco copied to", dst);
}
