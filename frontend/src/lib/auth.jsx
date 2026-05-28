import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import client, { setToken, getToken, formatApiErrorDetail } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = loading, false = anon, object = signed in
  const [bootstrapped, setBootstrapped] = useState(false);

  const fetchMe = useCallback(async () => {
    const t = getToken();
    if (!t) {
      setUser(false);
      setBootstrapped(true);
      return;
    }
    try {
      const { data } = await client.get("/auth/me");
      setUser(data);
    } catch (e) {
      setToken(null);
      setUser(false);
    } finally {
      setBootstrapped(true);
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const login = useCallback(async (email, password) => {
    try {
      const { data } = await client.post("/auth/login", { email, password });
      setToken(data.token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  }, []);

  const register = useCallback(async (email, password, name, ref) => {
    try {
      const payload = { email, password, name };
      if (ref) payload.ref = ref;
      const { data } = await client.post("/auth/register", payload);
      setToken(data.token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(false);
  }, []);

  // Memoize context value so consumers don't re-render on every parent render.
  const value = useMemo(
    () => ({ user, bootstrapped, login, register, logout, refresh: fetchMe }),
    [user, bootstrapped, login, register, logout, fetchMe]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
