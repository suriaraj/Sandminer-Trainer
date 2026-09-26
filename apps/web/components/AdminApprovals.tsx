"use client";
import { useEffect, useState } from "react";

type Operator = { id: string; business_name: string; status: string };
type Vehicle = { id: string; brand: string; model: string; status: string };
type Case = { id: string; status: string; service_type: string };
type Evidence = { id: string; document_type: string; status: string; download_url: string | null };

export default function AdminApprovals() {
  const [operators, setOperators] = useState<Operator[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [documents, setDocuments] = useState<Evidence[]>([]);
  const [selectedCase, setSelectedCase] = useState("");
  const [message, setMessage] = useState("");

  async function api(path: string, body?: object) {
    const response = await fetch("/api/private/" + path, body ? {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    } : undefined);
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(payload?.error?.message ?? payload?.detail ?? "Request failed");
    return payload;
  }

  async function refresh() {
    const [ops, fleet, kyc] = await Promise.all([
      api("admin/operators"), api("admin/vehicles"),
      api("admin/kyc/cases?status=SUBMITTED")
    ]);
    setOperators(ops);
    setVehicles(fleet);
    setCases(kyc);
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(error.message));
  }, []);

  async function action(path: string, body: object) {
    setMessage("");
    try {
      await api(path, body);
      await refresh();
      setMessage("Action recorded and audited.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Action failed");
    }
  }

  async function openCase(id: string) {
    setSelectedCase(id);
    try { setDocuments(await api("admin/kyc/" + id + "/documents")); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to load documents"); }
  }

  return <section className="auth-card">
    <h2>Approvals and reviews</h2>
    <p className="muted">Only appropriately authorized accounts can execute these changes.
      Production onboarding still requires external regulatory and business verification.</p>
    <div className="kyc-grid">
      <div>
        <h3>Operators</h3>
        {operators.map(item => <div className="case-row" key={item.id}>
          <strong>{item.business_name}</strong> — {item.status}
          {item.status === "REGISTERED" && <button className="secondary-button" onClick={() =>
            action("admin/operators/" + item.id + "/status", { status: "UNDER_REVIEW" })
          }>Send for review</button>}
        </div>)}
      </div>
      <div>
        <h3>Inactive vehicles</h3>
        {vehicles.filter(v => v.status === "INACTIVE").map(v =>
          <div className="case-row" key={v.id}>
            {v.brand} {v.model}: {v.status}
            <button className="secondary-button" onClick={() =>
              action("admin/vehicles/" + v.id + "/status", { status: "AVAILABLE" })
            }>Activate (development only)</button>
          </div>
        )}
      </div>
    </div>
    <h3>Pending KYC document review</h3>
    {cases.map(item => <button className="case-row" key={item.id}
      onClick={() => openCase(item.id)}>
      {item.service_type} — {item.status} · Open evidence
    </button>)}
    {selectedCase && <section className="auth-card">
      <h4>Evidence for {selectedCase}</h4>
      {documents.map(doc => <div className="case-row" key={doc.id}>
        <strong>{doc.document_type}</strong> — {doc.status}
        {doc.download_url && <a className="secondary-button"
          rel="noreferrer" target="_blank" href={doc.download_url}>View evidence</a>}
        {doc.status === "UPLOADED" && <span>
          <button className="secondary-button" onClick={() =>
            action("admin/kyc/documents/" + doc.id + "/review", { decision: "VERIFIED" })
          }>Mark reviewed</button>
          <button className="secondary-button" onClick={() =>
            action("admin/kyc/documents/" + doc.id + "/review", { decision: "REJECTED" })
          }>Reject</button>
        </span>}
      </div>)}
      <p className="muted">Approval of the KYC case requires reviewed service-specific
        evidence and an explicit future expiry via the admin API.</p>
    </section>}
    {message && <p role="status" className="message">{message}</p>}
  </section>;
}
