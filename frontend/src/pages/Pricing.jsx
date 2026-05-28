import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import client, { formatApiErrorDetail } from "@/lib/api";
import { MarketingNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

const FEATURES = {
  free: ["50K tokens / month", "Gemini 2.5 Flash only", "1 API key", "Community support"],
  starter: ["1M tokens / month", "Gemini 2.5 Flash only", "5 API keys", "Email support", "Dashboard analytics"],
  pro: [
    "10M tokens / month",
    "BYO Keys — OpenAI, Anthropic, Gemini",
    "All 5 distillation pillars",
    "Unlimited API keys",
    "Priority support",
    "Advanced semantic cache",
    "ROI savings report (PDF)",
  ],
  enterprise: [
    "100M tokens / month",
    "BYO Keys — all providers",
    "Dedicated routing layer",
    "SSO / SAML",
    "99.99% SLA",
    "White-glove onboarding",
    "Custom contracts",
  ],
};

export default function Pricing() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [plans, setPlans] = useState([]);
  const [discount, setDiscount] = useState(20);
  const [busy, setBusy] = useState(null);
  const [cycle, setCycle] = useState("monthly"); // monthly | annual

  useEffect(() => {
    client.get("/billing/plans").then(({ data }) => {
      setPlans(data.plans);
      setDiscount(data.annual_discount_pct || 20);
    });
  }, []);

  const buy = async (planId) => {
    if (!user) {
      nav("/register");
      return;
    }
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

  const displayPrice = (p) => {
    if (p.id === "free") return { value: 0, sub: "/mo" };
    if (cycle === "annual") {
      // show monthly-equivalent on annual card
      return { value: (p.annual_amount / 12).toFixed(2), sub: "/mo, billed annually", total: p.annual_amount };
    }
    return { value: p.amount.toFixed(2).replace(/\.00$/, ""), sub: "/mo" };
  };

  return (
    <div className="min-h-screen flex flex-col">
      <MarketingNav />
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-16">
        <div className="text-center max-w-2xl mx-auto">
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">PRICING</div>
          <h1 className="font-display text-5xl tracking-tighter mt-3">Pay for tokens you'd save.</h1>
          <p className="text-[rgb(var(--tf-text-2))] mt-4">
            Every plan includes the full 5-pillar engine. You only pay more when you process more.
          </p>

          {/* Billing cycle toggle */}
          <div
            data-testid="billing-cycle-toggle"
            className="mt-8 inline-flex items-center gap-1 p-1 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] rounded-md"
          >
            <button
              data-testid="cycle-monthly"
              onClick={() => setCycle("monthly")}
              className={`px-4 py-1.5 text-xs font-mono uppercase tracking-widest rounded-sm transition-colors ${
                cycle === "monthly" ? "bg-[rgb(var(--tf-bg-3))] text-white" : "text-[rgb(var(--tf-text-2))] hover:text-white"
              }`}
            >
              Monthly
            </button>
            <button
              data-testid="cycle-annual"
              onClick={() => setCycle("annual")}
              className={`px-4 py-1.5 text-xs font-mono uppercase tracking-widest rounded-sm transition-colors flex items-center gap-2 ${
                cycle === "annual" ? "bg-[rgb(var(--tf-bg-3))] text-white" : "text-[rgb(var(--tf-text-2))] hover:text-white"
              }`}
            >
              Annual
              <span className="text-[10px] text-[rgb(var(--tf-success))]">−{discount}%</span>
            </button>
          </div>
        </div>

        <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
          {plans.map((t) => {
            const featured = t.id === "pro";
            const isCurrent = user?.plan === t.id;
            const price = displayPrice(t);
            return (
              <div
                key={t.id}
                data-testid={`pricing-card-${t.id}`}
                className={`bg-[rgb(var(--tf-bg-2))] p-8 flex flex-col tf-beam ${featured ? "tf-active" : ""}`}
              >
                {featured && (
                  <div className="text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--tf-brand))] mb-2">
                    Most popular
                  </div>
                )}
                <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                  {t.name || t.id}
                </div>
                <div className="font-display text-5xl mt-2 tracking-tight">
                  ${price.value}
                  <span className="text-sm text-[rgb(var(--tf-text-muted))] font-mono ml-1">{price.sub}</span>
                </div>
                {price.total && (
                  <div className="text-[10px] font-mono text-[rgb(var(--tf-success))] mt-1">
                    ${price.total.toFixed(2)} billed yearly
                  </div>
                )}
                <div className="font-mono text-xs text-[rgb(var(--tf-text-2))] mt-1">
                  {t.id === "free" ? "50,000" : t.monthly_quota?.toLocaleString()} tokens / mo
                </div>
                <ul className="mt-6 space-y-2 text-sm text-[rgb(var(--tf-text-2))] flex-1">
                  {(FEATURES[t.id] || []).map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <span className="text-[rgb(var(--tf-success))] mt-1">▸</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-6">
                  {t.id === "free" ? (
                    <Link
                      to={user ? "/dashboard" : "/register"}
                      data-testid={`pricing-cta-${t.id}`}
                      className="block text-center border border-[rgb(var(--tf-border-2))] hover:border-white px-4 py-2.5 rounded-md text-sm transition-colors"
                    >
                      {user ? "Go to dashboard" : "Start free →"}
                    </Link>
                  ) : t.id === "enterprise" ? (
                    <a
                      href="mailto:enterprise@tokenforge.io"
                      data-testid={`pricing-cta-${t.id}`}
                      className="block text-center border border-[rgb(var(--tf-border-2))] hover:border-white px-4 py-2.5 rounded-md text-sm transition-colors"
                    >
                      Talk to sales →
                    </a>
                  ) : (
                    <button
                      data-testid={`pricing-cta-${t.id}`}
                      disabled={busy === t.id || isCurrent}
                      onClick={() => buy(t.id)}
                      className={`w-full px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                        featured
                          ? "bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black"
                          : "border border-[rgb(var(--tf-border-2))] hover:border-white"
                      } disabled:opacity-60`}
                    >
                      {isCurrent ? "Current plan" : busy === t.id ? "Redirecting…" : `Upgrade — ${cycle === "annual" ? `$${(t.annual_amount).toFixed(0)}/yr` : `$${t.amount}/mo`}`}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-12 text-center text-xs font-mono text-[rgb(var(--tf-text-muted))]">
          All payments processed by Stripe · Cancel anytime · Quotas reset monthly
        </div>
      </main>
      <Footer />
    </div>
  );
}
