import React, { useEffect, useState } from "react";
import client, { formatApiErrorDetail } from "@/lib/api";
import { DashboardNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await client.get("/dashboard/logs?limit=100");
      setLogs(data.logs);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <DashboardNav />
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        <div className="flex items-end justify-between mb-6">
          <div>
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
              REQUEST STREAM
            </div>
            <h1 className="font-display text-3xl tracking-tight mt-1">Logs</h1>
          </div>
          <button
            data-testid="logs-refresh"
            onClick={load}
            className="text-xs font-mono border border-[rgb(var(--tf-border))] hover:border-[rgb(var(--tf-brand))] px-3 py-1.5 rounded-sm text-[rgb(var(--tf-text-2))] hover:text-white transition-colors"
          >
            ⟳ refresh
          </button>
        </div>

        <div className="border border-[rgb(var(--tf-border))] overflow-x-auto" data-testid="logs-table">
          <table className="w-full text-sm font-mono">
            <thead className="text-[rgb(var(--tf-text-muted))] text-xs uppercase">
              <tr className="border-b border-[rgb(var(--tf-border))]">
                <th className="px-4 py-3 text-left">Time</th>
                <th className="px-4 py-3 text-left">Provider</th>
                <th className="px-4 py-3 text-left">Model</th>
                <th className="px-4 py-3 text-left">Tier</th>
                <th className="px-4 py-3 text-left">Cache</th>
                <th className="px-4 py-3 text-right">Original</th>
                <th className="px-4 py-3 text-right">Optimized</th>
                <th className="px-4 py-3 text-right">Completion</th>
                <th className="px-4 py-3 text-right">Saved</th>
                <th className="px-4 py-3 text-right">$ saved</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10} className="px-4 py-12 text-center text-[rgb(var(--tf-text-muted))]">loading…</td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan={10} className="px-4 py-12 text-center text-[rgb(var(--tf-text-muted))]">No proxy calls yet — see Docs to start.</td></tr>
              ) : logs.map((l) => (
                <tr key={l.id} className="border-b border-[rgb(var(--tf-border))] hover:bg-[rgb(var(--tf-bg-2))]">
                  <td className="px-4 py-2 text-[rgb(var(--tf-text-2))] text-xs">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2">{l.provider}</td>
                  <td className="px-4 py-2">{l.model}</td>
                  <td className="px-4 py-2">{l.tier}</td>
                  <td className="px-4 py-2">{l.cache_hit ? <span className="text-[rgb(var(--tf-success))]">HIT</span> : "—"}</td>
                  <td className="px-4 py-2 text-right">{l.original_tokens}</td>
                  <td className="px-4 py-2 text-right">{l.optimized_tokens}</td>
                  <td className="px-4 py-2 text-right">{l.completion_tokens}</td>
                  <td className="px-4 py-2 text-right text-[rgb(var(--tf-success))]">{l.tokens_saved}</td>
                  <td className="px-4 py-2 text-right">${l.cost_saved_usd?.toFixed(5)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
      <Footer />
    </div>
  );
}
