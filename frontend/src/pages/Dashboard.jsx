import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import client, { BACKEND_URL, getToken, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DashboardNav, Footer } from "@/components/Nav";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar } from "recharts";
import { toast } from "sonner";

export default function Dashboard() {
  const { user, refresh } = useAuth();
  const nav = useNavigate();
  const [overview, setOverview] = useState(null);
  const [series, setSeries] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  const load = async () => {
    try {
      const [ov, ts, lg] = await Promise.all([
        client.get("/dashboard/overview"),
        client.get("/dashboard/timeseries?days=14"),
        client.get("/dashboard/logs?limit=10"),
      ]);
      setOverview(ov.data);
      setSeries(ts.data.series);
      setLogs(lg.data.logs);
      await refresh();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const downloadReport = async () => {
    setDownloading(true);
    try {
      const token = getToken();
      const res = await fetch(`${BACKEND_URL}/api/reports/savings.pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tokenforge-savings-${new Date().toISOString().slice(0, 7).replace("-", "")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("ROI report downloaded");
    } catch (e) {
      toast.error("Failed to generate report");
    } finally {
      setDownloading(false);
    }
  };

  const [emailing, setEmailing] = useState(false);
  const emailReport = async () => {
    setEmailing(true);
    try {
      const { data } = await client.post("/reports/savings/email");
      if (data.sent) toast.success("Report emailed — check your inbox");
      else toast.error("Email failed — check backend config");
    } catch (e) {
      toast.error("Email failed");
    } finally {
      setEmailing(false);
    }
  };

  const [sharing, setSharing] = useState(false);
  const createShare = async () => {
    setSharing(true);
    try {
      const { data } = await client.post("/share/savings");
      const url = `${window.location.origin}/share/${data.slug}`;
      await navigator.clipboard.writeText(url);
      toast.success("Public share link copied to clipboard");
    } catch (e) {
      toast.error("Failed to create share link");
    } finally {
      setSharing(false);
    }
  };

  const usage = user?.usage || { tokens_used: 0, monthly_quota: 50000, percent_used: 0 };
  const pct = Math.min(100, usage.percent_used || 0);
  const showWarn = pct >= 80 && pct < 100;
  const showBlock = pct >= 100;

  return (
    <div className="min-h-screen flex flex-col">
      <DashboardNav />
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {/* Quota Alert Banner */}
        {(showWarn || showBlock) && (
          <div
            data-testid="quota-alert-banner"
            className={`mb-6 border rounded-md p-4 flex items-center justify-between flex-wrap gap-3 ${
              showBlock
                ? "border-[rgb(var(--tf-error))] bg-[rgba(244,67,54,0.08)]"
                : "border-[rgb(var(--tf-warning))] bg-[rgba(255,179,0,0.08)]"
            }`}
          >
            <div>
              <div className={`font-mono text-xs uppercase tracking-widest ${
                showBlock ? "text-[rgb(var(--tf-error))]" : "text-[rgb(var(--tf-warning))]"
              }`}>
                {showBlock ? "QUOTA EXCEEDED" : "QUOTA WARNING"}
              </div>
              <div className="text-sm mt-1">
                {showBlock
                  ? `You've used 100% of your monthly quota (${usage.tokens_used.toLocaleString()} / ${usage.monthly_quota.toLocaleString()} tokens). Proxy calls will return 429 until next month or an upgrade.`
                  : `You've used ${pct}% of your monthly quota (${usage.tokens_used.toLocaleString()} / ${usage.monthly_quota.toLocaleString()} tokens).`}
              </div>
            </div>
            <button
              data-testid="quota-alert-upgrade"
              onClick={() => nav("/dashboard/billing")}
              className="bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-4 py-2 rounded-md text-sm transition-colors"
            >
              Upgrade plan →
            </button>
          </div>
        )}

        <div className="flex items-end justify-between mb-6 flex-wrap gap-3">
          <div>
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
              CONTROL ROOM
            </div>
            <h1 className="font-display text-3xl tracking-tight mt-1">Overview</h1>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              data-testid="share-savings-btn"
              onClick={createShare}
              disabled={sharing}
              className="text-xs font-mono border border-[rgb(var(--tf-border))] hover:border-[rgb(var(--tf-success))] hover:text-[rgb(var(--tf-success))] px-3 py-1.5 rounded-sm text-[rgb(var(--tf-text-2))] transition-colors disabled:opacity-60"
            >
              {sharing ? "creating…" : "🔗 share my savings"}
            </button>
            <button
              data-testid="email-report-btn"
              onClick={emailReport}
              disabled={emailing}
              className="text-xs font-mono border border-[rgb(var(--tf-border))] hover:border-[rgb(var(--tf-brand))] hover:text-[rgb(var(--tf-brand))] px-3 py-1.5 rounded-sm text-[rgb(var(--tf-text-2))] transition-colors disabled:opacity-60"
            >
              {emailing ? "sending…" : "✉ email me the report"}
            </button>
            <button
              data-testid="download-report-btn"
              onClick={downloadReport}
              disabled={downloading}
              className="text-xs font-mono border border-[rgb(var(--tf-brand))] text-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand))] hover:text-black px-3 py-1.5 rounded-sm transition-colors disabled:opacity-60"
            >
              {downloading ? "generating…" : "↓ download ROI report (PDF)"}
            </button>
            <button
              data-testid="refresh-overview"
              onClick={load}
              className="text-xs font-mono border border-[rgb(var(--tf-border))] hover:border-[rgb(var(--tf-brand))] px-3 py-1.5 rounded-sm text-[rgb(var(--tf-text-2))] hover:text-white transition-colors"
            >
              ⟳ refresh
            </button>
          </div>
        </div>

        {/* Quota Meter */}
        <div data-testid="quota-meter" className="mb-6 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] p-5">
          <div className="flex items-center justify-between mb-3 text-xs font-mono">
            <span className="uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
              MONTHLY QUOTA · {(user?.plan || "free").toUpperCase()}
            </span>
            <span className="text-[rgb(var(--tf-text-2))]">
              <span data-testid="quota-used" className={
                showBlock ? "text-[rgb(var(--tf-error))]" :
                showWarn ? "text-[rgb(var(--tf-warning))]" :
                "text-[rgb(var(--tf-success))]"
              }>
                {usage.tokens_used.toLocaleString()}
              </span>
              {" / "}
              <span data-testid="quota-total">{usage.monthly_quota.toLocaleString()}</span>
              {" tokens "}
              <span className="text-[rgb(var(--tf-text-muted))]">({pct}%)</span>
            </span>
          </div>
          <div className="h-2 bg-[rgb(var(--tf-bg-3))] rounded-sm overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                showBlock ? "bg-[rgb(var(--tf-error))]" :
                showWarn ? "bg-[rgb(var(--tf-warning))]" :
                "bg-[rgb(var(--tf-success))]"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]" data-testid="kpi-grid">
          <KPI
            label="Tokens saved"
            value={(overview?.total_tokens_saved || 0).toLocaleString()}
            unit="tk"
            success
            big
          />
          <KPI
            label="$ saved"
            value={`$${(overview?.total_cost_saved_usd || 0).toFixed(4)}`}
          />
          <KPI label="Requests" value={(overview?.total_requests || 0).toLocaleString()} />
          <KPI
            label="Cache hit rate"
            value={`${overview?.cache_hit_rate || 0}%`}
            accent
          />
        </div>

        {/* Chart */}
        <div className="mt-6 grid lg:grid-cols-3 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
          <div className="bg-[rgb(var(--tf-bg-2))] p-6 lg:col-span-2" data-testid="chart-tokens">
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Tokens saved · last 14d
              </div>
              <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))]">
                avg −{overview?.avg_percent_saved || 0}%
              </div>
            </div>
            <div className="h-64">
              {series.length === 0 ? (
                <EmptyChart text="No data yet — try the proxy below" />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                    <XAxis dataKey="date" stroke="#71717A" fontSize={11} />
                    <YAxis stroke="#71717A" fontSize={11} />
                    <Tooltip
                      contentStyle={{ background: "#121212", border: "1px solid #27272A", fontSize: 12 }}
                      labelStyle={{ color: "#FAFAFA" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="tokens_saved"
                      stroke="#00E676"
                      strokeWidth={2}
                      dot={{ fill: "#00E676", r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
          <div className="bg-[rgb(var(--tf-bg-2))] p-6">
            <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))] mb-4">
              Requests · last 14d
            </div>
            <div className="h-64">
              {series.length === 0 ? (
                <EmptyChart text="—" />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                    <XAxis dataKey="date" stroke="#71717A" fontSize={10} />
                    <YAxis stroke="#71717A" fontSize={10} />
                    <Tooltip
                      contentStyle={{ background: "#121212", border: "1px solid #27272A", fontSize: 12 }}
                    />
                    <Bar dataKey="requests" fill="#FF4500" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* Recent Logs */}
        <div className="mt-6 border border-[rgb(var(--tf-border))]">
          <div className="px-5 py-3 flex items-center justify-between border-b border-[rgb(var(--tf-border))]">
            <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
              Recent proxy calls
            </div>
            <a
              href="/dashboard/logs"
              data-testid="link-all-logs"
              className="text-xs font-mono text-[rgb(var(--tf-brand))] hover:underline"
            >
              view all →
            </a>
          </div>
          <div className="overflow-x-auto" data-testid="recent-logs-table">
            <table className="w-full text-sm font-mono">
              <thead className="text-[rgb(var(--tf-text-muted))] text-xs uppercase">
                <tr>
                  <Th>Time</Th>
                  <Th>Model</Th>
                  <Th>Tier</Th>
                  <Th>Cache</Th>
                  <Th align="right">Orig</Th>
                  <Th align="right">Opt</Th>
                  <Th align="right">Saved</Th>
                  <Th align="right">$ saved</Th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-5 py-10 text-center text-[rgb(var(--tf-text-muted))]">
                      No requests yet. Make your first proxy call from <a className="text-[rgb(var(--tf-brand))] hover:underline" href="/docs">Docs</a>.
                    </td>
                  </tr>
                ) : (
                  logs.map((l) => (
                    <tr key={l.id} className="border-t border-[rgb(var(--tf-border))] hover:bg-[rgb(var(--tf-bg-2))]">
                      <Td>{new Date(l.created_at).toLocaleString()}</Td>
                      <Td>{l.model}</Td>
                      <Td>{l.tier}</Td>
                      <Td>{l.cache_hit ? <span className="text-[rgb(var(--tf-success))]">HIT</span> : "—"}</Td>
                      <Td align="right">{l.original_tokens}</Td>
                      <Td align="right">{l.optimized_tokens}</Td>
                      <Td align="right" className="text-[rgb(var(--tf-success))]">{l.tokens_saved}</Td>
                      <Td align="right">${l.cost_saved_usd?.toFixed(5)}</Td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function KPI({ label, value, unit, success, accent, big }) {
  return (
    <div className={`bg-[rgb(var(--tf-bg-2))] p-6 ${big ? "" : ""}`}>
      <div className="text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">{label}</div>
      <div className={`font-display text-3xl lg:text-4xl mt-2 tf-counter ${
        success ? "text-[rgb(var(--tf-success))]" : accent ? "text-[rgb(var(--tf-brand))]" : ""
      }`}>
        {value}
        {unit && <span className="text-xs ml-1 font-mono text-[rgb(var(--tf-text-muted))]">{unit}</span>}
      </div>
    </div>
  );
}

function Th({ children, align }) {
  return (
    <th className={`px-4 py-2 text-${align || "left"} font-mono font-medium text-xs`}>{children}</th>
  );
}
function Td({ children, align, className }) {
  return <td className={`px-4 py-2 text-${align || "left"} ${className || ""}`}>{children}</td>;
}
function EmptyChart({ text }) {
  return (
    <div className="h-full w-full flex items-center justify-center text-[rgb(var(--tf-text-muted))] text-sm font-mono">
      {text}
    </div>
  );
}
