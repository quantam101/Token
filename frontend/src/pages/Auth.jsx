import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { setToken } from "@/lib/api";
import { API } from "@/lib/api";
import { MarketingNav, Footer } from "@/components/Nav";
import { toast } from "sonner";

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    const r = await login(email, password);
    if (r.ok) {
      toast.success("Welcome back");
      nav("/dashboard");
    } else {
      setErr(r.error);
    }
    setBusy(false);
  };

  return (
    <AuthShell title="Sign in" subtitle="Welcome back to the forge.">
      <GoogleButton text="Sign in with Google" />
      <Divider />
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        <Field label="Email">
          <input
            data-testid="login-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="tf-input"
            autoFocus
          />
        </Field>
        <Field label="Password">
          <input
            data-testid="login-password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="tf-input"
          />
        </Field>
        {err && <div data-testid="login-error" className="text-sm text-[rgb(var(--tf-error))] font-mono">{err}</div>}
        <button
          data-testid="login-submit"
          type="submit"
          disabled={busy}
          className="w-full bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-5 py-3 rounded-md transition-colors disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in →"}
        </button>
      </form>
      <div className="mt-6 text-sm text-[rgb(var(--tf-text-2))]">
        New to TokenForge?{" "}
        <Link to="/register" data-testid="link-to-register" className="text-[rgb(var(--tf-brand))] hover:underline">
          Create an account
        </Link>
      </div>
    </AuthShell>
  );
}

export function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const ref = searchParams.get("ref") || "";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    const r = await register(email, password, name, ref);
    if (r.ok) {
      if (ref) toast.success("Account + 500K bonus tokens unlocked from referral.");
      else toast.success("Account created — your API key is ready.");
      nav("/dashboard");
    } else {
      setErr(r.error);
    }
    setBusy(false);
  };

  return (
    <AuthShell
      title="Create account"
      subtitle={ref ? "Referral applied — you'll get +500K bonus tokens this month." : "50,000 free tokens/month. No card required."}
    >
      {ref && (
        <div data-testid="referral-banner" className="mb-4 border border-[rgb(var(--tf-success))] bg-[rgba(0,230,118,0.08)] rounded-md p-3 text-sm">
          <span className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-success))]">REFERRAL BONUS</span>
          <span className="ml-2 text-[rgb(var(--tf-text-2))]">+500,000 tokens unlocked on signup.</span>
        </div>
      )}
      <GoogleButton text="Sign up with Google" />
      <Divider />
      <form onSubmit={submit} className="space-y-4" data-testid="register-form">
        <Field label="Name">
          <input data-testid="register-name" value={name} onChange={(e) => setName(e.target.value)} className="tf-input" />
        </Field>
        <Field label="Work email">
          <input
            data-testid="register-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="tf-input"
          />
        </Field>
        <Field label="Password (min 6)">
          <input
            data-testid="register-password"
            type="password"
            minLength={6}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="tf-input"
          />
        </Field>
        {err && <div data-testid="register-error" className="text-sm text-[rgb(var(--tf-error))] font-mono">{err}</div>}
        <button
          data-testid="register-submit"
          disabled={busy}
          type="submit"
          className="w-full bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black font-medium px-5 py-3 rounded-md transition-colors disabled:opacity-60"
        >
          {busy ? "Creating…" : "Create account →"}
        </button>
      </form>
      <div className="mt-6 text-sm text-[rgb(var(--tf-text-2))]">
        Already have an account?{" "}
        <Link to="/login" data-testid="link-to-login" className="text-[rgb(var(--tf-brand))] hover:underline">
          Sign in
        </Link>
      </div>
    </AuthShell>
  );
}

function GoogleButton({ text = "Continue with Google" }) {
  return (
    <button
      type="button"
      onClick={() => { window.location.href = `${API}/auth/google`; }}
      className="w-full flex items-center justify-center gap-3 border border-[rgb(var(--tf-border))] hover:border-white bg-transparent text-white font-medium px-5 py-3 rounded-md transition-colors"
    >
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
        <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z" fill="#34A853"/>
        <path d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332z" fill="#FBBC05"/>
        <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.962L3.964 6.294C4.672 4.167 6.656 3.58 9 3.58z" fill="#EA4335"/>
      </svg>
      {text}
    </button>
  );
}

function Divider() {
  return (
    <div className="flex items-center gap-3 my-4">
      <div className="flex-1 h-px bg-[rgb(var(--tf-border))]" />
      <span className="text-xs font-mono text-[rgb(var(--tf-text-muted))] uppercase tracking-widest">or</span>
      <div className="flex-1 h-px bg-[rgb(var(--tf-border))]" />
    </div>
  );
}

export function OAuthCallback() {
  const { refresh } = useAuth();
  const nav = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const error = params.get("error");
    if (token) {
      setToken(token);
      refresh().then(() => {
        toast.success("Signed in with Google");
        nav("/dashboard", { replace: true });
      });
    } else {
      toast.error(error === "google_denied" ? "Google sign-in cancelled" : "Google sign-in failed");
      nav("/login", { replace: true });
    }
  }, [nav, refresh]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[rgb(var(--tf-bg))] text-[rgb(var(--tf-text-muted))] font-mono text-sm">
      Signing in…
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <div className="text-xs font-mono uppercase tracking-widest text-[rgb(var(--tf-text-muted))] mb-1.5">
        {label}
      </div>
      {children}
    </label>
  );
}

function AuthShell({ title, subtitle, children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <MarketingNav />
      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-md">
          <h1 className="font-display text-4xl tracking-tight">{title}</h1>
          <p className="text-[rgb(var(--tf-text-2))] mt-2">{subtitle}</p>
          <div className="mt-8 p-7 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] rounded-md">
            {children}
          </div>
        </div>
      </main>
      <Footer />
      <style>{`
        .tf-input {
          width: 100%;
          background: rgb(var(--tf-bg-3));
          border: 1px solid rgb(var(--tf-border));
          color: white;
          padding: 0.625rem 0.875rem;
          border-radius: 0.375rem;
          font-family: 'IBM Plex Mono', monospace;
          font-size: 0.875rem;
          outline: none;
        }
        .tf-input:focus {
          border-color: rgb(var(--tf-brand));
          box-shadow: 0 0 0 1px rgb(var(--tf-brand));
        }
      `}</style>
    </div>
  );
}
