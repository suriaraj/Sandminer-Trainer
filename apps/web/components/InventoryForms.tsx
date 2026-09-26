"use client";
import { FormEvent, useState } from "react";

type Operator = { id: string; business_name: string };
type Category = { id: string; name: string };
export default function InventoryForms({ operators, categories }: {
  operators: Operator[]; categories: Category[]
}) {
  const [operator, setOperator] = useState(operators[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");

  async function save(e: FormEvent<HTMLFormElement>, resource: string) {
    e.preventDefault();
    setBusy(true);
    setResult("");
    const form = new FormData(e.currentTarget);
    const raw = Object.fromEntries(form);
    const payload = resource === "vehicles" ? {
      ...raw, operator_id: operator, timezone: "Asia/Kolkata",
      seats: Number(raw.seats)
    } : {
      ...raw, operator_id: operator, currency: "INR",
      duration_minutes: Number(raw.duration_minutes)
    };
    try {
      const response = await fetch("/api/private/operator/" + resource, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.error?.message ?? data?.detail ?? "Save failed");
      setResult(resource === "vehicles"
        ? "Vehicle added; administrator activation is required."
        : "Pricing package saved.");
    } catch (error) {
      setResult(error instanceof Error ? error.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (!operators.length) return <p>Register an operator first.</p>;
  return <section className="auth-card">
    <h2>Manage your fleet</h2>
    <label>Operator
      <select value={operator} onChange={e => setOperator(e.target.value)}>
        {operators.map(o => <option value={o.id} key={o.id}>{o.business_name}</option>)}
      </select>
    </label>
    <div className="kyc-grid">
      <form className="auth-card stack" onSubmit={e => save(e, "vehicles")}>
        <h3>Add a vehicle</h3>
        <label>Category<select name="category_id" required>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select></label>
        {(["registration_number", "brand", "model", "city"] as const).map(key =>
          <label key={key}>{key.replace("_", " ")}<input name={key} required /></label>
        )}
        <label>Fuel<input name="fuel" defaultValue="PETROL" /></label>
        <label>Transmission<select name="transmission">
          <option value="MANUAL">Manual</option>
          <option value="AUTOMATIC">Automatic</option>
        </select></label>
        <label>Seats<input name="seats" type="number" min={1} max={80} defaultValue={5} required /></label>
        <button className="primary-button" disabled={busy}>Save vehicle</button>
      </form>
      <form className="auth-card stack" onSubmit={e => save(e, "packages")}>
        <h3>Add a rental package</h3>
        <label>Name<input name="name" defaultValue="24 hours / 200 km" required /></label>
        <label>Service<select name="service_type">
          {["SELF_DRIVE","CHAUFFEUR_PACKAGE","AIRPORT_TRANSFER","OUTSTATION_ONE_WAY","OUTSTATION_ROUND_TRIP"].map(value =>
            <option key={value} value={value}>{value.replaceAll("_", " ")}</option>
          )}
        </select></label>
        {([
          ["duration_minutes","1440"],["included_km","200"],["base_price","2500"],
          ["tax_rate","0.18"],["deposit","5000"]
        ] as const).map(([key,value]) =>
          <label key={key}>{key.replaceAll("_", " ")}
            <input name={key} type="number" min={0} step={key==="duration_minutes" ? "1" : ".01"}
              defaultValue={value} required />
          </label>
        )}
        <button className="primary-button" disabled={busy}>Save package</button>
      </form>
    </div>
    {result && <p role="status" className="message">{result}</p>}
  </section>;
}
