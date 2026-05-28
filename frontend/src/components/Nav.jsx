import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function MarketingNav() {
  return (
    <header
      data-testid="marketing-nav"
      className="sticky top-0 z-50 backdrop-blur-xl bg-[rgb(var(--tf-bg))]/70 border-b border-[rgb(var(--tf-border))]"
    >
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" data-testid="brand-home" className="flex items-center gap-2">
          <Logo />
          <span className="font-display text-xl tracking-tight">TokenForge</span>
        </Link>
        <nav className="hidden md:flex items-center gap-8 text-sm text-[rgb(var(--tf-text-2))]">
          <a href="/#engine" data-testid="nav-engine" className="hover:text-white">Engine</a>
          <a href="/#pillars" data-testid="nav-pillars" className="hover:text-white">5 Pillars</a>
          <Link to="/playground" data-testid="nav-playground" className="hover:text-white">Playground</Link>
          <Link to="/pricing" data-testid="nav-pricing" className="hover:text-white">Pricing</Link>
          <Link to="/docs" data-testid="nav-docs" className="hover:text-white">Docs</Link>
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/login" data-testid="nav-login" className="text-sm text-[rgb(var(--tf-text-2))] hover:text-white px-3 py-2">
            Sign in
          </Link>
          <Link
            to="/register"
            data-testid="nav-cta-register"
            className="text-sm font-medium bg-[rgb(var(--tf-brand))] hover:bg-[rgb(var(--tf-brand-hover))] text-black px-4 py-2 rounded-md transition-colors"
          >
            Start free →
          </Link>
        </div>
      </div>
    </header>
  );
}

export function DashboardNav() {
  const { user, logout } = useAuth();
  const loc = useLocation();
  const link = (to, label, testid) => (
    <Link
      to={to}
      data-testid={testid}
      className={`px-3 py-2 rounded-md text-sm transition-colors ${
        loc.pathname === to
          ? "bg-[rgb(var(--tf-bg-3))] text-white"
          : "text-[rgb(var(--tf-text-2))] hover:text-white hover:bg-[rgb(var(--tf-bg-2))]"
      }`}
    >
      {label}
    </Link>
  );
  return (
    <header
      data-testid="dashboard-nav"
      className="sticky top-0 z-50 backdrop-blur-xl bg-[rgb(var(--tf-bg))]/80 border-b border-[rgb(var(--tf-border))]"
    >
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <Link to="/dashboard" className="flex items-center gap-2" data-testid="dash-brand">
            <Logo />
            <span className="font-display text-lg tracking-tight">TokenForge</span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {link("/dashboard", "Overview", "dash-nav-overview")}
            {link("/dashboard/keys", "API Keys", "dash-nav-keys")}
            {link("/dashboard/logs", "Logs", "dash-nav-logs")}
            {link("/playground", "Playground", "dash-nav-playground")}
            {link("/dashboard/billing", "Billing", "dash-nav-billing")}
            {link("/docs", "Docs", "dash-nav-docs")}
            {user?.role === "admin" && link("/admin", "Admin", "dash-nav-admin")}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <div data-testid="user-email" className="text-xs text-[rgb(var(--tf-text-2))] font-mono">{user?.email}</div>
            <div data-testid="user-plan" className="text-[10px] uppercase tracking-widest text-[rgb(var(--tf-brand))]">{user?.plan || "free"}</div>
          </div>
          <button
            data-testid="logout-btn"
            onClick={logout}
            className="text-xs text-[rgb(var(--tf-text-2))] hover:text-white border border-[rgb(var(--tf-border))] hover:border-[rgb(var(--tf-border-2))] px-3 py-1.5 rounded-md transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

export function Logo() {
  return (
    <div className="w-7 h-7 rounded-sm bg-[rgb(var(--tf-brand))] flex items-center justify-center relative overflow-hidden">
      <span className="font-display text-black text-sm leading-none">TF</span>
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/20 to-transparent" />
    </div>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-[rgb(var(--tf-border))] mt-24" data-testid="footer">
      <div className="max-w-7xl mx-auto px-6 py-10 grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Logo />
            <span className="font-display text-lg tracking-tight">TokenForge</span>
          </div>
          <p className="text-[rgb(var(--tf-text-muted))] text-xs leading-relaxed">
            Deterministic prompt distillation. Cut your LLM API bill by 40–80% without changing your model.
          </p>
        </div>
        <div>
          <div className="text-[rgb(var(--tf-text-muted))] text-xs uppercase tracking-widest mb-3">Product</div>
          <ul className="space-y-2 text-[rgb(var(--tf-text-2))]">
            <li><Link to="/playground" className="hover:text-white">Playground</Link></li>
            <li><Link to="/pricing" className="hover:text-white">Pricing</Link></li>
            <li><Link to="/docs" className="hover:text-white">Docs</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-[rgb(var(--tf-text-muted))] text-xs uppercase tracking-widest mb-3">Engine</div>
          <ul className="space-y-2 text-[rgb(var(--tf-text-2))]">
            <li>Lexical Compression</li>
            <li>Boilerplate Strip</li>
            <li>Struct Serialization</li>
            <li>Semantic Cache</li>
            <li>Multi-tier Routing</li>
          </ul>
        </div>
        <div>
          <div className="text-[rgb(var(--tf-text-muted))] text-xs uppercase tracking-widest mb-3">Company</div>
          <ul className="space-y-2 text-[rgb(var(--tf-text-2))]">
            <li><Link to="/register" className="hover:text-white">Get started</Link></li>
            <li><Link to="/login" className="hover:text-white">Sign in</Link></li>
            <li><a href="mailto:hello@tokenforge.io" className="hover:text-white">hello@tokenforge.io</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-[rgb(var(--tf-border))] py-5 text-center text-xs text-[rgb(var(--tf-text-muted))] font-mono">
        © {new Date().getFullYear()} TokenForge — distill or perish.
      </div>
    </footer>
  );
}
