"use client";

import { FormEvent, useState } from "react";

export default function OperatorRegistration() {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/private/operators", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        legal_name: form.get("legal_name"),
        business_name: form.get("business_name")
      })
    });
    const body = await response.json();
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) {
      setMessage(body?.error?.message ?? body?.detail ?? "Registration failed");
      setBusy(false);
      return;
    }
    window.location.reload();
  }

  return (
    <form className="auth-card stack" onSubmit={submit}>
      <h2>Register a fleet business</h2>
      <p>New operators must be approved before listings become bookable.</p>
      <label>Legal business name<input name="legal_name" required minLength={2} /></label>
      <label>Public business name<input name="business_name" required minLength={2} /></label>
      <button className="primary-button" disabled={busy}>Register operator</button>
      {message && <p className="message" role="alert">{message}</p>}
    </form>
  );
}
