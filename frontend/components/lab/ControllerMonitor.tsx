"use client";

import { useEffect } from "react";
import { useRuntime } from "@/lib/runtime";
import { Badge, Empty } from "../ui";

const tone = (state: string) => (state === "active" ? "good" : state === "inactive" ? "warn" : "bad") as "good" | "warn" | "bad";

/** Live ros2_control state: controllers per controller_manager, polled from list_controllers. */
export function ControllerMonitor() {
  const controllers = useRuntime((s) => s.controllers);
  const jointStates = useRuntime((s) => s.jointStates);
  const simClock = useRuntime((s) => s.simClock);
  const managers = controllers?.managers ?? [];
  const { send, connected } = useRuntime();
  // joint states come from the agent's robot watcher
  useEffect(() => { if (connected) send({ cmd: "robot_watch", enable: true }); }, [connected, send]);

  if (!managers.length) {
    return (
      <Empty title="No controller_manager running">
        Launch your simulation. Gazebo&apos;s gz_ros2_control plugin starts a controller_manager, and its
        controllers appear here with their state and the hardware interfaces they claim.
      </Empty>
    );
  }
  return (
    <div className="h-full overflow-auto p-3 text-xs">
      {simClock && (
        <div className="mb-3 text-[11px] text-muted">
          sim time {simClock.simTime.toFixed(1)} s · real-time factor {simClock.rtf?.toFixed(2) ?? "…"}
        </div>
      )}
      {managers.map((m) => (
        <div key={m.manager} className="mb-4">
          <div className="mb-1 font-mono text-[12px] text-ink2">{m.manager}</div>
          <table className="w-full">
            <thead>
              <tr className="text-left text-muted">
                <th className="py-1">controller</th><th>type</th><th>state</th><th>claimed interfaces</th>
              </tr>
            </thead>
            <tbody>
              {m.controllers.map((c) => (
                <tr key={c.name} className="border-t border-line align-top">
                  <td className="py-1.5 pr-2 font-mono">{c.name}</td>
                  <td className="pr-2 font-mono text-[10.5px] text-muted">{c.type}</td>
                  <td className="pr-2"><Badge tone={tone(c.state)}>{c.state}</Badge></td>
                  <td className="font-mono text-[10.5px]">
                    {c.claimed_interfaces.length ? c.claimed_interfaces.join(", ")
                      : <span className="text-muted">{c.state === "active" ? "none (reads state only)" : "—"}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {jointStates && Object.keys(jointStates.positions).length > 0 && (
        <div>
          <div className="mb-1 font-semibold text-ink2">/joint_states <span className="font-normal text-muted">({jointStates.publishers.join(", ") || "?"})</span></div>
          <div className="grid grid-cols-[1fr_auto] gap-x-4 font-mono text-[11px]">
            {Object.entries(jointStates.positions).sort().map(([n, v]) => (
              <div key={n} className="contents"><span>{n}</span><span className="text-right">{v.toFixed(3)}</span></div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
