"use client";
import React, { useState, useEffect, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

function api(path: string, opts: RequestInit = {}) {
  const url = API_BASE ? `${API_BASE}${path.startsWith("/") ? path : "/" + path}` : `/api${path}`;
  return fetch(url, opts);
}

export default function RescanButton({ initialTotal }: { initialTotal: number }) {
  const [running, setRunning] = useState(false);
  const [total, setTotal] = useState(initialTotal);
  const [withFaces, setWithFaces] = useState<number | null>(null);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
    };
  }, []);

  async function startPolling() {
    // poll every 2s
    intervalRef.current = window.setInterval(async () => {
      try {
        const s = await api("/scan/status");
        if (s.ok) {
          const js = await s.json();
          setRunning(Boolean(js.running));
          setTotal(js.total ?? total);
          setWithFaces(js.with_faces ?? withFaces);
          if (!js.running && intervalRef.current) {
            window.clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
        const st = await api("/stats");
        if (st.ok) {
          const jst = await st.json();
          setTotal(jst.total ?? total);
          setWithFaces(jst.with_faces ?? withFaces);
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  }

  async function handleRescan(e: React.MouseEvent) {
    e.preventDefault();
    try {
      const res = await api("/scan", { method: "POST" });
      if (!res.ok) {
        console.error("scan request failed", res.statusText);
        return;
      }
      const js = await res.json();
      if (js.status === "started" || js.status === "already_running") {
        setRunning(true);
        // start polling
        await startPolling();
      }
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div>
      <button onClick={handleRescan} disabled={running} style={{ marginRight: 8 }}>
        {running ? "Scan in progress…" : "Rescan Photos"}
      </button>
      <span> Total: {total}</span>
      {withFaces !== null && <span> • With faces: {withFaces}</span>}
    </div>
  );
}
