import React, { useState } from "react";
import client, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { MarketingNav, DashboardNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

const SAMPLES = [
  `In order to please help me, I would really like you to summarize the following information about artificial intelligence as well as machine learning, if you don't mind. Thank you in advance.`,
  `Hello! Could you kindly extract the following information from this text and return it as JSON: name, email, phone. The text is below.`,
  `As an AI assistant, I would like to ask you to write a basic fundamental explanation of how large language models work, with reference to neural networks and transformers.`,
];

export default function Playground() {
  const { user } = useAuth();
  const [input, setInput] = useState(SAMPLES[0]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const { data } = await client.post("/optimize", { text: input });
      setResult(data);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed");
    } finally {
      setLoading(false);
    }
  };

  const Nav = user ? DashboardNav : MarketingNav;

  return (
    <div className="min-h-screen flex flex-col">
      <Nav />
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
          <div>
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">
              PLAYGROUND
            </div>
            <h1 className="font-display text-4xl tracking-tight mt-2">Distillation Playground</h1>
            <p className="text-[rgb(var(--tf-text-2))] mt-2 max-w-xl">
              Paste any prompt to see exactly what the 5-pillar engine does. Deterministic, instant, free.
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            {SAMPLES.map((s, i) => (
              <button
                key={`sample-${i}-${s.length}`}
                data-testid={`pg-sample-${i}`}
                onClick={() => setInput(s)}
                className="text-xs font-mono px-2 py-1 border border-[rgb(var(--tf-border))] hover:border-[rgb(var(--tf-brand))] rounded-sm text-[rgb(var(--tf-text-2))] hover:text-white transition-colors"
              >
                sample_{i + 1}
              </button>
            ))}
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
          <div className="bg-[rgb(var(--tf-bg-2))] p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Original prompt
              </div>
              {result && (
                <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))]">
                  {result.original_tokens} tk
                </div>
              )}
            </div>
            <textarea
              data-testid="pg-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={14}
              className="w-full bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] focus:border-[rgb(var(--tf-brand))] focus:ring-1 focus:ring-[rgb(var(--tf-brand))] outline-none rounded-md p-4 font-mono text-sm"
            />
            <button
              data-testid="pg-run"
              onClick={run}
              disabled={loading}
              className="mt-4 bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-5 py-2.5 rounded-md transition-colors disabled:opacity-60"
            >
              {loading ? "Distilling…" : "Distill →"}
            </button>
          </div>

          <div className="bg-[rgb(var(--tf-bg-2))] p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                Optimized output
              </div>
              {result && (
                <div className="text-xs font-mono text-[rgb(var(--tf-success))]">
                  {result.optimized_tokens} tk · −{result.percent_saved}%
                </div>
              )}
            </div>
            {result ? (
              <>
                <pre
                  data-testid="pg-output"
                  className="bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] rounded-md p-4 font-mono text-sm whitespace-pre-wrap min-h-[280px]"
                >
                  {result.optimized_text}
                </pre>
                <div className="mt-4 grid grid-cols-3 gap-2">
                  <Mini label="Saved" value={`${result.tokens_saved} tk`} success />
                  <Mini label="Tier" value={result.tier} />
                  <Mini label="Model" value={result.recommended_model.split(" ")[0]} />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {result.pillars_applied?.map((p) => (
                    <span
                      key={p}
                      className="text-[10px] uppercase tracking-widest font-mono px-2 py-1 border border-[rgb(var(--tf-border-2))] text-[rgb(var(--tf-text-2))] rounded-sm"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-sm text-[rgb(var(--tf-text-muted))] font-mono py-20 text-center">
                press Distill →
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function Mini({ label, value, success }) {
  return (
    <div className="border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-3))] p-2">
      <div className="text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">{label}</div>
      <div className={`font-mono text-sm mt-0.5 ${success ? "text-[rgb(var(--tf-success))]" : ""}`}>{value}</div>
    </div>
  );
}
