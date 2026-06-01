import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/lib/auth";

import Landing from "@/pages/Landing";
import { Login, Register, OAuthCallback } from "@/pages/Auth";
import Pricing from "@/pages/Pricing";
import Playground from "@/pages/Playground";
import Dashboard from "@/pages/Dashboard";
import Keys from "@/pages/Keys";
import LlmKeys from "@/pages/LlmKeys";
import Logs from "@/pages/Logs";
import Billing, { BillingSuccess } from "@/pages/Billing";
import Docs from "@/pages/Docs";
import Admin from "@/pages/Admin";
import Share from "@/pages/Share";
import Refer from "@/pages/Refer";
import Enterprise from "@/pages/Enterprise";
import Affiliate from "@/pages/Affiliate";

function Protected({ children, adminOnly }) {
  const { user, bootstrapped } = useAuth();
  if (!bootstrapped) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[rgb(var(--tf-bg))] text-[rgb(var(--tf-text-muted))] font-mono text-sm">
        <span className="tf-dot" /><span className="tf-dot" /><span className="tf-dot" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster theme="dark" position="bottom-right" richColors />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/oauth/callback" element={<OAuthCallback />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/refer" element={<Refer />} />
          <Route path="/enterprise" element={<Enterprise />} />
          <Route path="/affiliate" element={<Affiliate />} />
          <Route path="/share/:slug" element={<Share />} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/dashboard/keys" element={<Protected><Keys /></Protected>} />
          <Route path="/dashboard/llm-keys" element={<Protected><LlmKeys /></Protected>} />
          <Route path="/dashboard/logs" element={<Protected><Logs /></Protected>} />
          <Route path="/dashboard/billing" element={<Protected><Billing /></Protected>} />
          <Route path="/billing/success" element={<Protected><BillingSuccess /></Protected>} />
          <Route path="/admin" element={<Protected adminOnly><Admin /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
