"use client";

export default function LogoutButton() {
  async function logout() {
    await fetch("/api/session/logout", { method: "POST" });
    window.location.href = "/";
  }

  return (
    <button type="button" className="secondary-button" onClick={logout}>
      Sign out
    </button>
  );
}
