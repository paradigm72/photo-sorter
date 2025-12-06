"use client";
import React, { useState, useEffect, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

function api(path: string, opts: RequestInit = {}) {
  const url = API_BASE ? `${API_BASE}${path.startsWith("/") ? path : "/" + path}` : `/api${path}`;
  return fetch(url, opts);
}

export default function RescanControls({ initialTotal }: { initialTotal: number }) {
  const [runningType, setRunningType] = useState<string | null>(null);
  const [total, setTotal] = useState(initialTotal);
  const [withFaces, setWithFaces] = useState<number | null>(null);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    // Start polling on mount so the controls reflect any scan already running
    startPolling();

    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
    };
  }, []);

  async function pollStatus() {
    try {
      const r = await api("/scan/status");
      if (r.ok) {
        const js = await r.json();
        setRunningType(js.type ?? null);
        setTotal(js.total ?? total);
        setWithFaces(js.with_faces ?? withFaces);
        if (!js.running && intervalRef.current) {
          window.clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function startPolling() {
    await pollStatus();
    if (!intervalRef.current) {
      intervalRef.current = window.setInterval(pollStatus, 2000);
    }
  }

  async function startScan(full = false) {
    try {
      const res = await api(full ? "/scan/full" : "/scan", { method: "POST" });
      if (!res.ok) {
        console.error("scan request failed", res.statusText);
        return;
      }
      const js = await res.json();
      if (js.status === "started" || js.status === "already_running") {
        await startPolling();
      }
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={() => startScan(false)} disabled={runningType !== null && runningType !== 'incremental'}>
          {runningType === 'incremental' ? 'Scan in progress…' : 'Scan for updates'}
        </button>
        {runningType === 'incremental' && <span>⏳ scanning updates</span>}
        <span> Total: {total}</span>
        {withFaces !== null && <span> • With faces: {withFaces}</span>}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={() => startScan(true)} disabled={runningType !== null && runningType !== 'full'}>
          {runningType === 'full' ? 'Full rescan in progress…' : 'Re-scan all photos'}
        </button>
        {runningType === 'full' && <span>⏳ full rescan</span>}
        <span style={{ color: 'var(--muted)' }}> (full rescan clears and rebuilds the DB)</span>
      </div>
    </div>
  );
}
