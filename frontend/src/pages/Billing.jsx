import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import client, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DashboardNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

export default function Billing() {
  const { user, refresh } = useAuth();
  const nav = useNavigate();
  const [plans, setPlans] = useState([]);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    client.get("/billing/plans").then(({ data }) => setPlans(data.plans));
  }, []);

  const buy = async (planId) => {
    setBusy(planId);
    try {
      const { data } = await client.post("/billing/checkout", {
        plan_id: planId,
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Checkout failed");
      setBusy(null);
    }
  };

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
          <div className="flex items-center justify-between">
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
        </div>

        <h2 className="font-display text-2xl tracking-tight mt-10 mb-4">Upgrade</h2>
        <div className="grid md:grid-cols-3 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
          {plans.map((p) => {
            const isCurrent = user?.plan === p.id;
            const featured = p.id === "pro";
            return (
              <div key={p.id} data-testid={`billing-plan-${p.id}`} className={`bg-[rgb(var(--tf-bg-2))] p-6 tf-beam ${featured ? "tf-active" : ""}`}>
                <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                  {p.name}
                </div>
                <div className="font-display text-4xl mt-2 tracking-tight">
                  ${p.amount}
                  <span className="text-sm text-[rgb(var(--tf-text-muted))] font-mono ml-1">/mo</span>
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
                  {isCurrent ? "Current" : busy === p.id ? "Redirecting…" : `Upgrade — $${p.amount}/mo`}
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
