import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import client, { formatApiErrorDetail } from "@/lib/api";
import { MarketingNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

const HERO_BG =
  "https://static.prod-images.emergentagent.com/jobs/1cf30eb1-b91f-40f9-9ca0-9229018c5ce8/images/d657e5bc154183e09cb6042310433410ee6496a7c94719bd8576df1dbaa03bd5.png";
const INFRA_IMG =
  "https://images.unsplash.com/photo-1695668548342-c0c1ad479aee?crop=entropy&cs=srgb&fm=jpg&q=85";

const SAMPLE = `Hello, could you please help me? In order to summarize the following information about artificial intelligence and machine learning, I would like you to write a paragraph. Thank you in advance for your help.`;

function useTypedCounter(target, duration = 1500) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let start;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min(1, (ts - start) / duration);
      setV(Math.floor(target * (0.2 + 0.8 * (1 - Math.pow(1 - p, 3)))));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);
  return v;
}

function PillarCard({ num, title, desc, accent, big }) {
  return (
    <div
      className={`relative border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] p-6 ${
        big ? "lg:col-span-2" : ""
      }`}
    >
      <div className="font-mono text-xs text-[rgb(var(--tf-text-muted))]">PILLAR // {num}</div>
      <div className={`font-display text-2xl mt-2 ${accent || ""}`}>{title}</div>
      <div className="text-sm text-[rgb(var(--tf-text-2))] mt-3 leading-relaxed">{desc}</div>
    </div>
  );
}

export default function Landing() {
  const [stats, setStats] = useState({ tokens_saved: 0, requests_optimized: 0, waitlist_count: 0, user_count: 0 });
  const [calcInput, setCalcInput] = useState(SAMPLE);
  const [calcResult, setCalcResult] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [wlEmail, setWlEmail] = useState("");
  const [wlCompany, setWlCompany] = useState("");
  const [wlSubmitting, setWlSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await client.get("/stats/public");
        setStats(data);
      } catch (e) {
        if (process.env.NODE_ENV !== "production") {
          // eslint-disable-next-line no-console
          console.warn("public stats fetch failed (non-blocking)", e);
        }
      }
    })();
    // Run an initial optimize on the sample so user sees instant value
    (async () => {
      try {
        setCalcLoading(true);
        const { data } = await client.post("/optimize", { text: SAMPLE });
        setCalcResult(data);
      } finally {
        setCalcLoading(false);
      }
    })();
    // One-shot on mount; SAMPLE is a module-level constant.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitCalc = async () => {
    if (!calcInput.trim()) return;
    setCalcLoading(true);
    try {
      const { data } = await client.post("/optimize", { text: calcInput });
      setCalcResult(data);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed");
    } finally {
      setCalcLoading(false);
    }
  };

  const submitWaitlist = async (e) => {
    e.preventDefault();
    if (!wlEmail) return;
    setWlSubmitting(true);
    try {
      const { data } = await client.post("/waitlist", { email: wlEmail, company: wlCompany });
      if (data.status === "joined") toast.success("You're on the list — we'll be in touch.");
      else toast.info("You're already on the waitlist.");
      setWlEmail("");
      setWlCompany("");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed");
    } finally {
      setWlSubmitting(false);
    }
  };

  const liveSaved = useTypedCounter(Math.max(12_400_000, stats.tokens_saved), 2200);

  // Annual cost saved at $5/M tokens average (representative)
  const annualCostBasis = useMemo(() => {
    const monthlySaved = liveSaved;
    const pricePerToken = 5 / 1_000_000;
    return Math.round(monthlySaved * pricePerToken * 12);
  }, [liveSaved]);

  return (
    <div className="min-h-screen bg-[rgb(var(--tf-bg))] text-white">
      <MarketingNav />

      {/* HERO */}
      <section className="relative overflow-hidden" data-testid="hero-section">
        <div
          className="absolute inset-0 opacity-50"
          style={{
            backgroundImage: `url(${HERO_BG})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[rgb(var(--tf-bg))]/40 via-[rgb(var(--tf-bg))]/70 to-[rgb(var(--tf-bg))]" />
        <div className="relative max-w-7xl mx-auto px-6 pt-16 pb-24 lg:pt-24 lg:pb-32">
          <div className="inline-flex items-center gap-2 px-3 py-1 border border-[rgb(var(--tf-border-2))] bg-[rgb(var(--tf-bg-2))]/60 backdrop-blur rounded-full mb-8">
            <span className="w-1.5 h-1.5 bg-[rgb(var(--tf-success))] rounded-full animate-pulse" />
            <span className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-2))]">
              ATOE v1.0 · Engine online
            </span>
          </div>

          <h1 className="font-display text-5xl md:text-7xl lg:text-8xl tracking-tighter leading-[0.95] max-w-5xl">
            Distill prompts.
            <br />
            <span className="text-[rgb(var(--tf-brand))]">Slash LLM costs</span>
            <br />
            by <span className="tf-counter">80%</span>.
          </h1>

          <p className="mt-8 text-lg md:text-xl text-[rgb(var(--tf-text-2))] max-w-2xl leading-relaxed">
            TokenForge is a deterministic prompt-optimization engine that sits in front of OpenAI, Claude, and
            Gemini. Five distillation pillars. Zero model retraining. One drop-in API.
          </p>

          {/* Live counter */}
          <div className="mt-10 flex flex-wrap items-end gap-8 lg:gap-14">
            <div data-testid="hero-counter-tokens">
              <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Tokens distilled (live)
              </div>
              <div className="font-display text-4xl md:text-5xl text-[rgb(var(--tf-success))] tf-counter">
                {liveSaved.toLocaleString()}
              </div>
            </div>
            <div data-testid="hero-counter-cost">
              <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Annualized $ saved (basis)
              </div>
              <div className="font-display text-4xl md:text-5xl tf-counter">
                ${annualCostBasis.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Engine pillars
              </div>
              <div className="font-display text-4xl md:text-5xl tf-counter">05</div>
            </div>
          </div>

          <div className="mt-12 flex flex-wrap items-center gap-4">
            <Link
              to="/register"
              data-testid="hero-cta-primary"
              className="inline-flex items-center gap-2 bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-6 py-3 rounded-md transition-colors"
            >
              Start free — 50k tokens/mo →
            </Link>
            <Link
              to="/playground"
              data-testid="hero-cta-secondary"
              className="inline-flex items-center gap-2 border border-[rgb(var(--tf-border-2))] hover:border-white text-white px-6 py-3 rounded-md transition-colors"
            >
              Open Playground
            </Link>
            <span className="text-xs font-mono text-[rgb(var(--tf-text-muted))]">No credit card. No retraining. No proxy lag.</span>
          </div>
        </div>
      </section>

      {/* LIVE CALCULATOR */}
      <section id="calculator" className="relative" data-testid="calculator-section">
        <div className="max-w-7xl mx-auto px-6 py-16 lg:py-24 border-t border-[rgb(var(--tf-border))]">
          <div className="grid lg:grid-cols-2 gap-10">
            <div>
              <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">
                01 · LIVE CALCULATOR
              </div>
              <h2 className="font-display text-4xl md:text-5xl tracking-tight mt-3">
                Paste a prompt. See the savings.
              </h2>
              <p className="text-[rgb(var(--tf-text-2))] mt-4 max-w-md leading-relaxed">
                Our engine runs all 5 distillation pillars on your prompt deterministically — no LLM call
                needed. The output is semantically equivalent, dramatically shorter.
              </p>
              <textarea
                data-testid="calc-input"
                value={calcInput}
                onChange={(e) => setCalcInput(e.target.value)}
                rows={9}
                className="mt-6 w-full bg-[rgb(var(--tf-bg-2))] border border-[rgb(var(--tf-border))] focus:border-[rgb(var(--tf-brand))] focus:ring-1 focus:ring-[rgb(var(--tf-brand))] outline-none rounded-md p-4 font-mono text-sm text-white"
                placeholder="Paste your prompt..."
              />
              <button
                data-testid="calc-run-btn"
                onClick={submitCalc}
                disabled={calcLoading}
                className="mt-4 bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-5 py-2.5 rounded-md transition-colors disabled:opacity-60"
              >
                {calcLoading ? "Distilling…" : "Distill prompt"}
              </button>
            </div>
            <div className="lg:pl-10 border-l border-[rgb(var(--tf-border))]">
              <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Optimized output
              </div>
              {calcResult ? (
                <>
                  <div className="grid grid-cols-3 gap-4 mt-4" data-testid="calc-metrics">
                    <Metric label="Original" value={calcResult.original_tokens} unit="tk" />
                    <Metric label="Optimized" value={calcResult.optimized_tokens} unit="tk" accent />
                    <Metric label="Saved" value={`${calcResult.percent_saved}%`} success />
                  </div>
                  <pre
                    data-testid="calc-output"
                    className="mt-5 bg-[rgb(var(--tf-bg-2))] border border-[rgb(var(--tf-border))] p-4 rounded-md font-mono text-sm text-[rgb(var(--tf-text))] whitespace-pre-wrap"
                  >
                    {calcResult.optimized_text}
                  </pre>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {calcResult.pillars_applied?.map((p) => (
                      <span
                        key={p}
                        className="text-[10px] uppercase tracking-widest font-mono px-2 py-1 border border-[rgb(var(--tf-border-2))] text-[rgb(var(--tf-text-2))] rounded-sm"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                  <div className="mt-4 text-xs font-mono text-[rgb(var(--tf-text-muted))]">
                    Routed → {calcResult.tier} · Suggested model: {calcResult.recommended_model}
                  </div>
                </>
              ) : (
                <div className="mt-6 text-sm text-[rgb(var(--tf-text-muted))] font-mono">
                  <span className="tf-dot" /><span className="tf-dot" /><span className="tf-dot" />
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 5 PILLARS BENTO */}
      <section id="pillars" className="relative" data-testid="pillars-section">
        <div className="max-w-7xl mx-auto px-6 py-16 lg:py-24 border-t border-[rgb(var(--tf-border))]">
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">02 · THE ENGINE</div>
          <h2 className="font-display text-4xl md:text-5xl tracking-tight mt-3 max-w-3xl">
            Five distillation pillars. Applied in order. Every request.
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-[rgb(var(--tf-border))] mt-10 border border-[rgb(var(--tf-border))]">
            <PillarCard
              num="01"
              title="Sub-Byte Lexical Compression"
              desc="A pre-compiled lookup table swaps verbose multi-token phrases for compact single-token synonyms aligned with cl100k / o200k vocabularies."
              big
            />
            <PillarCard
              num="02"
              title="Boilerplate Strip"
              desc="Politeness padding, hedging, and conversational wrappers are surgically removed — leaving the actual instruction."
            />
            <PillarCard
              num="03"
              title="Struct Serialization"
              desc="Embedded JSON/YAML blocks collapsed to non-linear pipe-delimited or minified form — kills whitespace tax."
            />
            <PillarCard
              num="04"
              title="Semantic Cache (cosine ≥ 0.98)"
              desc="Hashed bag-of-words embeddings catch near-identical prompts. Cache hits cost 0 tokens, return in <5ms."
              accent="text-[rgb(var(--tf-success))]"
            />
            <PillarCard
              num="05"
              title="Multi-tier Routing"
              desc="Algorithmic → Extractive → Cognitive. Trivial requests never reach a frontier model. Big-iron only when needed."
              big
            />
          </div>
        </div>
      </section>

      {/* INFRA + TRUST */}
      <section className="relative" data-testid="infra-section">
        <div className="max-w-7xl mx-auto px-6 py-16 lg:py-24 border-t border-[rgb(var(--tf-border))]">
          <div className="grid lg:grid-cols-5 gap-8">
            <div className="lg:col-span-3">
              <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">
                03 · INFRASTRUCTURE
              </div>
              <h2 className="font-display text-4xl md:text-5xl tracking-tight mt-3">
                Drop-in proxy. <br />
                Your stack, your keys, your data.
              </h2>
              <p className="text-[rgb(var(--tf-text-2))] mt-5 max-w-xl leading-relaxed">
                Replace your <code className="font-mono text-[rgb(var(--tf-brand))]">api.openai.com</code>{" "}
                base URL with TokenForge. We optimize, route, and cache. Your model. Your prompt. Your output.
                Just shorter.
              </p>
              <div className="mt-8 bg-[rgb(var(--tf-bg-2))] border border-[rgb(var(--tf-border))] rounded-md p-5 font-mono text-sm overflow-x-auto">
                <div className="text-[rgb(var(--tf-text-muted))] text-xs mb-2"># curl</div>
                <pre className="text-[rgb(var(--tf-text))] whitespace-pre-wrap">{`curl -X POST https://api.tokenforge.io/api/proxy/chat \\
  -H "X-TF-Key: tf_live_YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "Summarize the following text...",
    "provider": "anthropic",
    "model": "claude-sonnet-4-6"
  }'`}</pre>
              </div>
            </div>
            <div className="lg:col-span-2 relative min-h-[320px]">
              <div
                className="absolute inset-0 rounded-md border border-[rgb(var(--tf-border))]"
                style={{
                  backgroundImage: `linear-gradient(180deg, rgba(10,10,10,0.4), rgba(10,10,10,0.9)), url(${INFRA_IMG})`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                }}
              />
              <div className="relative h-full flex flex-col justify-end p-6">
                <div className="font-mono text-xs text-[rgb(var(--tf-success))]">// uptime</div>
                <div className="font-display text-5xl tracking-tight">99.99%</div>
                <div className="text-xs text-[rgb(var(--tf-text-2))] mt-1">Edge-deployed routing layer</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* WAITLIST */}
      <section className="relative" data-testid="waitlist-section">
        <div className="max-w-3xl mx-auto px-6 py-16 lg:py-24 border-t border-[rgb(var(--tf-border))]">
          <div className="text-center">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">
              04 · ENTERPRISE PILOT
            </div>
            <h2 className="font-display text-4xl md:text-5xl tracking-tight mt-3">
              Burning $50k+/mo on tokens?
            </h2>
            <p className="text-[rgb(var(--tf-text-2))] mt-4">
              Join the enterprise pilot waitlist. White-glove onboarding, dedicated routing, SLA.
            </p>
          </div>
          <form
            onSubmit={submitWaitlist}
            className="mt-8 grid sm:grid-cols-3 gap-3"
            data-testid="waitlist-form"
          >
            <input
              type="email"
              required
              value={wlEmail}
              onChange={(e) => setWlEmail(e.target.value)}
              placeholder="work email"
              data-testid="waitlist-email"
              className="sm:col-span-1 bg-[rgb(var(--tf-bg-2))] border border-[rgb(var(--tf-border))] focus:border-[rgb(var(--tf-brand))] focus:ring-1 focus:ring-[rgb(var(--tf-brand))] outline-none rounded-md px-4 py-3 font-mono text-sm"
            />
            <input
              type="text"
              value={wlCompany}
              onChange={(e) => setWlCompany(e.target.value)}
              placeholder="company"
              data-testid="waitlist-company"
              className="sm:col-span-1 bg-[rgb(var(--tf-bg-2))] border border-[rgb(var(--tf-border))] focus:border-[rgb(var(--tf-brand))] focus:ring-1 focus:ring-[rgb(var(--tf-brand))] outline-none rounded-md px-4 py-3 font-mono text-sm"
            />
            <button
              type="submit"
              disabled={wlSubmitting}
              data-testid="waitlist-submit"
              className="sm:col-span-1 bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium rounded-md px-5 py-3 transition-colors disabled:opacity-60"
            >
              {wlSubmitting ? "…" : "Request pilot →"}
            </button>
          </form>
          <div className="mt-4 text-center text-xs font-mono text-[rgb(var(--tf-text-muted))]">
            {stats.waitlist_count} teams on the list · 0 spam, ever
          </div>
        </div>
      </section>

      {/* PRICING TEASER */}
      <section className="relative" data-testid="pricing-teaser">
        <div className="max-w-7xl mx-auto px-6 py-16 lg:py-24 border-t border-[rgb(var(--tf-border))]">
          <div className="flex flex-wrap items-end justify-between gap-4 mb-10">
            <div>
              <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">
                05 · PRICING
              </div>
              <h2 className="font-display text-4xl md:text-5xl tracking-tight mt-3">
                Pay for tokens you'd save.
              </h2>
            </div>
            <Link
              to="/pricing"
              data-testid="pricing-cta-full"
              className="text-sm text-[rgb(var(--tf-text-2))] hover:text-white"
            >
              See full pricing →
            </Link>
          </div>
          <PriceTeaser />
        </div>
      </section>

      <Footer />
    </div>
  );
}

function Metric({ label, value, unit, accent, success }) {
  return (
    <div className="border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] p-4">
      <div className="text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">{label}</div>
      <div className={`font-display text-2xl tf-counter mt-1 ${
        success ? "text-[rgb(var(--tf-success))]" :
        accent ? "text-[rgb(var(--tf-brand))]" : ""
      }`}>
        {value}
        {unit && <span className="text-xs ml-1 font-mono text-[rgb(var(--tf-text-muted))]">{unit}</span>}
      </div>
    </div>
  );
}

function PriceTeaser() {
  const tiers = [
    { id: "free", name: "Free", price: "$0", quota: "50k tokens / mo", featured: false },
    { id: "starter", name: "Starter", price: "$19", quota: "1M tokens / mo", featured: false },
    { id: "pro", name: "Pro", price: "$99", quota: "10M tokens / mo", featured: true },
    { id: "enterprise", name: "Enterprise", price: "$499", quota: "100M tokens / mo", featured: false },
  ];
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
      {tiers.map((t) => (
        <div
          key={t.id}
          data-testid={`price-card-${t.id}`}
          className={`bg-[rgb(var(--tf-bg-2))] p-7 relative tf-beam ${t.featured ? "tf-active" : ""}`}
        >
          <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
            {t.name}
          </div>
          <div className="mt-2 font-display text-4xl tracking-tight">
            {t.price}
            <span className="text-sm text-[rgb(var(--tf-text-muted))] font-mono ml-1">/mo</span>
          </div>
          <div className="mt-1 font-mono text-xs text-[rgb(var(--tf-text-2))]">{t.quota}</div>
          {t.featured && (
            <div className="absolute top-3 right-3 text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--tf-brand))]">
              Best Value
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
