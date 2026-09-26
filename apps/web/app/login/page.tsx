import AuthForm from "../../components/AuthForm";

export default function LoginPage() {
  return (
    <main className="portal-page">
      <a className="brand dark-brand" href="/">PYRO <span>RENTALS</span></a>
      <section className="portal-panel">
        <p className="eyebrow">Secure account</p>
        <h1>Manage every rental in one place.</h1>
        <p className="muted">
          Sign in to create bookings, complete KYC and view your rental history.
        </p>
        <AuthForm />
      </section>
    </main>
  );
}
