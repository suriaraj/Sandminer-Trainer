"use client";

import { FormEvent, useState } from "react";
import { searchVehicles, VehicleSearchItem } from "../lib/api";

export default function SearchPanel() {
  const [city, setCity] = useState("Chennai");
  const [pickupAt, setPickupAt] = useState("");
  const [returnAt, setReturnAt] = useState("");
  const [vehicles, setVehicles] = useState<VehicleSearchItem[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const results = await searchVehicles({
        city,
        pickupAt: new Date(pickupAt).toISOString(),
        returnAt: new Date(returnAt).toISOString()
      });
      setVehicles(results);
      if (results.length === 0) setMessage("No vehicles are available for that exact period.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed.");
      setVehicles([]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="search-shell" aria-labelledby="search-title">
      <div>
        <p className="eyebrow">Plan the exact rental</p>
        <h2 id="search-title">Search live vehicle inventory</h2>
        <p className="muted">
          Availability is revalidated again when you book, so a search result never becomes a false guarantee.
        </p>
      </div>
      <form onSubmit={submit} className="search-grid">
        <label>City<input value={city} onChange={(e) => setCity(e.target.value)} required /></label>
        <label>Pickup<input type="datetime-local" value={pickupAt} onChange={(e) => setPickupAt(e.target.value)} required /></label>
        <label>Return<input type="datetime-local" value={returnAt} onChange={(e) => setReturnAt(e.target.value)} required /></label>
        <button type="submit" disabled={busy}>{busy ? "Checking…" : "Check availability"}</button>
      </form>
      {message && <p role="status" className="message">{message}</p>}
      <div className="vehicle-grid" aria-live="polite">
        {vehicles.map((vehicle) => (
          <article className="vehicle-card" key={vehicle.id}>
            <span className="tag">Available</span>
            <h3>{vehicle.brand} {vehicle.model}</h3>
            <p>{vehicle.variant ?? "Standard variant"}</p>
            <dl>
              <div><dt>City</dt><dd>{vehicle.city}</dd></div>
              <div><dt>Fuel</dt><dd>{vehicle.fuel ?? "—"}</dd></div>
              <div><dt>Transmission</dt><dd>{vehicle.transmission ?? "—"}</dd></div>
              <div><dt>Seats</dt><dd>{vehicle.seats ?? "—"}</dd></div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
