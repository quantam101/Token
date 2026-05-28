import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import client, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DashboardNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

function usageBarColor(percent) {
  if (percent >= 100) return "bg-[rgb(var(--tf-error))]";
  if (percent >= 80) return "bg-[rgb(var(--tf-warning))]";
  return "bg-[rgb(var(--tf-success))]";
}

export default function Billing() {
  const { user } = useAuth();
  const [plans, setPlans] = useState([]);
  const [busy, setBusy] = useState(null);
  const [cycle, setCycle] = useState("monthly");
  const [discount, setDiscount] = useState(20);

  useEffect(() => {
    client.get("/billing/plans").then(({ data }) => {
      // Only show paid plans on billing page (free isn't upgradable)
      setPlans(data.plans.filter((p) => p.id !== "free"));
      setDiscount(data.annual_discount_pct || 20);
    });
    // Intentionally one-shot on mount; plan list is static for the session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const buy = async (planId) => {
    setBusy(planId);
    try {
      const { data } = await client.post("/billing/checkout", {
        plan_id: planId,
        origin_url: window.location.origin,
        billing_cycle: cycle,
      });
      window.location.href = data.url;
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Checkout failed");
      setBusy(null);
    }
  };

  const usage = user?.usage || { tokens_used: 0, monthly_quota: 50000, percent_used: 0 };
  const pct = Math.min(100, usage.percent_used || 0);

  return (
    <div className="min-h-screen flex flex-col">
      <DashboardNav />
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8">
        <div>
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
            BILLING
          </div>
          <h1 className="font-display text-3xl tracking-tight mt-1">Plan & Usage</h1>
        </div>

        <div className="mt-6 border border-[rgb(var(--tf-border))] p-6 bg-[rgb(var(--tf-bg-2))]" data-testid="current-plan-card">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Current plan
              </div>
              <div className="font-display text-3xl mt-1 capitalize">{user?.plan || "free"}</div>
            </div>
            <div className="text-right">
              <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Monthly quota
              </div>
              <div className="font-mono mt-1 text-[rgb(var(--tf-success))]">
                {(user?.monthly_quota || 50_000).toLocaleString()} tk
              </div>
            </div>
          </div>
          {/* Usage bar */}
          <div className="mt-5">
            <div className="flex items-center justify-between text-xs font-mono mb-2">
              <span className="uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Used this month
              </span>
              <span className="text-[rgb(var(--tf-text-2))]">
                {usage.tokens_used.toLocaleString()} / {usage.monthly_quota.toLocaleString()} ({pct}%)
              </span>
            </div>
            <div className="h-2 bg-[rgb(var(--tf-bg-3))] rounded-sm overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${usageBarColor(pct)}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        </div>

        <div className="mt-10 flex items-center justify-between flex-wrap gap-3">
          <h2 className="font-display text-2xl tracking-tight">Upgrade</h2>
          <div
            data-testid="billing-cycle-toggle"
            className="inline-flex items-center gap-1 p-1 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] rounded-md"
          >
            <button
              data-testid="bill-cycle-monthly"
              onClick={() => setCycle("monthly")}
              className={`px-3 py-1.5 text-xs font-mono uppercase tracking-widest rounded-sm transition-colors ${
                cycle === "monthly" ? "bg-[rgb(var(--tf-bg-3))] text-white" : "text-[rgb(var(--tf-text-2))] hover:text-white"
              }`}
            >
              Monthly
            </button>
            <button
              data-testid="bill-cycle-annual"
              onClick={() => setCycle("annual")}
              className={`px-3 py-1.5 text-xs font-mono uppercase tracking-widest rounded-sm transition-colors flex items-center gap-2 ${
                cycle === "annual" ? "bg-[rgb(var(--tf-bg-3))] text-white" : "text-[rgb(var(--tf-text-2))] hover:text-white"
              }`}
            >
              Annual <span className="text-[10px] text-[rgb(var(--tf-success))]">−{discount}%</span>
            </button>
          </div>
        </div>
        <div className="mt-4 grid md:grid-cols-3 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
          {plans.map((p) => {
            const isCurrent = user?.plan === p.id;
            const featured = p.id === "pro";
            const price = cycle === "annual" ? (p.annual_amount / 12).toFixed(2) : p.amount.toFixed(2).replace(/\.00$/, "");
            return (
              <div key={p.id} data-testid={`billing-plan-${p.id}`} className={`bg-[rgb(var(--tf-bg-2))] p-6 tf-beam ${featured ? "tf-active" : ""}`}>
                <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                  {p.name}
                </div>
                <div className="font-display text-4xl mt-2 tracking-tight">
                  ${price}
                  <span className="text-sm text-[rgb(var(--tf-text-muted))] font-mono ml-1">
                    {cycle === "annual" ? "/mo, billed annually" : "/mo"}
                  </span>
                </div>
                <div className="font-mono text-xs text-[rgb(var(--tf-text-2))] mt-1">
                  {p.monthly_quota.toLocaleString()} tokens / mo
                </div>
                <button
                  data-testid={`billing-buy-${p.id}`}
                  disabled={isCurrent || busy === p.id}
                  onClick={() => buy(p.id)}
                  className={`mt-5 w-full px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    featured
                      ? "bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black"
                      : "border border-[rgb(var(--tf-border-2))] hover:border-white"
                  } disabled:opacity-60`}
                >
                  {isCurrent ? "Current" : busy === p.id ? "Redirecting…" : `Upgrade — ${cycle === "annual" ? `$${p.annual_amount.toFixed(0)}/yr` : `$${p.amount}/mo`}`}
                </button>
              </div>
            );
          })}
        </div>

        <div className="mt-8 text-xs font-mono text-[rgb(var(--tf-text-muted))]">
          Payments processed by Stripe · Cancel anytime
        </div>
      </main>
      <Footer />
    </div>
  );
}

export function BillingSuccess() {
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [status, setStatus] = useState({ status: "checking", payment_status: "" });
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    const sessionId = new URLSearchParams(window.location.search).get("session_id");
    if (!sessionId) {
      nav("/dashboard/billing");
      return;
    }
    let cancelled = false;
    const poll = async (n) => {
      if (cancelled) return;
      if (n >= 12) {
        setStatus({ status: "timeout" });
        return;
      }
      try {
        const { data } = await client.get(`/billing/status/${sessionId}`);
        setStatus(data);
        setAttempts(n + 1);
        if (data.payment_status === "paid") {
          toast.success("Payment confirmed — plan upgraded.");
          await refresh();
          setTimeout(() => nav("/dashboard"), 1200);
          return;
        }
        if (data.status === "expired") {
          toast.error("Session expired.");
          setTimeout(() => nav("/dashboard/billing"), 1200);
          return;
        }
        setTimeout(() => poll(n + 1), 2000);
      } catch (e) {
        setStatus({ status: "error", payment_status: "" });
      }
    };
    poll(0);
    return () => { cancelled = true; };
  }, [nav, refresh]);

  return (
    <div className="min-h-screen flex flex-col">
      <DashboardNav />
      <main className="flex-1 flex items-center justify-center px-6">
        <div className="text-center" data-testid="billing-success-state">
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">
            STRIPE CHECKOUT
          </div>
          <div className="font-display text-4xl mt-3">
            {status.payment_status === "paid"
              ? "Payment confirmed"
              : status.status === "timeout"
              ? "Still processing…"
              : status.status === "expired"
              ? "Session expired"
              : "Checking payment status"}
          </div>
          <div className="mt-3 text-[rgb(var(--tf-text-2))] font-mono text-sm">
            attempt {attempts}/12
            {status.status === "complete" && status.payment_status === "paid" && (
              <span className="ml-2 text-[rgb(var(--tf-success))]">✓ paid</span>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
