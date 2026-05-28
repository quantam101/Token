import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import client, { formatApiErrorDetail } from "@/lib/api";
import { DashboardNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

const PROVIDER_META = {
  openai: {
    label: "OpenAI",
    placeholder: "sk-proj-...",
    docs: "https://platform.openai.com/api-keys",
    accent: "#10A37F",
  },
  anthropic: {
    label: "Anthropic",
    placeholder: "sk-ant-api03-...",
    docs: "https://console.anthropic.com/settings/keys",
    accent: "#C97757",
  },
  google: {
    label: "Google Gemini",
    placeholder: "AIza...",
    docs: "https://aistudio.google.com/apikey",
    accent: "#4285F4",
  },
};

export default function LlmKeys() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [state, setState] = useState({
    byok_unlocked: false,
    plan: "free",
    supported_providers: [],
    keys: [],
  });
  const [drafts, setDrafts] = useState({ openai: "", anthropic: "", google: "" });
  const [saving, setSaving] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await client.get("/byok");
      setState(data);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed to load keys");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async (provider) => {
    const apiKey = drafts[provider]?.trim();
    if (!apiKey) {
      toast.error(`Paste your ${PROVIDER_META[provider].label} key first`);
      return;
    }
    setSaving((s) => ({ ...s, [provider]: true }));
    try {
      await client.post("/byok", { provider, api_key: apiKey });
      setDrafts((d) => ({ ...d, [provider]: "" }));
      await load();
      toast.success(`${PROVIDER_META[provider].label} key saved — encrypted at rest`);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Save failed");
    } finally {
      setSaving((s) => ({ ...s, [provider]: false }));
    }
  };

  const remove = async (provider) => {
    if (!window.confirm(`Remove your ${PROVIDER_META[provider].label} key? Calls using it will fall back to TokenForge's default model.`)) return;
    try {
      await client.delete(`/byok/${provider}`);
      await load();
      toast.success("Key removed");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Delete failed");
    }
  };

  const existingForProvider = (provider) =>
    state.keys.find((k) => k.provider === provider);

  return (
    <div className="min-h-screen flex flex-col" data-testid="byok-page">
      <DashboardNav />
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8">
        <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
          BYO KEYS
        </div>
        <h1 className="font-display text-3xl mt-2">Bring Your Own LLM Keys</h1>
        <p className="text-sm text-[rgb(var(--tf-text-2))] mt-2 max-w-2xl">
          Connect your own OpenAI, Anthropic, and Google Gemini API keys. TokenForge proxies your
          calls using <em>your</em> keys, applies semantic caching, and bills you nothing for the
          LLM tokens — you pay your provider directly at their cost.
        </p>

        {/* Plan gate banner */}
        {!state.byok_unlocked && !loading && (
          <div
            className="mt-8 rounded-2xl border border-[rgb(var(--tf-border))] bg-[rgba(255,69,0,0.05)] p-6"
            data-testid="byok-paywall"
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-sm border border-[rgb(var(--tf-brand))] text-[rgb(var(--tf-brand))]">
                PRO FEATURE
              </span>
              <span className="text-sm text-[rgb(var(--tf-text-2))]">
                Currently on the <strong>{state.plan}</strong> plan
              </span>
            </div>
            <h2 className="font-display text-xl mt-4">Unlock BYO Keys with Pro</h2>
            <p className="text-sm text-[rgb(var(--tf-text-2))] mt-2">
              Pro and Enterprise customers can plug in their own provider keys to use OpenAI,
              Anthropic, Claude, and the full Gemini lineup. Free and Starter plans run on TokenForge's
              shared Gemini 2.5 Flash tier (rate-limited).
            </p>
            <button
              onClick={() => navigate("/pricing")}
              data-testid="byok-upgrade-btn"
              className="mt-4 px-5 py-2.5 rounded-md bg-[rgb(var(--tf-brand))] text-black font-mono text-xs uppercase tracking-widest hover:opacity-90 transition-opacity"
            >
              Upgrade to Pro →
            </button>
          </div>
        )}

        {/* Provider key inputs */}
        <div className="mt-8 grid gap-4">
          {Object.keys(PROVIDER_META).map((provider) => {
            const meta = PROVIDER_META[provider];
            const existing = existingForProvider(provider);
            const disabled = !state.byok_unlocked || saving[provider];
            return (
              <div
                key={provider}
                data-testid={`byok-card-${provider}`}
                className="rounded-2xl border border-[rgb(var(--tf-border))] p-5 bg-[rgba(0,0,0,0.2)]"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block w-2 h-2 rounded-full"
                        style={{ backgroundColor: meta.accent }}
                      />
                      <h3 className="font-display text-lg">{meta.label}</h3>
                      {existing && (
                        <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-sm border border-[rgb(var(--tf-matrix))] text-[rgb(var(--tf-matrix))]">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <a
                      href={meta.docs}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-[rgb(var(--tf-text-muted))] hover:text-[rgb(var(--tf-brand))] mt-1 inline-block"
                    >
                      Get a key →
                    </a>
                  </div>
                  {existing && (
                    <button
                      onClick={() => remove(provider)}
                      data-testid={`byok-remove-${provider}`}
                      className="text-xs text-[rgb(var(--tf-text-muted))] hover:text-red-400 border border-[rgb(var(--tf-border))] hover:border-red-400 px-3 py-1.5 rounded-md transition-colors"
                    >
                      Remove
                    </button>
                  )}
                </div>

                {existing ? (
                  <div className="mt-4 font-mono text-sm text-[rgb(var(--tf-text-2))]">
                    Stored key: <span className="text-white">{existing.masked}</span>
                    <span className="text-[rgb(var(--tf-text-muted))] ml-3">
                      added {new Date(existing.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ) : (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      save(provider);
                    }}
                    className="mt-4 flex flex-col sm:flex-row gap-2"
                  >
                    <input
                      type="password"
                      placeholder={meta.placeholder}
                      value={drafts[provider]}
                      onChange={(e) =>
                        setDrafts((d) => ({ ...d, [provider]: e.target.value }))
                      }
                      disabled={disabled}
                      data-testid={`byok-input-${provider}`}
                      className="flex-1 bg-[rgba(0,0,0,0.4)] border border-[rgb(var(--tf-border))] rounded-md px-3 py-2 font-mono text-sm disabled:opacity-40"
                    />
                    <button
                      type="submit"
                      disabled={disabled}
                      data-testid={`byok-save-${provider}`}
                      className="px-5 py-2 rounded-md bg-[rgb(var(--tf-brand))] text-black font-mono text-xs uppercase tracking-widest hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      {saving[provider] ? "Saving…" : "Save & encrypt"}
                    </button>
                  </form>
                )}
              </div>
            );
          })}
        </div>

        {/* Security blurb */}
        <div className="mt-8 text-xs text-[rgb(var(--tf-text-muted))] font-mono leading-relaxed">
          🔒 Keys are encrypted at rest with AES-128-CBC + HMAC (Fernet). The server decrypts in-memory
          per request and never logs raw keys. Rotate or remove at any time.
        </div>
      </main>
      <Footer />
    </div>
  );
}
