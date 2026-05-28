import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import client, { BACKEND_URL } from "@/lib/api";
import { MarketingNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

export default function Share() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [showEmbed, setShowEmbed] = useState(false);
  const [theme, setTheme] = useState("dark");

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

  const snippet = useMemo(
    () =>
      `<script src="${BACKEND_URL}/api/widget.js"\n        data-tf-slug="${slug}"\n        data-tf-theme="${theme}"\n        async defer></script>`,
    [slug, theme]
  );

  const copySnippet = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      toast.success("Embed snippet copied to clipboard");
    } catch {
      toast.error("Copy failed — select & copy manually");
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <MarketingNav />
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-16">
        {err ? (
          <div data-testid="share-error" className="text-center py-24">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-error))]">{err}</div>
            <div className="font-display text-3xl mt-3 tracking-tight">This share link doesn't exist.</div>
            <p className="text-[rgb(var(--tf-text-2))] mt-3 max-w-md mx-auto">
              Maybe it was revoked, or you mistyped. Want your own savings dashboard?
            </p>
            <div className="mt-6 flex items-center justify-center gap-3">
              <Link
                to="/"
                className="border border-[rgb(var(--tf-border-2))] hover:border-white text-white px-5 py-2.5 rounded-md text-sm transition-colors"
              >
                ← Home
              </Link>
              <Link
                to="/register"
                className="bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-5 py-2.5 rounded-md text-sm transition-colors"
              >
                Start saving free →
              </Link>
            </div>
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
              {data.tokens_saved > 0 && (
                <button
                  data-testid="share-tweet"
                  onClick={tweet}
                  className="bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-6 py-3 rounded-md transition-colors"
                >
                  Tweet your savings →
                </button>
              )}
              <button
                data-testid="share-embed-btn"
                onClick={() => setShowEmbed((v) => !v)}
                className="border border-[rgb(var(--tf-border-2))] hover:border-[rgb(var(--tf-success))] hover:text-[rgb(var(--tf-success))] text-white px-6 py-3 rounded-md transition-colors"
              >
                {showEmbed ? "Hide embed snippet ↑" : "Embed this widget →"}
              </button>
              <Link
                to="/register"
                data-testid="share-cta-signup"
                className="border border-[rgb(var(--tf-border-2))] hover:border-white text-white px-6 py-3 rounded-md transition-colors"
              >
                Start saving — free →
              </Link>
            </div>

            {showEmbed && (
              <div
                data-testid="embed-snippet-panel"
                className="mt-8 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] rounded-md overflow-hidden"
              >
                <div className="px-5 py-3 border-b border-[rgb(var(--tf-border))] flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-widest text-[rgb(var(--tf-brand))]">
                      ONE-LINE EMBED · SHIP TO ANY SITE
                    </div>
                    <div className="text-sm text-[rgb(var(--tf-text-2))] mt-1">
                      Drop this <code className="font-mono text-[rgb(var(--tf-brand))]">&lt;script&gt;</code> into Notion, Webflow, your blog, your README — it renders a live counter that updates from this share link.
                    </div>
                  </div>
                  <div className="flex items-center gap-1 p-1 border border-[rgb(var(--tf-border))] rounded-md">
                    <button
                      data-testid="embed-theme-dark"
                      onClick={() => setTheme("dark")}
                      className={`px-3 py-1 text-[10px] font-mono uppercase tracking-widest rounded-sm transition-colors ${
                        theme === "dark"
                          ? "bg-[rgb(var(--tf-bg-3))] text-white"
                          : "text-[rgb(var(--tf-text-2))] hover:text-white"
                      }`}
                    >
                      Dark
                    </button>
                    <button
                      data-testid="embed-theme-light"
                      onClick={() => setTheme("light")}
                      className={`px-3 py-1 text-[10px] font-mono uppercase tracking-widest rounded-sm transition-colors ${
                        theme === "light"
                          ? "bg-[rgb(var(--tf-bg-3))] text-white"
                          : "text-[rgb(var(--tf-text-2))] hover:text-white"
                      }`}
                    >
                      Light
                    </button>
                  </div>
                </div>
                <div className="p-5 grid lg:grid-cols-2 gap-5">
                  <div>
                    <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))] mb-2">
                      Snippet
                    </div>
                    <pre
                      data-testid="embed-snippet-code"
                      className="bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] p-4 rounded-md font-mono text-xs whitespace-pre overflow-x-auto"
                    >
                      {snippet}
                    </pre>
                    <button
                      data-testid="embed-copy-btn"
                      onClick={copySnippet}
                      className="mt-3 bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-4 py-2 rounded-md text-xs transition-colors"
                    >
                      Copy snippet
                    </button>
                  </div>
                  <div>
                    <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))] mb-2">
                      Live preview
                    </div>
                    <iframe
                      key={`${slug}-${theme}`}
                      data-testid="embed-preview-iframe"
                      title="TokenForge widget preview"
                      src={`${BACKEND_URL}/api/embed/${slug}?theme=${theme}`}
                      style={{
                        width: "100%",
                        minHeight: "200px",
                        border: 0,
                        background: theme === "light" ? "#fff" : "transparent",
                        borderRadius: "6px",
                      }}
                      sandbox="allow-scripts allow-same-origin allow-popups"
                    />
                    <div className="mt-3 text-[10px] font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
                      Auto-resizes to fit · refreshes from /api/share/savings
                    </div>
                  </div>
                </div>
              </div>
            )}

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
