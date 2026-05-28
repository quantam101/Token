import React, { useEffect, useState } from "react";
import client, { formatApiErrorDetail } from "@/lib/api";
import { DashboardNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

export default function Admin() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get("/admin/overview")
      .then(({ data }) => setData(data))
      .catch((e) => toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <DashboardNav />
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        <div>
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-error))]">
            ADMIN — SYSTEM
          </div>
          <h1 className="font-display text-3xl tracking-tight mt-1">Admin Console</h1>
        </div>

        {loading ? (
          <div className="mt-8 text-[rgb(var(--tf-text-muted))] font-mono">loading…</div>
        ) : !data ? (
          <div className="mt-8 text-[rgb(var(--tf-error))] font-mono">Access denied.</div>
        ) : (
          <>
            <div className="mt-6 grid grid-cols-2 lg:grid-cols-6 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]" data-testid="admin-kpis">
              <Kpi label="Users" value={data.users} />
              <Kpi label="Waitlist" value={data.waitlist} />
              <Kpi label="Requests" value={data.requests} />
              <Kpi label="Paid Tx" value={data.paid_transactions} />
              <Kpi label="Revenue" value={`$${data.revenue_usd.toFixed(2)}`} accent />
              <Kpi label="Tokens saved" value={data.total_tokens_saved.toLocaleString()} success />
            </div>

            <div className="mt-8">
              <h2 className="font-display text-xl tracking-tight mb-3">Recent waitlist</h2>
              <div className="border border-[rgb(var(--tf-border))] overflow-x-auto" data-testid="admin-waitlist-table">
                <table className="w-full text-sm font-mono">
                  <thead className="text-[rgb(var(--tf-text-muted))] text-xs uppercase">
                    <tr className="border-b border-[rgb(var(--tf-border))]">
                      <th className="px-4 py-3 text-left">Email</th>
                      <th className="px-4 py-3 text-left">Company</th>
                      <th className="px-4 py-3 text-left">Joined</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_waitlist?.length === 0 ? (
                      <tr><td colSpan={3} className="px-4 py-6 text-center text-[rgb(var(--tf-text-muted))]">No signups yet</td></tr>
                    ) : data.recent_waitlist?.map((w) => (
                      <tr key={w.id} className="border-b border-[rgb(var(--tf-border))]">
                        <td className="px-4 py-2">{w.email}</td>
                        <td className="px-4 py-2 text-[rgb(var(--tf-text-2))]">{w.company || "—"}</td>
                        <td className="px-4 py-2 text-[rgb(var(--tf-text-muted))] text-xs">{new Date(w.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}

function kpiColorClass(success, accent) {
  if (success) return "text-[rgb(var(--tf-success))]";
  if (accent) return "text-[rgb(var(--tf-brand))]";
  return "";
}

function Kpi({ label, value, accent, success }) {
  return (
    <div className="bg-[rgb(var(--tf-bg-2))] p-5">
      <div className="text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">{label}</div>
      <div className={`font-display text-2xl mt-2 tf-counter ${kpiColorClass(success, accent)}`}>{value}</div>
    </div>
  );
}
