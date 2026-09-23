import SearchPanel from "../components/SearchPanel";

const services = ["Self Drive", "With Driver", "Airport Transfer", "Outstation", "Corporate"];

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <nav className="nav" aria-label="Primary navigation">
          <a className="brand" href="#">PYRO <span>RENTALS</span></a>
          <div className="nav-links">
            <a href="#services">Services</a><a href="#how">How it works</a><a href="#trust">Safety</a>
          </div>
          <a className="secondary" href="/login">Sign in</a>
        </nav>
        <div className="hero-copy">
          <p className="eyebrow">Vehicle rentals, without the guesswork</p>
          <h1>Your trip. Your dates. <em>The right vehicle.</em></h1>
          <p className="hero-text">
            Book self-drive or chauffeur vehicles with clear pricing, verified availability and a digital handover trail from pickup to return.
          </p>
          <div className="trust-row">
            <span>Exact inventory</span><span>Clear price breakdown</span><span>Secure KYC flow</span>
          </div>
        </div>
      </section>
      <SearchPanel />
      <section id="services" className="section">
        <p className="eyebrow">One marketplace</p><h2>Rent for the way you travel</h2>
        <div className="service-grid">
          {services.map((service, index) => (
            <article key={service}>
              <span>0{index + 1}</span><h3>{service}</h3>
              <p>Configurable inventory and pricing for each service, backed by the same booking and settlement controls.</p>
            </article>
          ))}
        </div>
      </section>
      <section id="how" className="split section">
        <div><p className="eyebrow">Built around inventory</p><h2>No driver-matching theatre.</h2></div>
        <div><p>PYRO RENTALS asks one operational question: can this exact vehicle be rented for this exact period? Search, quote, payment and handover all respect that same source of truth.</p></div>
      </section>
      <footer><strong>PYRO RENTALS</strong><span>Inventory-first rental marketplace</span></footer>
    </main>
  );
}
