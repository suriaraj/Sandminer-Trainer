import { redirect } from "next/navigation";
import { authenticatedFetch } from "../../lib/server-api";
import AdminApprovals from "../../components/AdminApprovals";

type Kpis = {
  total_users: number;
  total_operators: number;
  total_vehicles: number;
  available_vehicles: number;
  total_bookings: number;
  active_rentals: number;
  captured_revenue: string;
  pending_kyc: number;
};

export default async function AdminPage() {
  const response = await authenticatedFetch("/admin/kpis");
  if (response.status === 401) redirect("/login");
  if (response.status === 403) {
    return (
      <main className="portal-page">
        <h1>Administrator access required</h1>
        <p>This workspace is restricted by server-side role permissions.</p>
        <a href="/account/bookings">Return to bookings</a>
      </main>
    );
  }
  const kpis: Kpis | null = response.ok ? await response.json() : null;
  const items = kpis ? [
    ["Customers", kpis.total_users],
    ["Operators", kpis.total_operators],
    ["Vehicles", kpis.total_vehicles],
    ["Available vehicles", kpis.available_vehicles],
    ["Bookings", kpis.total_bookings],
    ["Active rentals", kpis.active_rentals],
    ["Pending KYC", kpis.pending_kyc],
    ["Captured revenue (INR)", kpis.captured_revenue],
  ] : [];

  return (
    <main className="portal-page">
      <header className="portal-header">
        <a className="brand dark-brand" href="/">PYRO <span>RENTALS</span></a>
        <a className="secondary-button" href="/operator">Operator workspace</a>
      </header>
      <section className="portal-panel wide">
        <p className="eyebrow">Authorized operations</p>
        <h1>Administrator console</h1>
        <p className="muted">
          These KPIs are calculated by the backend, not generated from
          fake frontend arrays. Approval and KYC review endpoints require
          explicit administrator permissions.
        </p>
        {kpis ? (
          <div className="vehicle-grid">
            {items.map(([label, value]) => (
              <article className="vehicle-card" key={label}>
                <p>{label}</p>
                <h2>{value}</h2>
              </article>
            ))}
          </div>
        ) : <p role="alert">Unable to retrieve administrator data.</p>}
        <AdminApprovals />
      </section>
    </main>
  );
}
