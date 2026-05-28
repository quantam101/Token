import React, { useEffect, useState } from "react";
import client, { formatApiErrorDetail } from "@/lib/api";
import { DashboardNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

export default function Keys() {
  const [keys, setKeys] = useState([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [revealId, setRevealId] = useState(null);

  const load = async () => {
    const { data } = await client.get("/keys");
    setKeys(data.keys);
  };

  useEffect(() => {
    load();
  }, []);

  const create = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      const { data } = await client.post("/keys", { name });
      setName("");
      setRevealId(data.id);
      await load();
      toast.success("Key created");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (id) => {
    if (!window.confirm("Revoke this API key? Calls using it will stop working immediately.")) return;
    try {
      await client.delete(`/keys/${id}`);
      await load();
      toast.success("Key revoked");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || "Failed");
    }
  };

  const copy = (k) => {
    navigator.clipboard.writeText(k);
    toast.success("Copied to clipboard");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <DashboardNav />
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8">
        <div>
          <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))]">
            CREDENTIALS
          </div>
          <h1 className="font-display text-3xl tracking-tight mt-1">API Keys</h1>
          <p className="text-[rgb(var(--tf-text-2))] mt-2 max-w-xl">
            Use the <code className="font-mono text-[rgb(var(--tf-brand))]">X-TF-Key</code> header to authenticate proxy calls.
          </p>
        </div>

        <form onSubmit={create} className="mt-6 flex gap-3" data-testid="create-key-form">
          <input
            data-testid="new-key-name"
            placeholder="key name (e.g. production-web)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 bg-[rgb(var(--tf-bg-2))] border border-[rgb(var(--tf-border))] focus:border-[rgb(var(--tf-brand))] focus:ring-1 focus:ring-[rgb(var(--tf-brand))] outline-none rounded-md px-4 py-2.5 font-mono text-sm"
          />
          <button
            type="submit"
            disabled={busy}
            data-testid="create-key-btn"
            className="bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-5 py-2.5 rounded-md transition-colors disabled:opacity-60"
          >
            {busy ? "Creating…" : "Generate key"}
          </button>
        </form>

        <div className="mt-6 border border-[rgb(var(--tf-border))]" data-testid="keys-table">
          <table className="w-full text-sm">
            <thead className="text-[rgb(var(--tf-text-muted))] text-xs uppercase font-mono">
              <tr className="border-b border-[rgb(var(--tf-border))]">
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Key</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {keys.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-[rgb(var(--tf-text-muted))]">No keys yet</td></tr>
              ) : keys.map((k) => {
                const masked = k.key.slice(0, 12) + "•••" + k.key.slice(-4);
                const showFull = revealId === k.id;
                return (
                  <tr key={k.id} className="border-b border-[rgb(var(--tf-border))] hover:bg-[rgb(var(--tf-bg-2))]">
                    <td className="px-4 py-3 font-medium">{k.name}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      <button
                        data-testid={`reveal-key-${k.id}`}
                        onClick={() => setRevealId(showFull ? null : k.id)}
                        className="text-[rgb(var(--tf-text-2))] hover:text-white"
                      >
                        {showFull ? k.key : masked}
                      </button>
                      <button
                        data-testid={`copy-key-${k.id}`}
                        onClick={() => copy(k.key)}
                        className="ml-2 text-[10px] uppercase tracking-widest text-[rgb(var(--tf-brand))] hover:underline"
                      >
                        copy
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs text-[rgb(var(--tf-text-2))] font-mono">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      {k.active ? (
                        <span className="text-xs font-mono text-[rgb(var(--tf-success))]">● active</span>
                      ) : (
                        <span className="text-xs font-mono text-[rgb(var(--tf-text-muted))]">○ revoked</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {k.active && (
                        <button
                          data-testid={`revoke-key-${k.id}`}
                          onClick={() => revoke(k.id)}
                          className="text-xs font-mono text-[rgb(var(--tf-error))] hover:underline"
                        >
                          revoke
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </main>
      <Footer />
    </div>
  );
}
