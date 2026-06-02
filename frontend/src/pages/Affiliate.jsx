import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import client from "@/lib/api";
import { MarketingNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

const TIERS = [
  { label: "Starter", commission: 20, threshold: "$0", color: "text-[rgb(var(--tf-text-2))]" },
  { label: "Growth", commission: 25, threshold: "5 active referrals", color: "text-[rgb(var(--tf-brand))]" },
  { label: "Partner", commission: 30, threshold: "15 active referrals", color: "text-[rgb(var(--tf-success))]" },
];

const STEPS = [
  { n: "01", title: "Sign up free", desc: "Create your TokenForge account — no credit card required." },
  { n: "02", title: "Get your link", desc: "Your unique referral link is generated instantly from your dashboard." },
  { n: "03", title: "Share anywhere", desc: "Blog, X, YouTube, Discord — wherever your audience lives." },
  { n: "04", title: "Earn recurring", desc: "Get paid every month your referrals stay subscribed. No cap." },
];

const FAQS = [
  { q: "When do I get paid?", a: "Payouts process on the 1st of each month via Stripe for all balances over $25. International? We pay via bank transfer." },
  { q: "How long does the cookie last?", a: "90 days. If someone clicks your link and upgrades within 90 days, you earn the commission." },
  { q: "Does commission apply to annual plans?", a: "Yes — you earn your commission rate on the full annual payment, paid out after the 30-day refund window." },
  { q: "Can I refer enterprise customers?", a: "Absolutely. Enterprise deals ($499+/mo) are tracked manually — reach out to affiliate@tokenforge.io after making an intro." },
  { q: "Is there a referral cap?", a: "No cap. Our top affiliates have earned over $2,000/mo in recurring commissions." },
];

function EarningsProjector() {
  const [referrals, setReferrals] = useState(10);
  const [avgPlan, setAvgPlan] = useState(99);
  const commission = referrals >= 15 ? 0.30 : referrals >= 5 ? 0.25 : 0.20;
  const monthly = referrals * avgPlan * commission;
  const annual = monthly * 12;
  const tier = referrals >= 15 ? "Partner" : referrals >= 5 ? "Growth" : "Starter";

  return (
    <div className="border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] p-8">
      <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))] mb-6">EARNINGS PROJECTOR</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div>
            <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-2 uppercase tracking-widest">
              Active referrals: <span className="text-white">{referrals}</span>
            </label>
            <input type="range" min={1} max={100} value={referrals}
              onChange={(e) => setReferrals(Number(e.target.value))}
              className="w-full accent-[rgb(var(--tf-brand))]" />
          </div>
          <div>
            <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-2 uppercase tracking-widest">
              Avg plan: <span className="text-white">${avgPlan}/mo</span>
            </label>
            <input type="range" min={19} max={499} step={10} value={avgPlan}
              onChange={(e) => setAvgPlan(Number(e.target.value))}
              className="w-full accent-[rgb(var(--tf-brand))]" />
            <div className="flex justify-between text-xs text-[rgb(var(--tf-text-muted))] mt-1">
              <span>Starter $19</span><span>Pro $99</span><span>Enterprise $499</span>
            </div>
          </div>
        </div>
        <div className="flex flex-col justify-center gap-4">
          <div>
            <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))] uppercase tracking-widest">Tier</div>
            <div className="font-display text-2xl mt-1">{tier} · {(commission * 100).toFixed(0)}% commission</div>
          </div>
          <div>
            <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))] uppercase tracking-widest">Monthly earnings</div>
            <div className="font-display text-4xl mt-1 text-[rgb(var(--tf-success))]">${monthly.toFixed(0)}<span className="text-lg text-[rgb(var(--tf-text-muted))]">/mo</span></div>
          </div>
          <div>
            <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))] uppercase tracking-widest">Annual earnings</div>
            <div className="font-display text-2xl mt-1 text-[rgb(var(--tf-brand))]">${annual.toLocaleString(undefined, { maximumFractionDigits: 0 })}/yr</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Affiliate() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [applying, setApplying] = useState(false);

  const joinProgram = async () => {
    if (!user) {
      nav("/register?ref=affiliate");
      return;
    }
    setApplying(true);
    try {
      const { data } = await client.post("/referrals/join-affiliate");
      toast.success("You're in! Check your referral dashboard.");
      nav("/refer");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not enroll. Try again.");
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <MarketingNav />
      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-7xl mx-auto px-6 py-24 text-center">
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">AFFILIATE PROGRAM</div>
          <h1 className="font-display text-6xl tracking-tighter mt-4">
            Earn up to 30% recurring.<br />Every month. No cap.
          </h1>
          <p className="text-[rgb(var(--tf-text-2))] text-xl mt-6 max-w-2xl mx-auto">
            Refer developers and teams to TokenForge. Earn commission as long as they stay subscribed.
            Most affiliates go full-time within 12 months.
          </p>
          <button onClick={joinProgram} disabled={applying}
            className="mt-10 bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-10 py-4 rounded-md text-lg transition-colors disabled:opacity-60">
            {user ? "Get my referral link →" : "Join for free →"}
          </button>
          <div className="mt-4 text-xs text-[rgb(var(--tf-text-muted))]">No approval process. Instant link. Paid monthly.</div>
        </section>

        {/* Commission tiers */}
        <section className="max-w-5xl mx-auto px-6 py-16">
          <div className="text-center mb-10">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">COMMISSION TIERS</div>
            <h2 className="font-display text-4xl mt-3">More referrals, higher rate</h2>
          </div>
          <div className="grid grid-cols-3 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
            {TIERS.map((t) => (
              <div key={t.label} className="bg-[rgb(var(--tf-bg-2))] p-8 text-center">
                <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">{t.label}</div>
                <div className={`font-display text-5xl mt-3 ${t.color}`}>{t.commission}%</div>
                <div className="text-sm text-[rgb(var(--tf-text-muted))] mt-2">From {t.threshold}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-center text-xs text-[rgb(var(--tf-text-muted))]">
            Commission applies to Starter ($19), Pro ($99), and Enterprise ($499) plans — monthly and annual.
          </div>
        </section>

        {/* Earnings projector */}
        <section className="max-w-5xl mx-auto px-6 py-8">
          <EarningsProjector />
        </section>

        {/* How it works */}
        <section className="max-w-5xl mx-auto px-6 py-16">
          <div className="text-center mb-12">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">HOW IT WORKS</div>
            <h2 className="font-display text-4xl mt-3">Four steps to passive income</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
            {STEPS.map((s) => (
              <div key={s.n} className="bg-[rgb(var(--tf-bg-2))] p-6">
                <div className="font-mono text-3xl text-[rgb(var(--tf-border-2))]">{s.n}</div>
                <div className="font-display text-xl mt-3">{s.title}</div>
                <div className="text-sm text-[rgb(var(--tf-text-2))] mt-2 leading-relaxed">{s.desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section className="max-w-3xl mx-auto px-6 py-16">
          <div className="text-center mb-10">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">FAQ</div>
            <h2 className="font-display text-4xl mt-3">Common questions</h2>
          </div>
          <div className="space-y-4">
            {FAQS.map((faq) => (
              <details key={faq.q} className="border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] group">
                <summary className="px-6 py-4 cursor-pointer font-medium text-sm flex justify-between items-center">
                  {faq.q}
                  <span className="font-mono text-[rgb(var(--tf-text-muted))] group-open:rotate-45 transition-transform">+</span>
                </summary>
                <div className="px-6 pb-4 text-sm text-[rgb(var(--tf-text-2))] leading-relaxed">{faq.a}</div>
              </details>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="max-w-3xl mx-auto px-6 pb-24 text-center">
          <div className="border border-[rgb(var(--tf-brand))]/30 bg-[rgb(var(--tf-brand))]/5 p-12">
            <h2 className="font-display text-4xl">Start earning today</h2>
            <p className="text-[rgb(var(--tf-text-2))] mt-4">
              Join hundreds of developers, bloggers, and agencies already earning recurring revenue with TokenForge.
            </p>
            <button onClick={joinProgram} disabled={applying}
              className="mt-8 bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-10 py-4 rounded-md text-lg transition-colors disabled:opacity-60">
              {user ? "Get my referral link →" : "Join the program →"}
            </button>
            <div className="mt-4 text-xs text-[rgb(var(--tf-text-muted))]">
              Questions? <a href="mailto:affiliate@tokenforge.io" className="underline hover:text-white">affiliate@tokenforge.io</a>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
