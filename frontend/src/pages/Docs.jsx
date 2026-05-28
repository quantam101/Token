import React, { useState } from "react";
import { useAuth } from "@/lib/auth";
import { MarketingNav, DashboardNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

const SAMPLE_KEY = "tf_live_YOUR_API_KEY_HERE";

const CURL_SAMPLE = (origin, key) => `curl -X POST ${origin}/api/proxy/chat \\
  -H "X-TF-Key: ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "Summarize the article below in 3 bullet points...",
    "system": "You are a concise summarizer.",
    "provider": "anthropic",
    "model": "claude-sonnet-4-6"
  }'`;

const PY_SAMPLE = (origin, key) => `import requests

resp = requests.post(
    "${origin}/api/proxy/chat",
    headers={"X-TF-Key": "${key}"},
    json={
        "prompt": "Summarize the article below in 3 bullet points...",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
    },
)
data = resp.json()
print(data["response"])
print(f"Saved {data['tokens']['saved']} tokens / ${'{'}data['cost_saved_usd']{'}'}")`;

const JS_SAMPLE = (origin, key) => `const res = await fetch("${origin}/api/proxy/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-TF-Key": "${key}",
  },
  body: JSON.stringify({
    prompt: "Summarize the article below in 3 bullet points...",
    provider: "anthropic",
    model: "claude-sonnet-4-6",
  }),
});
const data = await res.json();
console.log(data.response);
console.log(\`Saved \${data.tokens.saved} tokens (\$\${data.cost_saved_usd})\`);`;

export default function Docs() {
  const { user } = useAuth();
  const Nav = user ? DashboardNav : MarketingNav;
  const origin = typeof window !== "undefined" ? window.location.origin : "https://tokenforge.io";
  const key = SAMPLE_KEY;
  const [tab, setTab] = useState("curl");

  const samples = {
    curl: { lang: "bash", code: CURL_SAMPLE(origin, key) },
    python: { lang: "python", code: PY_SAMPLE(origin, key) },
    js: { lang: "javascript", code: JS_SAMPLE(origin, key) },
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Nav />
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-10 grid lg:grid-cols-[220px_1fr] gap-10">
        <aside className="lg:sticky lg:top-24 lg:self-start text-sm space-y-1">
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))] mb-2">
            DOCS
          </div>
          <DocLink href="#quickstart">Quickstart</DocLink>
          <DocLink href="#auth">Authentication</DocLink>
          <DocLink href="#proxy">/proxy/chat</DocLink>
          <DocLink href="#optimize">/optimize</DocLink>
          <DocLink href="#models">Supported models</DocLink>
          <DocLink href="#errors">Errors</DocLink>
        </aside>

        <article className="prose prose-invert max-w-none">
          <header className="mb-10">
            <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-brand))]">
              API REFERENCE · v1
            </div>
            <h1 className="font-display text-5xl tracking-tight mt-2 m-0">TokenForge API</h1>
            <p className="text-[rgb(var(--tf-text-2))] mt-3">
              One drop-in endpoint. Your model. Your prompt. We distill and route.
            </p>
          </header>

          <Section id="quickstart" title="Quickstart">
            <ol className="text-[rgb(var(--tf-text-2))] space-y-2 list-decimal pl-5">
              <li>Create an account — you get an API key instantly.</li>
              <li>Replace your provider call with a single POST to <code className="font-mono text-[rgb(var(--tf-brand))]">/api/proxy/chat</code>.</li>
              <li>Pass <code className="font-mono">X-TF-Key</code> header. Optionally choose provider/model.</li>
              <li>Watch tokens-saved climb in your dashboard.</li>
            </ol>
            <div className="mt-6 border border-[rgb(var(--tf-border))] rounded-md overflow-hidden">
              <div className="flex border-b border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))]">
                {["curl", "python", "js"].map((t) => (
                  <button
                    key={t}
                    data-testid={`docs-tab-${t}`}
                    onClick={() => setTab(t)}
                    className={`px-4 py-2 text-xs font-mono uppercase tracking-widest ${
                      tab === t ? "text-white border-b-2 border-[rgb(var(--tf-brand))]" : "text-[rgb(var(--tf-text-2))]"
                    }`}
                  >
                    {t}
                  </button>
                ))}
                <div className="ml-auto flex items-center px-3">
                  <button
                    data-testid="docs-copy"
                    onClick={() => {
                      navigator.clipboard.writeText(samples[tab].code);
                      toast.success("Copied");
                    }}
                    className="text-xs font-mono text-[rgb(var(--tf-brand))] hover:underline"
                  >
                    copy
                  </button>
                </div>
              </div>
              <pre className="m-0 p-4 bg-[rgb(var(--tf-bg-3))] font-mono text-sm text-[rgb(var(--tf-text))] whitespace-pre overflow-x-auto">
                {samples[tab].code}
              </pre>
            </div>
          </Section>

          <Section id="auth" title="Authentication">
            <p className="text-[rgb(var(--tf-text-2))]">
              All proxy calls require the <code className="font-mono">X-TF-Key</code> header. Keys are created in the{" "}
              <a href="/dashboard/keys" className="text-[rgb(var(--tf-brand))]">Keys dashboard</a>.
            </p>
          </Section>

          <Section id="proxy" title="POST /api/proxy/chat">
            <p className="text-[rgb(var(--tf-text-2))]">
              Distills the prompt, optionally hits the semantic cache, routes to the right model, and returns the model's reply along with token accounting.
            </p>
            <h4 className="font-display text-lg mt-5">Request body</h4>
            <Table rows={[
              ["prompt", "string (required)", "Raw user prompt to distill + send."],
              ["system", "string (optional)", "System prompt. Default: 'You are a helpful assistant.'"],
              ["provider", "openai | anthropic | gemini", "Default: anthropic"],
              ["model", "string", "Model id, e.g. claude-sonnet-4-6"],
              ["optimize", "bool", "Default true. Set false to skip distillation (for benchmarking)."],
            ]} />
            <h4 className="font-display text-lg mt-5">Response</h4>
            <pre className="bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] rounded-md p-4 font-mono text-sm whitespace-pre overflow-x-auto">{`{
  "response": "…model reply…",
  "provider": "anthropic",
  "model": "claude-sonnet-4-6",
  "tier": "cognitive",
  "cache_hit": false,
  "tokens": { "original": 142, "optimized": 58, "completion": 220, "saved": 84 },
  "cost_saved_usd": 0.00042,
  "pillars_applied": ["lexical_compression", "boilerplate_strip", "routing:cognitive"]
}`}</pre>
          </Section>

          <Section id="optimize" title="POST /api/optimize (no auth)">
            <p className="text-[rgb(var(--tf-text-2))]">
              Returns the distilled prompt + metrics without calling any LLM. Use it for benchmarking, dry-runs, and educational tooling.
            </p>
            <pre className="bg-[rgb(var(--tf-bg-3))] border border-[rgb(var(--tf-border))] rounded-md p-4 font-mono text-sm whitespace-pre overflow-x-auto">{`curl -X POST ${origin}/api/optimize \\
  -H "Content-Type: application/json" \\
  -d '{"text":"Your verbose prompt here..."}'`}</pre>
          </Section>

          <Section id="models" title="Supported models">
            <Table rows={[
              ["openai", "gpt-5.4, gpt-5.4-mini, gpt-4o, gpt-4o-mini", "best for general/code"],
              ["anthropic", "claude-sonnet-4-6, claude-haiku-4-5", "best for reasoning, default"],
              ["gemini", "gemini-3-flash-preview, gemini-3.1-pro-preview", "best for extraction, cheapest"],
            ]} />
          </Section>

          <Section id="errors" title="Errors">
            <Table rows={[
              ["401", "Missing or invalid X-TF-Key"],
              ["400", "Validation error (see detail)"],
              ["502", "Upstream LLM provider error"],
            ]} />
          </Section>
        </article>
      </main>
      <Footer />
    </div>
  );
}

function DocLink({ href, children }) {
  return (
    <a
      href={href}
      className="block px-2 py-1 rounded-sm text-[rgb(var(--tf-text-2))] hover:text-white hover:bg-[rgb(var(--tf-bg-2))] font-mono text-sm"
    >
      {children}
    </a>
  );
}

function Section({ id, title, children }) {
  return (
    <section id={id} className="scroll-mt-24 mb-12">
      <h2 className="font-display text-3xl tracking-tight border-b border-[rgb(var(--tf-border))] pb-2 m-0">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Table({ rows }) {
  return (
    <div className="overflow-x-auto border border-[rgb(var(--tf-border))] rounded-md">
      <table className="w-full font-mono text-sm">
        <tbody>
          {rows.map((r, i) => (
            <tr key={`${r[0]}-${i}`} className={i ? "border-t border-[rgb(var(--tf-border))]" : ""}>
              {r.map((c, j) => (
                <td key={`${r[0]}-${j}`} className={`px-4 py-2 ${j === 0 ? "text-[rgb(var(--tf-brand))] whitespace-nowrap" : "text-[rgb(var(--tf-text-2))]"}`}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
