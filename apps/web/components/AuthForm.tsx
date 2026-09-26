"use client";

import { FormEvent, useState } from "react";

export default function AuthForm() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    const payload =
      mode === "login"
        ? {
            email: form.get("email"),
            password: form.get("password")
          }
        : {
            full_name: form.get("full_name"),
            email: form.get("email"),
            password: form.get("password")
          };

    const response = await fetch(`/api/session/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      window.location.href = "/account/bookings";
      return;
    }

    const body = await response.json().catch(() => ({}));
    setMessage(body?.error?.message ?? body?.detail ?? "Authentication failed.");
    setBusy(false);
  }

  return (
    <div className="auth-card">
      <div className="auth-tabs" role="tablist">
        <button
          type="button"
          className={mode === "login" ? "active" : ""}
          onClick={() => setMode("login")}
        >
          Sign in
        </button>
        <button
          type="button"
          className={mode === "register" ? "active" : ""}
          onClick={() => setMode("register")}
        >
          Create account
        </button>
      </div>
      <form onSubmit={submit} className="stack">
        {mode === "register" && (
          <label>
            Full name
            <input name="full_name" minLength={2} maxLength={160} required />
          </label>
        )}
        <label>
          Email
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            minLength={12}
            maxLength={128}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
          />
        </label>
        <button className="primary-button" disabled={busy}>
          {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
        {message && <p className="message" role="alert">{message}</p>}
      </form>
    </div>
  );
}
