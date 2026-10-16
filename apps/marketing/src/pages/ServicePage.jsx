
import { Link, Navigate, useParams } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Check } from 'lucide-react';
import { services } from '../data/services';

export default function ServicePage() {
  const { slug } = useParams();
  const service = services[slug];

  if (!service) {
    return <Navigate to="/" replace />;
  }

  const Icon = service.icon;

  return (
    <main
      className="service-landing"
      style={{
        '--service-accent': service.accent,
        '--service-tint': service.tint,
      }}
    >
      <section className="service-landing-hero">
        <div className="container service-landing-layout">
          <div className="service-landing-copy">
            <div className="service-breadcrumb">
              <Link to="/">Home</Link>
              <span>/</span>
              <span>{service.title}</span>
            </div>

            <span className="service-landing-eyebrow">
              <span className="service-landing-dot" />
              {service.eyebrow}
            </span>

            <h1>{service.headline}</h1>

            <p className="service-landing-description">
              {service.description}
            </p>

            <div className="service-landing-actions">
              <Link
                to={service.ctaHref}
                className="button service-landing-primary"
              >
                {service.cta} <ArrowRight size={18} />
              </Link>

              <a href="#service-benefits" className="service-landing-secondary">
                Explore the possibilities <ArrowUpRight size={17} />
              </a>
            </div>

            <div className="service-landing-note">
              <Check size={17} />
              <span>Part of the connected Univa ecosystem</span>
            </div>
          </div>

          <div className="service-showcase">
            <div className="service-showcase-orbit service-showcase-orbit-one" />
            <div className="service-showcase-orbit service-showcase-orbit-two" />

            <div className="service-showcase-card">
              <div className="service-showcase-top">
                <span className="service-showcase-brand">
                  <span className="service-showcase-brand-mark">U</span>
                  univa
                </span>
                <span className="service-showcase-number">
                  {service.number}
                </span>
              </div>

              <div className="service-showcase-icon">
                <Icon size={45} strokeWidth={1.6} />
              </div>

              <span className="service-showcase-label">
                THE UNIVA ECOSYSTEM
              </span>

              <h2>{service.title}</h2>

              <p>{service.description}</p>

              <div className="service-showcase-footer">
                <span>Connected by design</span>
                <ArrowUpRight size={18} />
              </div>
            </div>

            <span className="service-floating-label service-floating-label-one">
              <Check size={15} /> Connected
            </span>

            <span className="service-floating-label service-floating-label-two">
              Discover more
            </span>
          </div>
        </div>
      </section>

      <section
        className="service-benefits section-padding"
        id="service-benefits"
      >
        <div className="container">
          <div className="service-benefits-heading">
            <span className="section-eyebrow">
              EXPLORE {service.title.toUpperCase()}
            </span>

            <h2>
              Designed around
              <span> what matters.</span>
            </h2>

            <p>
              Discover the ideas behind this part of Univa and how it fits
              into a more connected digital experience.
            </p>
          </div>

          <div className="service-benefits-grid">
            {service.benefits.map((benefit, index) => (
              <article className="service-benefit-card" key={benefit.title}>
                <span className="service-benefit-number">
                  0{index + 1}
                </span>

                <div className="service-benefit-icon">
                  <Icon size={23} strokeWidth={1.8} />
                </div>

                <h3>{benefit.title}</h3>
                <p>{benefit.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="service-closing">
        <div className="container">
          <div className="service-closing-panel">
            <div>
              <span className="service-closing-eyebrow">
                ONE CONNECTED ECOSYSTEM
              </span>

              <h2>
                There is more to discover with Univa.
              </h2>

              <p>
                Explore the wider ecosystem and discover how its different
                services come together.
              </p>
            </div>

            <Link to="/#services" className="button service-closing-button">
              Explore all services <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
