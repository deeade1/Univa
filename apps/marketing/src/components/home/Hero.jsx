
import { ArrowDown, ArrowRight, ShoppingBag, MessageCircle, Building2, Wallet, Truck, Play } from 'lucide-react';
import { Link } from 'react-router-dom';

const floatingServices = [
  { label: 'Shopping', icon: ShoppingBag, className: 'hero-float-shopping' },
  { label: 'Chat', icon: MessageCircle, className: 'hero-float-chat' },
  { label: 'Real estate', icon: Building2, className: 'hero-float-property' },
  { label: 'Banking', icon: Wallet, className: 'hero-float-banking' },
  { label: 'Logistics', icon: Truck, className: 'hero-float-logistics' },
];

export default function Hero() {
  return (
    <section className="hero-section">
      <div className="hero-glow hero-glow-one" />
      <div className="hero-glow hero-glow-two" />

      <div className="container hero-layout">
        <div className="hero-content">
          <span className="eyebrow">
            <span className="eyebrow-dot" />
            One platform. More possibilities.
          </span>

          <h1>
            Everything you need.
            <span className="hero-heading-accent"> All in Univa.</span>
          </h1>

          <p className="hero-description">
            Shop, connect, discover properties, explore financial services,
            and move goods and people. Univa brings more of everyday life
            together in one connected digital ecosystem.
          </p>

          <div className="hero-actions">
            <Link to="/about" className="button button-primary button-large">
              Discover Univa <ArrowRight size={19} />
            </Link>
            <Link to="/contact" className="button button-secondary button-large">
              <Play size={17} /> Talk to our team
            </Link>
          </div>

          <div className="hero-trust">
            <div className="hero-trust-mark" aria-hidden="true">
              <span>U</span>
            </div>
            <p>
              <strong>One connected ecosystem</strong>
              <span>Built around people, businesses, and opportunity.</span>
            </p>
          </div>
        </div>

        <div className="hero-visual" aria-label="Univa's connected services">
          <div className="hero-orbit hero-orbit-outer" />
          <div className="hero-orbit hero-orbit-inner" />

          <div className="hero-core">
            <span className="hero-core-mark">U</span>
            <span className="hero-core-name">univa</span>
            <span className="hero-core-caption">One connected world</span>
          </div>

          {floatingServices.map(({ label, icon: Icon, className }) => (
            <div className={`hero-float-card ${className}`} key={label}>
              <span className="hero-float-icon">
                <Icon size={21} />
              </span>
              <span>{label}</span>
            </div>
          ))}

          <div className="hero-visual-caption">
            <span className="hero-caption-dot" />
            Different services. One experience.
          </div>
        </div>
      </div>

      <a className="hero-scroll" href="#services">
        Explore the ecosystem <ArrowDown size={16} />
      </a>
    </section>
  );
}
