import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import client from "@/lib/api";
import { MarketingNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

const SHARE_COPY = [
  "I've been saving tokens with TokenForge — get 500K free when you sign up via my link:",
  "Stop paying full price for LLM tokens. TokenForge's semantic cache cuts costs by 40-70%.",
  "Building with AI? I'm using TokenForge to proxy OpenAI/Anthropic at a fraction of the cost.",
];

export default function Refer() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (user) {
      client.get("/referrals/me").then(({ data }) => setStats(data)).catch(() => {});
    }
  }, [user]);

  const referralUrl = user
    ? `${window.location.origin}/register?ref=${user.id}`
    : null;

  const copy = () => {
    if (!referralUrl) return;
    navigator.clipboard.writeText(referralUrl).then(() => {
      setCopied(true);
      toast.success("Link copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const tweet = () => {
    const msg = encodeURIComponent(`${SHARE_COPY[0]}\n\n${referralUrl}\n\n#AI #LLM #DevTools`);
    window.open(`https://twitter.com/intent/tweet?text=${msg}`, "_blank");
  };

  const hnShare = () => {
    const title = encodeURIComponent("TokenForge – LLM proxy with semantic caching, 40-70% token savings");
    const url = encodeURIComponent(referralUrl || window.location.origin);
    window.open(`https://news.ycombinator.com/submitlink?u=${url}&t=${title}`, "_blank");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <MarketingNav />
      <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-16">
        {/* Hero */}
        <div className="text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 border border-[rgb(var(--tf-success))] rounded-full text-xs font-mono text-[rgb(var(--tf-success))] mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-[rgb(var(--tf-success))] inline-block" />
            REFERRAL PROGRAM — LIVE
          </div>
          <h1 className="font-display text-5xl tracking-tight">
            Earn 500K tokens<br />per referral.
          </h1>
          <p className="text-[rgb(var(--tf-text-2))] mt-4 text-lg">
            Share your link. When a developer signs up, you both get{" "}
            <span className="text-white font-medium">500,000 bonus tokens</span> — no expiry, no strings.
          </p>
        </div>

        {/* Stats bar (authenticated) */}
        {user && stats && (
          <div className="mt-10 grid grid-cols-3 gap-px bg-[rgb(var(--tf-border))] border border-[rgb(var(--tf-border))] rounded-md overflow-hidden">
            {[
              { label: "Referrals", value: stats.referrals_count },
              { label: "Tokens Earned", value: (stats.referrals_count * stats.bonus_per_referral).toLocaleString() },
              { label: "Bonus / Referral", value: (stats.bonus_per_referral / 1000).toFixed(0) + "K" },
            ].map((s) => (
              <div key={s.label} className="bg-[rgb(var(--tf-bg-2))] px-6 py-5 text-center">
                <div className="font-display text-3xl tracking-tight text-[rgb(var(--tf-brand))]">{s.value}</div>
                <div className="text-xs font-mono text-[rgb(var(--tf-text-muted))] mt-1 uppercase tracking-widest">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Referral link box */}
        {user ? (
          <div className="mt-8 p-6 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] rounded-md">
            <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))] mb-3">Your referral link</div>
            <div className="flex gap-2">
              <input
                readOnly
                value={referralUrl}
                onClick={(e) => e.target.select()}
                className="flex-1 bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] text-[rgb(var(--tf-text-2))] font-mono text-sm px-3 py-2 rounded-md focus:outline-none"
              />
              <button
                onClick={copy}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  copied
                    ? "bg-[rgb(var(--tf-success))] text-black"
                    : "bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black"
                }`}
              >
                {copied ? "Copied ✓" : "Copy"}
              </button>
            </div>

            <div className="mt-4 flex gap-2">
              <button
                onClick={tweet}
                className="flex items-center gap-2 px-4 py-2 border border-[rgb(var(--tf-border))] hover:border-white rounded-md text-sm transition-colors"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.737-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                Share on X
              </button>
              <button
                onClick={hnShare}
                className="flex items-center gap-2 px-4 py-2 border border-[rgb(var(--tf-border))] hover:border-white rounded-md text-sm transition-colors"
              >
                <span className="text-[rgb(var(--tf-brand))] font-bold text-sm">Y</span>
                Post to HN
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-10 p-8 border border-[rgb(var(--tf-brand))] bg-[rgba(var(--tf-brand),0.05)] rounded-md text-center">
            <p className="text-[rgb(var(--tf-text-2))] mb-6">
              Sign up free to get your referral link and start earning bonus tokens.
            </p>
            <div className="flex justify-center gap-3">
              <Link to="/register" className="bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-6 py-2.5 rounded-md transition-colors">
                Create free account →
              </Link>
              <Link to="/login" className="border border-[rgb(var(--tf-border))] hover:border-white px-6 py-2.5 rounded-md transition-colors text-sm">
                Sign in
              </Link>
            </div>
          </div>
        )}

        {/* How it works */}
        <div className="mt-16">
          <h2 className="font-display text-2xl tracking-tight mb-8">How it works</h2>
          <div className="space-y-4">
            {[
              ["01", "Share your unique link", "Every signed-in user gets a permanent referral link tied to their account."],
              ["02", "Developer signs up", "When someone registers using your link, the bonus is automatically applied to both accounts."],
              ["03", "Both accounts get +500K tokens", "Tokens are added to your monthly quota immediately — no waiting, no approval."],
              ["04", "No limit on referrals", "Refer 10 devs → earn 5M tokens. There's no cap."],
            ].map(([n, title, desc]) => (
              <div key={n} className="flex gap-5 items-start p-5 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] rounded-md">
                <span className="font-mono text-2xl text-[rgb(var(--tf-brand))] shrink-0 w-8">{n}</span>
                <div>
                  <div className="font-medium text-white">{title}</div>
                  <div className="text-sm text-[rgb(var(--tf-text-2))] mt-1">{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Social proof nudge */}
        <div className="mt-16 p-6 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] rounded-md">
          <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))] mb-4">Spread the word</div>
          <div className="space-y-2">
            {SHARE_COPY.map((line) => (
              <div key={line} className="text-sm text-[rgb(var(--tf-text-2))] font-mono bg-[rgb(var(--tf-bg-3))] px-3 py-2 rounded border border-[rgb(var(--tf-border))]">
                "{line}"
              </div>
            ))}
          </div>
          <p className="text-xs text-[rgb(var(--tf-text-muted))] mt-3">Copy any message above + your link and post anywhere devs hang out.</p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
