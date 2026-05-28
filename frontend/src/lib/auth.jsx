import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
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

  const login = async (email, password) => {
    try {
      const { data } = await client.post("/auth/login", { email, password });
      setToken(data.token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  };

  const register = async (email, password, name) => {
    try {
      const { data } = await client.post("/auth/register", { email, password, name });
      setToken(data.token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, bootstrapped, login, register, logout, refresh: fetchMe }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
