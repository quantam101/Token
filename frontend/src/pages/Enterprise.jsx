import React, { useState } from "react";
import { Link } from "react-router-dom";
import { MarketingNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

const ROI_MODELS = {
  "gpt-4o":            { label: "GPT-4o",           inputPer1M: 5.00 },
  "gpt-4o-mini":       { label: "GPT-4o mini",       inputPer1M: 0.15 },
  "claude-sonnet-4-6": { label: "Claude Sonnet",     inputPer1M: 3.00 },
  "claude-haiku-4-5":  { label: "Claude Haiku",      inputPer1M: 0.80 },
  "gemini-2.5-pro":    { label: "Gemini 2.5 Pro",    inputPer1M: 1.25 },
  "gemini-2.5-flash":  { label: "Gemini 2.5 Flash",  inputPer1M: 0.30 },
};

const ENTERPRISE_FEATURES = [
  { icon: "⚡", title: "100M tokens / month", desc: "High-throughput routing across all major LLM providers." },
  { icon: "🔑", title: "BYO Keys — all providers", desc: "OpenAI, Anthropic, Google, Cohere, Mistral — one unified API." },
  { icon: "🛡️", title: "SSO / SAML", desc: "Okta, Azure AD, Google Workspace — zero extra config." },
  { icon: "📊", title: "99.99% SLA", desc: "Dedicated routing layer, health monitors, instant failover." },
  { icon: "🚀", title: "White-glove onboarding", desc: "Dedicated solutions engineer, integration review, custom playbook." },
  { icon: "📄", title: "Custom contracts", desc: "MSA, DPA, BAA, invoicing — whatever your procurement needs." },
  { icon: "🔒", title: "Data residency", desc: "US, EU, or customer-hosted deployment options." },
  { icon: "📈", title: "ROI reporting", desc: "Weekly savings dashboards sent to your FinOps team." },
];

function RoiCalculator() {
  const [model, setModel] = useState("gpt-4o");
  const [reqPerMonth, setReqPerMonth] = useState(500000);
  const [avgTokens, setAvgTokens] = useState(800);
  const [compressionPct, setCompressionPct] = useState(55);

  const selected = ROI_MODELS[model];
  const monthlyInputTokens = reqPerMonth * avgTokens;
  const currentCost = (monthlyInputTokens / 1_000_000) * selected.inputPer1M;
  const savedCost = currentCost * (compressionPct / 100);
  const annualSavings = savedCost * 12;
  const enterpriseCost = 499 * 12; // enterprise annual
  const netAnnualSavings = annualSavings - enterpriseCost;
  const roi = enterpriseCost > 0 ? ((netAnnualSavings / enterpriseCost) * 100).toFixed(0) : 0;

  return (
    <div className="border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] p-8">
      <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))] mb-6">ROI PROJECTOR</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-2 uppercase tracking-widest">Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] text-white text-sm px-3 py-2 rounded-md"
          >
            {Object.entries(ROI_MODELS).map(([id, m]) => (
              <option key={id} value={id}>{m.label} (${m.inputPer1M}/M tokens)</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-2 uppercase tracking-widest">
            Requests / month: <span className="text-white">{reqPerMonth.toLocaleString()}</span>
          </label>
          <input type="range" min={10000} max={10000000} step={10000} value={reqPerMonth}
            onChange={(e) => setReqPerMonth(Number(e.target.value))}
            className="w-full accent-[rgb(var(--tf-brand))]" />
        </div>
        <div>
          <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-2 uppercase tracking-widest">
            Avg tokens / request: <span className="text-white">{avgTokens.toLocaleString()}</span>
          </label>
          <input type="range" min={100} max={8000} step={100} value={avgTokens}
            onChange={(e) => setAvgTokens(Number(e.target.value))}
            className="w-full accent-[rgb(var(--tf-brand))]" />
        </div>
        <div>
          <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-2 uppercase tracking-widest">
            Compression: <span className="text-white">{compressionPct}%</span>
          </label>
          <input type="range" min={20} max={80} step={5} value={compressionPct}
            onChange={(e) => setCompressionPct(Number(e.target.value))}
            className="w-full accent-[rgb(var(--tf-brand))]" />
        </div>
      </div>
      <div className="mt-8 grid grid-cols-3 gap-4 border-t border-[rgb(var(--tf-border))] pt-6">
        <div className="text-center">
          <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))] uppercase tracking-widest">Current monthly cost</div>
          <div className="font-display text-3xl mt-1 text-red-400">${currentCost.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
        </div>
        <div className="text-center">
          <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))] uppercase tracking-widest">Annual savings</div>
          <div className="font-display text-3xl mt-1 text-[rgb(var(--tf-success))]">${annualSavings.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
        </div>
        <div className="text-center">
          <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))] uppercase tracking-widest">ROI vs Enterprise</div>
          <div className={`font-display text-3xl mt-1 ${netAnnualSavings > 0 ? "text-[rgb(var(--tf-brand))]" : "text-[rgb(var(--tf-text-2))]"}`}>
            {netAnnualSavings > 0 ? `${roi}%` : "Calculate"}
          </div>
        </div>
      </div>
      {netAnnualSavings > 0 && (
        <div className="mt-4 text-center text-sm text-[rgb(var(--tf-success))]">
          Net savings after Enterprise plan: <strong>${netAnnualSavings.toLocaleString(undefined, {maximumFractionDigits: 0})}/yr</strong>
        </div>
      )}
    </div>
  );
}

function ContactForm() {
  const [form, setForm] = useState({ name: "", email: "", company: "", volume: "", message: "" });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.email || !form.company) {
      toast.error("Email and company are required");
      return;
    }
    setSubmitting(true);
    try {
      // Post to a GitHub issue via our backend so no external service needed
      const res = await fetch("https://api.alreadyherellc.com/api/enterprise/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error("failed");
      setDone(true);
    } catch {
      // Fallback: mailto
      const subject = encodeURIComponent(`Enterprise inquiry — ${form.company}`);
      const body = encodeURIComponent(
        `Name: ${form.name}\nEmail: ${form.email}\nCompany: ${form.company}\nVolume: ${form.volume}\n\n${form.message}`
      );
      window.location.href = `mailto:enterprise@tokenforge.io?subject=${subject}&body=${body}`;
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="border border-[rgb(var(--tf-success))]/30 bg-[rgb(var(--tf-success))]/5 p-8 text-center">
        <div className="text-3xl mb-3">✓</div>
        <div className="font-display text-xl">We'll be in touch within 24h.</div>
        <div className="text-sm text-[rgb(var(--tf-text-2))] mt-2">Check your inbox at {form.email}</div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] p-8 space-y-4">
      <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))] mb-6">TALK TO SALES</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-1">Your name</label>
          <input value={form.name} onChange={set("name")} placeholder="Jane Smith"
            className="w-full bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] text-white text-sm px-3 py-2 rounded-md focus:outline-none focus:border-[rgb(var(--tf-brand))]" />
        </div>
        <div>
          <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-1">Work email *</label>
          <input type="email" value={form.email} onChange={set("email")} required placeholder="jane@company.com"
            className="w-full bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] text-white text-sm px-3 py-2 rounded-md focus:outline-none focus:border-[rgb(var(--tf-brand))]" />
        </div>
        <div>
          <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-1">Company *</label>
          <input value={form.company} onChange={set("company")} required placeholder="Acme Corp"
            className="w-full bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] text-white text-sm px-3 py-2 rounded-md focus:outline-none focus:border-[rgb(var(--tf-brand))]" />
        </div>
        <div>
          <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-1">Monthly LLM spend</label>
          <select value={form.volume} onChange={set("volume")}
            className="w-full bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] text-white text-sm px-3 py-2 rounded-md">
            <option value="">Select range</option>
            <option value="<1k">&lt; $1,000/mo</option>
            <option value="1k-5k">$1,000 – $5,000/mo</option>
            <option value="5k-20k">$5,000 – $20,000/mo</option>
            <option value="20k-100k">$20,000 – $100,000/mo</option>
            <option value=">100k">&gt; $100,000/mo</option>
          </select>
        </div>
      </div>
      <div>
        <label className="block text-xs font-mono text-[rgb(var(--tf-text-muted))] mb-1">What are you building?</label>
        <textarea value={form.message} onChange={set("message")} rows={3} placeholder="Describe your use case..."
          className="w-full bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] text-white text-sm px-3 py-2 rounded-md focus:outline-none focus:border-[rgb(var(--tf-brand))] resize-none" />
      </div>
      <button type="submit" disabled={submitting}
        className="w-full bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-6 py-3 rounded-md transition-colors disabled:opacity-60">
        {submitting ? "Sending…" : "Request enterprise demo →"}
      </button>
      <p className="text-xs text-[rgb(var(--tf-text-muted))] text-center">We respond within 24 hours. No spam, ever.</p>
    </form>
  );
}

export default function Enterprise() {
  return (
    <div className="min-h-screen flex flex-col">
      <MarketingNav />
      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-7xl mx-auto px-6 py-24 text-center">
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">ENTERPRISE</div>
          <h1 className="font-display text-6xl tracking-tighter mt-4 max-w-4xl mx-auto">
            Cut your LLM bill by 40–80%.<br />At any scale.
          </h1>
          <p className="text-[rgb(var(--tf-text-2))] text-xl mt-6 max-w-2xl mx-auto">
            TokenForge's 5-pillar distillation engine slots into your existing stack in under an hour.
            No model changes. No prompt rewrites. Just fewer tokens billed.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center mt-10">
            <a href="#contact"
              className="bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-8 py-3 rounded-md transition-colors">
              Talk to sales →
            </a>
            <Link to="/playground"
              className="border border-[rgb(var(--tf-border-2))] hover:border-white px-8 py-3 rounded-md transition-colors">
              Try the playground first
            </Link>
          </div>
        </section>

        {/* Social proof strip */}
        <section className="border-y border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] py-6">
          <div className="max-w-5xl mx-auto px-6 flex flex-wrap justify-center gap-12 text-center">
            {[["40–80%", "Token reduction"], ["< 1h", "Integration time"], ["99.99%", "Uptime SLA"], ["$0", "Model retraining"]].map(([v, l]) => (
              <div key={l}>
                <div className="font-display text-3xl text-[rgb(var(--tf-brand))]">{v}</div>
                <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))] mt-1 uppercase tracking-widest">{l}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ROI Calculator */}
        <section className="max-w-5xl mx-auto px-6 py-20">
          <div className="text-center mb-10">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">CALCULATE YOUR SAVINGS</div>
            <h2 className="font-display text-4xl mt-3">What would you save this year?</h2>
          </div>
          <RoiCalculator />
        </section>

        {/* Features grid */}
        <section className="max-w-7xl mx-auto px-6 py-16">
          <div className="text-center mb-12">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">ENTERPRISE PLAN</div>
            <h2 className="font-display text-4xl mt-3">Everything you need, nothing you don't</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
            {ENTERPRISE_FEATURES.map((f) => (
              <div key={f.title} className="bg-[rgb(var(--tf-bg-2))] p-6">
                <div className="text-2xl mb-3">{f.icon}</div>
                <div className="font-display text-lg mb-2">{f.title}</div>
                <div className="text-sm text-[rgb(var(--tf-text-2))] leading-relaxed">{f.desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Pricing callout */}
        <section className="max-w-3xl mx-auto px-6 py-8">
          <div className="border border-[rgb(var(--tf-brand))]/30 bg-[rgb(var(--tf-brand))]/5 p-8 text-center">
            <div className="font-display text-3xl">$499<span className="text-lg text-[rgb(var(--tf-text-2))]">/mo · billed annually</span></div>
            <div className="text-[rgb(var(--tf-text-2))] mt-2">or $5,988/yr — one invoice, zero per-seat fees</div>
            <div className="mt-4 text-sm text-[rgb(var(--tf-success))]">
              Most enterprise customers save 10–20× the plan cost in their first 90 days.
            </div>
          </div>
        </section>

        {/* Contact form */}
        <section id="contact" className="max-w-3xl mx-auto px-6 py-16">
          <div className="text-center mb-10">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">GET STARTED</div>
            <h2 className="font-display text-4xl mt-3">Book your onboarding call</h2>
            <p className="text-[rgb(var(--tf-text-2))] mt-3">We'll show you the ROI in 30 minutes. If it's not there, we'll say so.</p>
          </div>
          <ContactForm />
        </section>
      </main>
      <Footer />
    </div>
  );
}
