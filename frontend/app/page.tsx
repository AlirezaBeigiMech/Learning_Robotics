"use client";

import { useEffect } from "react";

export default function Home() {
  useEffect(() => window.location.replace("/dashboard"), []);
  return <div className="p-8 text-muted">Loading…</div>;
}
