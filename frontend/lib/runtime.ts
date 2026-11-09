"use client";

import { create } from "zustand";
import { Graph, ProcInfo, Submission, wsUrl } from "./api";
import type { TfFrame } from "./urdf";

const MAX_LINES = 2000;
const MAX_POINTS = 300;

export interface EchoState {
  msgType: string;
  rate: number;
  count: number;
  last: unknown[]; // most recent messages (newest first)
  series: { t: number; values: Record<string, number> }[];
}

interface RuntimeState {
  connected: boolean;
  graph: Graph | null;
  processes: Record<number, ProcInfo>;
  output: Record<number, string[]>;
  echo: Record<string, EchoState>;
  submissions: Record<number, Submission>;
  agentErrors: string[];
  // robot model (Chapter 3+): what ROS publishes, observed by the telemetry agent
  robotDescription: { urdf: string; t: number } | null;
  tf: { t: number; frames: TfFrame[] } | null;
  jointStates: { t: number; positions: Record<string, number>; publishers: string[] } | null;
  jointGuiEnabled: boolean;
  // simulation (Chapter 4+)
  simClock: { simTime: number; rtf: number | null; receivedAt: number } | null;
  controllers: { t: number; managers: ControllerManagerState[] } | null;
  connect: () => void;
  send: (msg: object) => void;
  clearOutput: (id: number) => void;
}

export interface ControllerState {
  name: string; type: string; state: string;
  claimed_interfaces: string[]; command_interfaces: string[]; state_interfaces: string[];
}
export interface ControllerManagerState { manager: string; controllers: ControllerState[] }

let socket: WebSocket | null = null;
let retry: ReturnType<typeof setTimeout> | null = null;

export const useRuntime = create<RuntimeState>((set, get) => ({
  connected: false,
  graph: null,
  processes: {},
  output: {},
  echo: {},
  submissions: {},
  agentErrors: [],
  robotDescription: null,
  tf: null,
  jointStates: null,
  jointGuiEnabled: false,
  simClock: null,
  controllers: null,

  connect: () => {
    if (socket && socket.readyState <= 1) return;
    socket = new WebSocket(wsUrl("/ws/runtime"));
    socket.onopen = () => {
      set({ connected: true });
      // re-subscribe to echoes that were open before a reconnect
      Object.keys(get().echo).forEach((topic) => get().send({ cmd: "echo", topic }));
    };
    socket.onclose = () => {
      set({ connected: false });
      if (retry) clearTimeout(retry);
      retry = setTimeout(() => get().connect(), 2000);
    };
    socket.onmessage = (ev) => {
      const e = JSON.parse(ev.data);
      switch (e.type) {
        case "hello": {
          const processes: Record<number, ProcInfo> = {};
          for (const p of e.status.processes as ProcInfo[]) processes[p.id] = p;
          set({ processes, graph: e.graph ?? get().graph });
          break;
        }
        case "graph":
          set({ graph: e });
          break;
        case "proc_state":
          set((s) => ({ processes: { ...s.processes, [e.process.id]: e.process } }));
          break;
        case "proc_output":
          set((s) => {
            const lines = s.output[e.id] ? [...s.output[e.id], e.line] : [e.line];
            return { output: { ...s.output, [e.id]: lines.length > MAX_LINES ? lines.slice(-MAX_LINES) : lines } };
          });
          break;
        case "build_notice":
          set((s) => ({ output: { ...s.output, [-1]: [...(s.output[-1] ?? []), e.line].slice(-MAX_LINES) } }));
          break;
        case "echo_started":
          set((s) => ({ echo: { ...s.echo, [e.topic]: s.echo[e.topic] ?? { msgType: e.msg_type, rate: 0, count: 0, last: [], series: [] } } }));
          break;
        case "echo": {
          set((s) => {
            const prev = s.echo[e.topic] ?? { msgType: e.msg_type, rate: 0, count: 0, last: [], series: [] };
            const series = [...prev.series, { t: e.t, values: e.numeric }];
            return {
              echo: {
                ...s.echo,
                [e.topic]: { msgType: e.msg_type, rate: e.rate, count: e.count, last: [e.data, ...prev.last].slice(0, 20),
                             series: series.length > MAX_POINTS ? series.slice(-MAX_POINTS) : series },
              },
            };
          });
          break;
        }
        case "echo_stats":
          set((s) => (s.echo[e.topic] ? { echo: { ...s.echo, [e.topic]: { ...s.echo[e.topic], rate: e.rate, count: e.count } } } : {}));
          break;
        case "echo_stopped":
          set((s) => {
            const echo = { ...s.echo };
            delete echo[e.topic];
            return { echo };
          });
          break;
        case "submission":
          set((s) => ({ submissions: { ...s.submissions, [e.submission.id]: e.submission } }));
          break;
        case "robot_description":
          set({ robotDescription: { urdf: e.urdf, t: e.t } });
          break;
        case "tf":
          set({ tf: { t: e.t, frames: e.frames } });
          break;
        case "joint_states":
          set({ jointStates: { t: e.t, positions: e.positions, publishers: e.publishers } });
          break;
        case "sim_clock":
          set({ simClock: { simTime: e.sim_time, rtf: e.rtf, receivedAt: Date.now() } });
          break;
        case "controllers":
          set({ controllers: { t: e.t ?? Date.now() / 1000, managers: e.managers } });
          break;
        case "joint_gui_state":
          set({ jointGuiEnabled: e.enabled });
          break;
        case "error":
          set((s) => ({ agentErrors: [...s.agentErrors, e.message].slice(-5) }));
          break;
      }
    };
  },

  send: (msg) => {
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(msg));
  },

  clearOutput: (id) => set((s) => ({ output: { ...s.output, [id]: [] } })),
}));
