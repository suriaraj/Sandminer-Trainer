"use client";

import { useState } from "react";

type Props = {
  vehicleId: string;
  packageId: string;
  pickupAt: string;
  returnAt: string;
  serviceType: string;
  pickupLocation: string;
  returnLocation: string;
  bookingTimezone: string;
};

export default function CheckoutButton(props: Props) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function book() {
    setBusy(true);
    setMessage("");
    const response = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vehicle_id: props.vehicleId,
        package_id: props.packageId,
        pickup_at: props.pickupAt,
        return_at: props.returnAt,
        service_type: props.serviceType,
        pickup_location: props.pickupLocation,
        return_location: props.returnLocation,
        booking_timezone: props.bookingTimezone
      })
    });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      setMessage(body?.error?.message ?? body?.detail ?? "Booking could not be created.");
      setBusy(false);
      return;
    }
    window.location.href = "/account/bookings";
  }

  return (
    <div>
      <button className="primary-button" type="button" onClick={book} disabled={busy}>
        {busy ? "Reserving…" : "Reserve this package"}
      </button>
      {message && <p className="message" role="alert">{message}</p>}
    </div>
  );
}
