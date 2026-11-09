"use client";

import { useEffect, useRef, useState } from "react";
import { wsUrl } from "@/lib/api";

/** A real PowerShell (ConPTY) on this machine with your ROS 2 environment and ROS_DOMAIN_ID. */
export function TerminalView() {
  const host = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"connecting" | "open" | "closed">("connecting");
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let disposed = false;
    let term: any, fit: any, ws: WebSocket, ro: ResizeObserver;
    (async () => {
      const [{ Terminal }, { FitAddon }] = await Promise.all([import("@xterm/xterm"), import("@xterm/addon-fit")]);
      if (disposed || !host.current) return;
      term = new Terminal({ fontFamily: "Cascadia Code, Consolas, monospace", fontSize: 13, cursorBlink: true,
        theme: { background: "#0c0d0f", foreground: "#ecebe8" }, scrollback: 5000 });
      fit = new FitAddon();
      term.loadAddon(fit);
      term.open(host.current);
      fit.fit();
      ws = new WebSocket(wsUrl("/ws/terminal"));
      ws.onopen = () => {
        setState("open");
        ws.send(JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols }));
      };
      ws.onmessage = (ev) => term.write(ev.data);
      ws.onclose = () => setState("closed");
      term.onData((d: string) => ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ type: "input", data: d })));
      ro = new ResizeObserver(() => {
        try {
          fit.fit();
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols }));
        } catch {}
      });
      ro.observe(host.current);
    })();
    return () => { disposed = true; ro?.disconnect(); ws?.close(); term?.dispose(); };
  }, [nonce]);

  return (
    <div className="relative flex h-full flex-col bg-[#0c0d0f]">
      <div ref={host} className="min-h-0 flex-1 p-1" />
      {state === "closed" && (
        <button className="absolute right-3 top-2 rounded border border-line bg-panel2 px-2 py-1 text-xs" onClick={() => { setState("connecting"); setNonce(nonce + 1); }}>
          Reconnect terminal
        </button>
      )}
    </div>
  );
}
