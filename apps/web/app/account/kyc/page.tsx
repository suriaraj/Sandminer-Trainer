"use client";

import { ChangeEvent, useEffect, useState } from "react";

type KycCase = {
  id: string;
  status: string;
  country_code: string;
  service_type: string;
  reason: string | null;
  expires_at: string | null;
};
type DocumentRow = {
  id: string;
  document_type: string;
  status: string;
};

export default function KycPage() {
  const [cases, setCases] = useState<KycCase[]>([]);
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [active, setActive] = useState<KycCase | null>(null);
  const [service, setService] = useState("SELF_DRIVE");
  const [documentType, setDocumentType] = useState("DRIVING_LICENSE");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function getJson(url: string, init?: RequestInit) {
    const response = await fetch(url, init);
    const data = await response.json();
    if (response.status === 401) {
      window.location.href = "/login";
      throw new Error("Session expired");
    }
    if (!response.ok) {
      throw new Error(data?.error?.message ?? data?.detail ?? "Request failed");
    }
    return data;
  }

  async function load() {
    const data: KycCase[] = await getJson("/api/private/kyc/cases/me");
    setCases(data);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function beginCase() {
    setBusy(true);
    setError("");
    try {
      const item: KycCase = await getJson("/api/private/kyc/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ country_code: "IN", service_type: service })
      });
      setActive(item);
      setDocuments([]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to begin KYC");
    } finally { setBusy(false); }
  }

  async function selectCase(item: KycCase) {
    setActive(item);
    setError("");
    try {
      const docs: DocumentRow[] = await getJson(
        `/api/private/kyc/cases/${item.id}/documents`
      );
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot load documents");
    }
  }

  function changeFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function upload() {
    if (!active || !file) return;
    setBusy(true);
    setError("");
    try {
      if (file.size > 10 * 1024 * 1024) {
        throw new Error("Maximum document size is 10 MB.");
      }
      const accepted = ["application/pdf", "image/png", "image/jpeg"];
      if (!accepted.includes(file.type)) {
        throw new Error("Upload a PDF, PNG or JPEG document.");
      }
      const grant = await getJson(
        `/api/private/kyc/cases/${active.id}/documents`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            document_type: documentType,
            content_type: file.type,
            file_size: file.size
          })
        }
      );
      const form = new FormData();
      for (const [key, value] of Object.entries(grant.fields as Record<string, string>)) {
        form.append(key, value);
      }
      form.append("file", file);
      const uploaded = await fetch(grant.upload_url, {
        method: "POST", body: form
      });
      if (!uploaded.ok) {
        throw new Error("Private storage upload failed; check your network and CORS.");
      }
      await getJson(`/api/private/kyc/documents/${grant.document_id}/confirm`, {
        method: "POST"
      });
      await selectCase(active);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Document upload failed");
    } finally { setBusy(false); }
  }

  return (
    <main className="portal-page">
      <header className="portal-header">
        <a className="brand dark-brand" href="/">PYRO <span>RENTALS</span></a>
        <a className="secondary-button" href="/account/bookings">My bookings</a>
      </header>
      <section className="portal-panel wide">
        <p className="eyebrow">Verified, privacy-first rentals</p>
        <h1>Identity verification</h1>
        <p className="muted">
          Your documents go directly to private storage. Submitting does not mean
          approval; an authorized reviewer verifies evidence before a rental can be confirmed.
        </p>
        <div className="kyc-grid">
          <div className="auth-card">
            <h2>Start a KYC case</h2>
            <label className="stack">Rental service
              <select value={service} onChange={(e) => {
                setService(e.target.value);
                setDocumentType(e.target.value === "SELF_DRIVE"
                  ? "DRIVING_LICENSE" : "IDENTITY_PROOF");
              }}>
                <option value="SELF_DRIVE">Self drive</option>
                <option value="CHAUFFEUR_PACKAGE">With driver</option>
                <option value="AIRPORT_TRANSFER">Airport</option>
                <option value="OUTSTATION_ONE_WAY">Outstation one-way</option>
                <option value="OUTSTATION_ROUND_TRIP">Outstation round-trip</option>
              </select>
            </label>
            <button className="primary-button" disabled={busy} onClick={beginCase}>
              Create or resume case
            </button>
          </div>
          <div className="auth-card">
            <h2>My cases</h2>
            {cases.length === 0 ? <p>No KYC cases yet.</p> : cases.map((item) => (
              <button
                type="button" className="case-row" key={item.id}
                onClick={() => selectCase(item)}
              >
                {item.service_type} — <strong>{item.status}</strong>
              </button>
            ))}
          </div>
        </div>
        {active && (
          <section className="auth-card">
            <h2>{active.service_type}: {active.status}</h2>
            {active.status === "VERIFIED" ? (
              <p>Your KYC is approved. Expiry: {active.expires_at ?? "Not configured"}</p>
            ) : active.status === "SUBMITTED" ? (
              <p>Your document is submitted and awaiting manual review.</p>
            ) : (
              <div className="stack">
                <label>Document type
                  <select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
                    <option value="DRIVING_LICENSE">Driving license</option>
                    <option value="IDENTITY_PROOF">Identity proof</option>
                    <option value="ADDRESS_PROOF">Address proof</option>
                  </select>
                </label>
                <label>PDF, JPEG or PNG (up to 10 MB)
                  <input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={changeFile} />
                </label>
                <button className="primary-button" disabled={!file || busy} onClick={upload}>
                  {busy ? "Uploading and verifying…" : "Upload securely"}
                </button>
              </div>
            )}
            {documents.map((doc) => (
              <p className="case-row" key={doc.id}>
                {doc.document_type}: <strong>{doc.status}</strong>
              </p>
            ))}
          </section>
        )}
        {error && <p className="message" role="alert">{error}</p>}
      </section>
    </main>
  );
}
