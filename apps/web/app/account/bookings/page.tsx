import { redirect } from "next/navigation";
import LogoutButton from "../../../components/LogoutButton";
import { authenticatedFetch } from "../../../lib/server-api";

type Booking = {
  id: string;
  booking_number: string;
  vehicle_id: string;
  pickup_at: string;
  return_at: string;
  status: string;
  currency: string;
  total_amount: string;
  deposit_amount: string;
};

export default async function BookingsPage() {
  const response = await authenticatedFetch("/bookings");
  if (response.status === 401) redirect("/login");
  const bookings: Booking[] = response.ok ? await response.json() : [];

  return (
    <main className="portal-page">
      <header className="portal-header">
        <a className="brand dark-brand" href="/">PYRO <span>RENTALS</span></a>
        <LogoutButton />
      </header>
      <section className="portal-panel wide">
        <p className="eyebrow">My rentals</p>
        <h1>Bookings</h1>
        {bookings.length === 0 ? (
          <div className="empty-state">
            <h2>No bookings yet</h2>
            <p>Search live inventory and choose a package to start a rental.</p>
            <a className="primary-link" href="/">Search vehicles</a>
          </div>
        ) : (
          <div className="booking-list">
            {bookings.map((booking) => (
              <article className="booking-row" key={booking.id}>
                <div>
                  <strong>{booking.booking_number}</strong>
                  <p>{new Date(booking.pickup_at).toLocaleString()} → {new Date(booking.return_at).toLocaleString()}</p>
                </div>
                <div><span className="status-pill">{booking.status}</span></div>
                <div>
                  <strong>{booking.currency} {booking.total_amount}</strong>
                  <p>Deposit {booking.currency} {booking.deposit_amount}</p>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
