"use client";

import clsx from "clsx";
import { ButtonHTMLAttributes, ReactNode } from "react";

export function Button({ variant = "default", size = "md", className, ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "ghost" | "danger"; size?: "sm" | "md" }) {
  return (
    <button
      {...props}
      className={clsx(
        "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md border font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
        size === "sm" ? "h-7 px-2 text-xs" : "h-8 px-3 text-[13px]",
        variant === "primary" && "border-accent bg-accent text-white hover:brightness-110",
        variant === "default" && "border-line bg-panel2 text-ink hover:bg-[#2a2c31]",
        variant === "ghost" && "border-transparent bg-transparent text-ink2 hover:bg-panel2",
        variant === "danger" && "border-[#5a2a2a] bg-[#2b1a1a] text-bad hover:bg-[#3a1f1f]",
        className,
      )}
    />
  );
}

export function Badge({ tone = "neutral", children, className }: { tone?: "neutral" | "good" | "warn" | "bad" | "accent"; children: ReactNode; className?: string }) {
  return (
    <span className={clsx(
      "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium leading-none",
      tone === "neutral" && "bg-panel2 text-ink2",
      tone === "good" && "bg-[#15301f] text-good",
      tone === "warn" && "bg-[#33270d] text-warn",
      tone === "bad" && "bg-[#3a1d1d] text-bad",
      tone === "accent" && "bg-[#162a44] text-accent",
      className,
    )}>{children}</span>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange, right }:
  { tabs: { id: T; label: ReactNode }[]; value: T; onChange: (v: T) => void; right?: ReactNode }) {
  return (
    <div className="flex h-9 shrink-0 items-stretch border-b border-line bg-panel">
      <div className="flex min-w-0 flex-1 items-stretch overflow-x-auto">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => onChange(t.id)}
            className={clsx("whitespace-nowrap border-b-2 px-3 text-[13px]",
              value === t.id ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink2")}>
            {t.label}
          </button>
        ))}
      </div>
      {right && <div className="flex items-center gap-1 px-2">{right}</div>}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
      <div className="text-sm font-medium text-ink2">{title}</div>
      {children && <div className="max-w-sm text-xs leading-relaxed text-muted">{children}</div>}
    </div>
  );
}
