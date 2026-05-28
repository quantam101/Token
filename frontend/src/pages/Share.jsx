import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import client from "@/lib/api";
import { MarketingNav, Footer } from "@/components/Nav";

export default function Share() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    client
      .get(`/share/savings/${slug}`)
      .then(({ data }) => setData(data))
      .catch((e) => setErr(e.response?.status === 404 ? "Link not found" : "Failed to load"));
  }, [slug]);

  const tweet = () => {
    if (!data) return;
    const msg = `I've saved ${data.tokens_saved.toLocaleString()} tokens ($${data.cost_saved_usd}) on LLM costs with @TokenForge_io — averaging ${data.avg_compression_pct}% prompt compression. ${window.location.href}`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(msg)}`, "_blank");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <MarketingNav />
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-16">
        {err ? (
          <div data-testid="share-error" className="text-center text-[rgb(var(--tf-text-2))] font-mono py-24">
            {err}
          </div>
        ) : !data ? (
          <div className="text-center text-[rgb(var(--tf-text-muted))] font-mono py-24">
            <span className="tf-dot" /><span className="tf-dot" /><span className="tf-dot" />
          </div>
        ) : (
          <div data-testid="share-content">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">
              PUBLIC RECEIPT
            </div>
            <h1 className="font-display text-5xl md:text-6xl tracking-tighter mt-3 leading-[1.05]">
              {data.display_name} has saved
              <br />
              <span className="text-[rgb(var(--tf-success))]" data-testid="share-tokens">
                {data.tokens_saved.toLocaleString()}
              </span>{" "}
              tokens
              <br />
              with <span className="text-[rgb(var(--tf-brand))]">TokenForge</span>.
            </h1>

            <div className="mt-10 grid sm:grid-cols-3 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))]">
              <Stat label="$ Saved (lifetime)" value={`$${data.cost_saved_usd}`} accent />
              <Stat label="Requests optimized" value={data.requests.toLocaleString()} />
              <Stat label="Avg compression" value={`${data.avg_compression_pct}%`} success />
            </div>

            <div className="mt-10 flex flex-wrap gap-3">
              <button
                data-testid="share-tweet"
                onClick={tweet}
                className="bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-6 py-3 rounded-md transition-colors"
              >
                Tweet your savings →
              </button>
              <Link
                to="/register"
                data-testid="share-cta-signup"
                className="border border-[rgb(var(--tf-border-2))] hover:border-white text-white px-6 py-3 rounded-md transition-colors"
              >
                Start saving — free →
              </Link>
            </div>

            <div className="mt-12 max-w-xl text-[rgb(var(--tf-text-2))] text-sm leading-relaxed">
              TokenForge is a deterministic prompt-optimization engine that sits in front of OpenAI, Claude,
              and Gemini. Five distillation pillars. Zero model retraining. Drop-in API.
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}

function Stat({ label, value, accent, success }) {
  return (
    <div className="bg-[rgb(var(--tf-bg-2))] p-6">
      <div className="text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">{label}</div>
      <div
        className={`font-display text-3xl mt-2 tf-counter ${
          success ? "text-[rgb(var(--tf-success))]" : accent ? "text-[rgb(var(--tf-brand))]" : ""
        }`}
      >
        {value}
      </div>
    </div>
  );
}
