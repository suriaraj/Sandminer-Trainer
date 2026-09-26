import { redirect } from "next/navigation";
import OperatorRegistration from "../../components/OperatorRegistration";
import InventoryForms from "../../components/InventoryForms";
import { authenticatedFetch } from "../../lib/server-api";

type Operator = { id: string; business_name: string; status: string };
type Vehicle = { id: string; brand: string; model: string; city: string; status: string };

export default async function OperatorPage() {
  const response = await authenticatedFetch("/operator/profile");
  if (response.status === 401) redirect("/login");
  const operators: Operator[] = response.ok ? await response.json() : [];
  const categoriesResponse = await authenticatedFetch("/vehicle-categories");
  const categories: { id: string; name: string }[] = categoriesResponse.ok
    ? await categoriesResponse.json() : [];
  const fleet = operators.length
    ? await authenticatedFetch("/operator/vehicles") : null;
  const vehicles: Vehicle[] = fleet?.ok ? await fleet.json() : [];

  return (
    <main className="portal-page">
      <header className="portal-header">
        <a className="brand dark-brand" href="/">PYRO <span>RENTALS</span></a>
        <div className="portal-actions">
          <a className="secondary-button" href="/account/bookings">My bookings</a>
          <a className="secondary-button" href="/admin">Admin</a>
        </div>
      </header>
      <section className="portal-panel wide">
        <p className="eyebrow">Business operations</p>
        <h1>Operator workspace</h1>
        <p className="muted">
          Onboard a fleet and keep rental inventory separate for each operator.
          Add vehicles and configure service-specific pricing. Listings remain
          inactive until administrator approval.
        </p>
        <div className="kyc-grid">
          <OperatorRegistration />
          <section className="auth-card">
            <h2>Your operators</h2>
            {operators.length === 0
              ? <p>No fleet businesses have been registered yet.</p>
              : operators.map((item) => (
                <p className="case-row" key={item.id}>
                  {item.business_name} <strong>{item.status}</strong>
                </p>
              ))}
          </section>
        </div>
        <InventoryForms operators={operators} categories={categories} />
        <section className="auth-card">
          <h2>Fleet inventory</h2>
          {vehicles.length === 0
            ? <p>No vehicles yet. Create vehicles and rental packages using the operator API.</p>
            : vehicles.map((vehicle) => (
              <p className="case-row" key={vehicle.id}>
                {vehicle.brand} {vehicle.model} · {vehicle.city} · <strong>{vehicle.status}</strong>
              </p>
            ))}
        </section>
      </section>
    </main>
  );
}
