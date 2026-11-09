export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(path, {
    method: opts.method ?? (opts.body !== undefined ? "POST" : "GET"),
    // The header proves the request comes from the academy page itself (the server refuses /api calls
    // without it; a cross-site page cannot add it). It replaces sign-in for this local, single-user app.
    headers: { "X-Academy-Client": "1", ...(opts.body !== undefined ? { "Content-Type": "application/json" } : {}) },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    credentials: "same-origin",
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((d: any) => d.msg).join("; ") : msg;
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json();
}

/** WebSocket URL for a backend path. In `next dev` (port 3000) sockets go straight to the backend on :8000. */
export function wsUrl(path: string): string {
  const { protocol, hostname, port } = window.location;
  const scheme = protocol === "https:" ? "wss" : "ws";
  const host = port === "3000" ? `${hostname}:8000` : window.location.host;
  return `${scheme}://${host}${path}`;
}

// ---- shared types --------------------------------------------------------------------------
export interface QoS { reliability: string; durability: string; history: string | null; depth: number | null }
export interface Endpoint { node: string; type: string; qos: QoS }
export interface QosPair { publisher: string; subscriber: string; compatible: "ok" | "warning" | "error"; reason: string }
export interface GraphTopic {
  name: string; types: string[]; system: boolean; publishers: Endpoint[]; subscribers: Endpoint[];
  qos_pairs: QosPair[]; echo: boolean;
}
export interface NamedType { name: string; type: string; system?: boolean }
export interface GraphNode { name: string; services: NamedType[]; clients: NamedType[]; action_servers: NamedType[]; action_clients: NamedType[] }
export interface Graph { t: number; nodes: GraphNode[]; topics: GraphTopic[] }
export interface ProcInfo {
  id: number; kind: string; label: string; pid: number | null; running: boolean; exit_code: number | null;
  started_at: number; ended_at: number | null; stopped_by_user: boolean;
}
export interface TestResult {
  id: string; title: string; status: "passed" | "failed" | "error" | "skipped"; hidden: boolean;
  expected: string | null; observed: string | null; message: string | null; suggestion: string | null; duration_s: number;
}
export interface Submission {
  id: number; lesson_id: string; checkpoint_id: string; status: "queued" | "running" | "passed" | "failed" | "error";
  score: number | null; created_at: string; finished_at: string | null;
  results: { build?: { ok: boolean; log_tail: string; timed_out?: boolean }; tests?: TestResult[];
             summary?: { passed: number; failed: number; total: number; duration_s?: number; timed_out?: boolean }; error?: string };
}
export interface Step {
  id: string; title: string; kind: string; markdown: string; focus_file: string | null; hint_count: number;
  completion: { type: string; checkpoint?: string; node?: string; publishes?: string; subscribes?: string; topic?: string };
}
export interface Lesson {
  id: string; title: string; description: string; chapter: number; difficulty: string; estimated_minutes: number;
  objectives: string[]; prerequisites: string[]; ros_dependencies: string[]; skills: string[]; lab_tabs: string[];
  workspace: { package: string; uses: string[] }; book_reference: { chapter: number; title?: string; sections: string[] };
  requires: string[]; missing_requirements: { id: string; name: string; url: string; where: string }[];
  steps: Step[]; checkpoints: { id: string; title: string; final: boolean; test_count: number }[];
}
export interface Progress {
  status: string; steps_completed: string[]; hints_used: Record<string, number>; current_step: string | null; level: string;
}
