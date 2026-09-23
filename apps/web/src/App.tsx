import { FormEvent, useEffect, useState } from "react";

import { Projects } from "./Projects";

type User = { id: number; name: string; email: string; role: "ADMIN" | "TESTER" | "DEV" };
type LoginResponse = { user: User; csrf_token: string };

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [csrfToken, setCsrfToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    fetch("/api/auth/session", { credentials: "include" })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload: LoginResponse | null) => {
        if (payload) {
          setUser(payload.user);
          setCsrfToken(payload.csrf_token);
        }
      })
      .catch(() => undefined);
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      if (!response.ok) throw new Error("Não foi possível iniciar sessão. Verifique os dados.");
      const payload = (await response.json()) as LoginResponse;
      setUser(payload.user);
      setCsrfToken(payload.csrf_token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    const response = await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken },
    });
    if (response.ok) {
      setUser(null);
      setCsrfToken("");
    }
  }

  return (
    <main className="shell">
      {user ? (
        <Projects user={user} csrfToken={csrfToken} onLogout={handleLogout} />
      ) : <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Ambiente local · acesso privado</p>
        <h1 id="page-title">QA Test Manager</h1>
          <form className="login-form" onSubmit={handleLogin}>
            <p className="summary">Entre com o Admin criado localmente. Nenhum dado é enviado para a cloud.</p>
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" autoComplete="username" required />
            <label htmlFor="password">Palavra-passe</label>
            <div className="password-field">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                aria-label={showPassword ? "Ocultar palavra-passe" : "Mostrar palavra-passe"}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? (
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8M9.9 4.2A10.8 10.8 0 0112 4c5.5 0 9 5 9 5a16 16 0 01-2.3 2.8M6.6 6.6C4.3 8.1 3 10 3 10s3.5 5 9 5a10 10 0 004-.8" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5z" />
                    <circle cx="12" cy="12" r="2.5" />
                  </svg>
                )}
              </button>
            </div>
            {error && <p className="error" role="alert">{error}</p>}
            <button type="submit" disabled={loading}>{loading ? "A entrar…" : "Entrar"}</button>
          </form>
      </section>}
    </main>
  );
}
