"use client";

import { FormEvent, useState } from "react";
import CheckoutButton from "./CheckoutButton";
import {
  getVehiclePackages,
  PricingPackage,
  searchVehicles,
  VehicleSearchItem
} from "../lib/api";

const services = [
  ["SELF_DRIVE", "Self drive"],
  ["CHAUFFEUR_PACKAGE", "With driver"],
  ["AIRPORT_TRANSFER", "Airport transfer"],
  ["OUTSTATION_ONE_WAY", "Outstation one-way"],
  ["OUTSTATION_ROUND_TRIP", "Outstation round-trip"],
  ["CUSTOM_DURATION", "Custom duration"]
] as const;

export default function SearchPanel() {
  const [city, setCity] = useState("Chennai");
  const [pickupLocation, setPickupLocation] = useState("Chennai");
  const [returnLocation, setReturnLocation] = useState("Chennai");
  const [serviceType, setServiceType] = useState("SELF_DRIVE");
  const [pickupAt, setPickupAt] = useState("");
  const [returnAt, setReturnAt] = useState("");
  const [vehicles, setVehicles] = useState<VehicleSearchItem[]>([]);
  const [selectedVehicle, setSelectedVehicle] =
    useState<VehicleSearchItem | null>(null);
  const [packages, setPackages] = useState<PricingPackage[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [packageBusy, setPackageBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setSelectedVehicle(null);
    setPackages([]);
    try {
      const pickupIso = new Date(pickupAt).toISOString();
      const returnIso = new Date(returnAt).toISOString();
      const results = await searchVehicles({
        city,
        pickupAt: pickupIso,
        returnAt: returnIso
      });
      setVehicles(results);
      if (results.length === 0) {
        setMessage("No vehicles are available for that exact period.");
      }
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Search failed."
      );
      setVehicles([]);
    } finally {
      setBusy(false);
    }
  }

  async function chooseVehicle(vehicle: VehicleSearchItem) {
    setSelectedVehicle(vehicle);
    setPackageBusy(true);
    setMessage("");
    try {
      setPackages(await getVehiclePackages(vehicle.id));
    } catch (error) {
      setPackages([]);
      setMessage(
        error instanceof Error ? error.message : "Packages could not be loaded."
      );
    } finally {
      setPackageBusy(false);
    }
  }

  const bookingTimezone =
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone
      : "UTC";

  return (
    <section className="search-shell" aria-labelledby="search-title">
      <div>
        <p className="eyebrow">Plan the exact rental</p>
        <h2 id="search-title">Search live vehicle inventory</h2>
        <p className="muted">
          Search is advisory. Availability is checked again inside the booking
          transaction before your vehicle is reserved.
        </p>
      </div>

      <form onSubmit={submit} className="search-grid enhanced">
        <label>
          City
          <input
            value={city}
            onChange={(event) => setCity(event.target.value)}
            required
          />
        </label>
        <label>
          Service
          <select
            value={serviceType}
            onChange={(event) => setServiceType(event.target.value)}
          >
            {services.map(([value, label]) => (
              <option value={value} key={value}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          Pickup location
          <input
            value={pickupLocation}
            onChange={(event) => setPickupLocation(event.target.value)}
            required
          />
        </label>
        <label>
          Return location
          <input
            value={returnLocation}
            onChange={(event) => setReturnLocation(event.target.value)}
            required
          />
        </label>
        <label>
          Pickup
          <input
            type="datetime-local"
            value={pickupAt}
            onChange={(event) => setPickupAt(event.target.value)}
            required
          />
        </label>
        <label>
          Return
          <input
            type="datetime-local"
            value={returnAt}
            onChange={(event) => setReturnAt(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Checking…" : "Check availability"}
        </button>
      </form>

      {message && <p role="status" className="message">{message}</p>}

      <div className="vehicle-grid" aria-live="polite">
        {vehicles.map((vehicle) => (
          <article
            className={
              selectedVehicle?.id === vehicle.id
                ? "vehicle-card selected"
                : "vehicle-card"
            }
            key={vehicle.id}
          >
            <span className="tag">Available</span>
            <h3>{vehicle.brand} {vehicle.model}</h3>
            <p>{vehicle.variant ?? "Standard variant"}</p>
            <dl>
              <div><dt>City</dt><dd>{vehicle.city}</dd></div>
              <div><dt>Fuel</dt><dd>{vehicle.fuel ?? "—"}</dd></div>
              <div><dt>Transmission</dt><dd>{vehicle.transmission ?? "—"}</dd></div>
              <div><dt>Seats</dt><dd>{vehicle.seats ?? "—"}</dd></div>
            </dl>
            <button
              type="button"
              className="text-button"
              onClick={() => chooseVehicle(vehicle)}
            >
              View rental packages
            </button>
          </article>
        ))}
      </div>

      {selectedVehicle && (
        <section className="package-section" aria-live="polite">
          <p className="eyebrow">Choose a package</p>
          <h3>{selectedVehicle.brand} {selectedVehicle.model}</h3>
          {packageBusy ? (
            <p className="muted">Loading packages…</p>
          ) : packages.length === 0 ? (
            <p className="muted">
              This operator has no active packages for this vehicle yet.
            </p>
          ) : (
            <div className="package-grid">
              {packages.map((item) => (
                <article className="package-card" key={item.id}>
                  <h4>{item.name}</h4>
                  <strong>{item.currency} {item.base_price}</strong>
                  <p>
                    {item.included_km} km included · Deposit {item.currency}{" "}
                    {item.deposit}
                  </p>
                  <CheckoutButton
                    vehicleId={selectedVehicle.id}
                    packageId={item.id}
                    pickupAt={new Date(pickupAt).toISOString()}
                    returnAt={new Date(returnAt).toISOString()}
                    serviceType={serviceType}
                    pickupLocation={pickupLocation}
                    returnLocation={returnLocation}
                    bookingTimezone={bookingTimezone}
                  />
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </section>
  );
}
