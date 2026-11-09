"use client";

import { useMemo, useState } from "react";
import { Background, Controls, Edge, Handle, MarkerType, Node, NodeProps, Position, ReactFlow } from "@xyflow/react";
import { Graph, GraphTopic } from "@/lib/api";
import { useLesson } from "@/lib/lesson";
import { useRuntime } from "@/lib/runtime";
import { Badge, Empty } from "../ui";

function RosNodeBox({ data }: NodeProps) {
  const d = data as { label: string; services: number };
  return (
    <div className="min-w-36 rounded-md border border-[#3a4150] bg-[#1c212b] px-3 py-2 text-center">
      <Handle type="target" position={Position.Left} className="!bg-muted" />
      <div className="font-mono text-[12px] text-ink">{d.label}</div>
      <div className="text-[10px] text-muted">node{d.services ? ` · ${d.services} srv` : ""}</div>
      <Handle type="source" position={Position.Right} className="!bg-muted" />
    </div>
  );
}

function TopicBox({ data }: NodeProps) {
  const d = data as { label: string; type: string; rate?: number };
  return (
    <div className="rounded-full border border-accent bg-[#14243a] px-3 py-1.5 text-center">
      <Handle type="target" position={Position.Left} className="!bg-accent" />
      <div className="font-mono text-[12px] text-ink">{d.label}</div>
      <div className="font-mono text-[9.5px] text-muted">{d.type}{d.rate ? ` · ${d.rate.toFixed(1)} Hz` : ""}</div>
      <Handle type="source" position={Position.Right} className="!bg-accent" />
    </div>
  );
}

const nodeTypes = { ros: RosNodeBox, topic: TopicBox };

/** Layered layout: rank = longest path from a source, alternating node → topic → node. */
function layout(graph: Graph, topics: GraphTopic[]) {
  const succ = new Map<string, string[]>();
  const add = (a: string, b: string) => succ.set(a, [...(succ.get(a) ?? []), b]);
  for (const t of topics) {
    for (const p of t.publishers) add(`n:${p.node}`, `t:${t.name}`);
    for (const s of t.subscribers) add(`t:${t.name}`, `n:${s.node}`);
  }
  const ids = [...graph.nodes.map((n) => `n:${n.name}`), ...topics.map((t) => `t:${t.name}`)];
  const rank = new Map<string, number>(ids.map((i) => [i, 0]));
  for (let iter = 0; iter < ids.length; iter++) {
    let changed = false;
    for (const [a, bs] of succ) for (const b of bs) {
      if ((rank.get(b) ?? 0) < (rank.get(a) ?? 0) + 1 && (rank.get(a) ?? 0) + 1 < ids.length * 2) { rank.set(b, (rank.get(a) ?? 0) + 1); changed = true; }
    }
    if (!changed) break;
  }
  const cols = new Map<number, string[]>();
  for (const i of ids) cols.set(rank.get(i)!, [...(cols.get(rank.get(i)!) ?? []), i]);
  const pos = new Map<string, { x: number; y: number }>();
  for (const [r, members] of cols) members.sort().forEach((m, k) => pos.set(m, { x: r * 195, y: k * 80 - ((members.length - 1) * 80) / 2 }));
  return pos;
}

export function RosGraph() {
  const graph = useRuntime((s) => s.graph);
  const connected = useRuntime((s) => s.connected);
  const echo = useRuntime((s) => s.echo);
  const { selectTopic, setLabTab } = useLesson();
  const [showSystem, setShowSystem] = useState(false);
  const [detail, setDetail] = useState<{ kind: "node" | "edge"; id: string } | null>(null);

  const { nodes, edges, topics } = useMemo(() => {
    if (!graph) return { nodes: [], edges: [], topics: [] as GraphTopic[] };
    const topics = graph.topics.filter((t) => showSystem || !t.system);
    const pos = layout(graph, topics);
    const nodes: Node[] = [
      ...graph.nodes.map((n) => ({ id: `n:${n.name}`, type: "ros", position: pos.get(`n:${n.name}`)!,
        data: { label: n.name, services: n.services.filter((s) => !s.system).length } })),
      ...topics.map((t) => ({ id: `t:${t.name}`, type: "topic", position: pos.get(`t:${t.name}`)!,
        data: { label: t.name, type: t.types[0], rate: echo[t.name]?.rate } })),
    ];
    const edges: Edge[] = [];
    for (const t of topics) {
      for (const p of t.publishers) edges.push({ id: `p|${p.node}|${t.name}`, source: `n:${p.node}`, target: `t:${t.name}`, animated: true,
        style: { stroke: "var(--series-1)", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3987e5" } });
      for (const s of t.subscribers) {
        const pairs = t.qos_pairs.filter((q) => q.subscriber === s.node);
        const level = pairs.some((q) => q.compatible === "error") ? "error" : pairs.some((q) => q.compatible === "warning") ? "warning" : pairs.length ? "ok" : "none";
        const color = { error: "#e66767", warning: "#c98500", ok: "#2fa36b", none: "#8b8a84" }[level];
        edges.push({ id: `s|${t.name}|${s.node}`, source: `t:${t.name}`, target: `n:${s.node}`, animated: level === "ok",
          label: level === "error" ? "QoS incompatible" : level === "none" ? "no publisher" : undefined,
          labelStyle: { fill: color, fontSize: 10 }, labelBgStyle: { fill: "#111214" },
          style: { stroke: color, strokeWidth: 2, strokeDasharray: level === "error" || level === "none" ? "4 4" : undefined },
          markerEnd: { type: MarkerType.ArrowClosed, color } });
      }
    }
    return { nodes, edges, topics };
  }, [graph, showSystem, echo]);

  if (!connected) return <Empty title="Connecting to your ROS 2 runtime…" />;
  if (!graph) return <Empty title="Waiting for the first graph snapshot">The telemetry agent is starting in your ROS domain.</Empty>;

  const detailNode = detail?.kind === "node" ? graph.nodes.find((n) => `n:${n.name}` === detail.id) : null;
  const detailEdge = detail?.kind === "edge" ? (() => {
    const [kind, a, b] = detail.id.split("|");
    const topic = graph.topics.find((t) => t.name === (kind === "p" ? b : a));
    return topic ? { topic, node: kind === "p" ? a : b, role: kind === "p" ? "publisher" : "subscriber" } : null;
  })() : null;

  return (
    <div className="relative flex h-full flex-col">
      <div className="flex h-8 shrink-0 items-center gap-3 border-b border-line px-3 text-xs text-muted">
        <span>{graph.nodes.length} nodes · {topics.length} topics</span>
        <span className="text-[10px]">live · updated {new Date(graph.t * 1000).toLocaleTimeString()}</span>
        <span className="flex-1" />
        <label className="flex items-center gap-1"><input type="checkbox" checked={showSystem} onChange={(e) => setShowSystem(e.target.checked)} /> system topics</label>
      </div>
      {graph.nodes.length === 0 ? (
        <Empty title="No nodes running">Run one of your executables. Nodes appear here within a couple of seconds. This graph is read from DDS discovery, not drawn by hand.</Empty>
      ) : (
        <div className="min-h-0 flex-1">
          <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ maxZoom: 1, padding: 0.08 }} colorMode="dark" proOptions={{ hideAttribution: true }}
            nodesDraggable onNodeClick={(_, n) => {
              if (n.id.startsWith("t:")) { selectTopic(n.id.slice(2)); setLabTab("topics"); } else setDetail({ kind: "node", id: n.id });
            }}
            onEdgeClick={(_, e) => setDetail({ kind: "edge", id: e.id })}>
            <Background color="#2a2c31" gap={20} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      )}
      {(detailNode || detailEdge) && (
        <div className="absolute bottom-2 right-2 z-10 max-h-[55%] w-80 overflow-auto rounded-md border border-line bg-panel p-3 text-xs shadow-xl">
          <button className="float-right text-muted hover:text-ink" onClick={() => setDetail(null)}>✕</button>
          {detailNode && (
            <>
              <div className="mb-2 font-mono text-[13px]">{detailNode.name}</div>
              {(["services", "clients", "action_servers", "action_clients"] as const).map((k) => {
                const items = detailNode[k].filter((s) => !s.system);
                return items.length ? (
                  <div key={k} className="mb-2"><div className="text-muted">{k.replace("_", " ")}</div>
                    {items.map((s) => <div key={s.name} className="font-mono">{s.name} <span className="text-muted">{s.type}</span></div>)}</div>
                ) : null;
              })}
              <div className="text-muted">{detailNode.services.filter((s) => s.system).length} parameter services hidden</div>
            </>
          )}
          {detailEdge && (() => {
            const { topic, node, role } = detailEdge;
            const ep = (role === "publisher" ? topic.publishers : topic.subscribers).find((e) => e.node === node);
            const pairs = topic.qos_pairs.filter((q) => (role === "publisher" ? q.publisher : q.subscriber) === node);
            return (
              <>
                <div className="mb-1 font-mono text-[13px]">{node} <span className="text-muted">{role}</span> {topic.name}</div>
                <div className="font-mono text-muted">{ep?.type}</div>
                {ep && <div className="mt-1">QoS: <span className="font-mono">{ep.qos.reliability} / {ep.qos.durability}</span></div>}
                <div className="mt-2 space-y-1">
                  {pairs.map((q) => (
                    <div key={q.publisher + q.subscriber}>
                      <Badge tone={q.compatible === "ok" ? "good" : q.compatible === "warning" ? "warn" : "bad"}>{q.compatible}</Badge>{" "}
                      <span className="font-mono">{q.publisher} → {q.subscriber}</span>
                      {q.reason && <div className="mt-0.5 text-bad">{q.reason}</div>}
                    </div>
                  ))}
                </div>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}
