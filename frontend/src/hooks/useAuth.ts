import { useState, useEffect } from "react";
import { config } from "../config";

interface AuthState {
  token: string | null;
  email: string | null;
  name: string | null;
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>({ token: null, email: null, name: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${config.apiUrl}/api/auth/status`)
      .then((r) => r.json())
      .then((data) => {
        if (data.authenticated) {
          setAuth({ token: data.token, email: data.email, name: data.name });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function requestCode(email: string) {
    const res = await fetch(`${config.apiUrl}/api/auth/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || "Failed to send code");
    }
  }

  async function confirmCode(email: string, code: string) {
    const res = await fetch(`${config.apiUrl}/api/auth/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, code }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || "Invalid code");
    }
    const data = await res.json();
    setAuth({ token: data.token, email: data.email, name: data.name });
  }

  function logout() {
    fetch(`${config.apiUrl}/api/auth/logout`, { method: "POST" }).catch(() => {});
    setAuth({ token: null, email: null, name: null });
  }

  return { auth, loading, requestCode, confirmCode, logout };
}
