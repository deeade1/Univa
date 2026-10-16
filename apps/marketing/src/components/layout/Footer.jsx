
import {
  ArrowUpRight,
  Mail,
  MapPin,
  Globe,
  Users,
  BriefcaseBusiness,
} from 'lucide-react';
import { Link } from 'react-router-dom';

const serviceLinks = [
  { label: 'E-commerce', href: '/ecommerce' },
  { label: 'Social', href: '/social' },
  { label: 'Chat', href: '/chat' },
  { label: 'Real Estate', href: '/real-estate' },
  { label: 'Banking', href: '/banking' },
  { label: 'Investments', href: '/investments' },
  { label: 'Transport & Logistics', href: '/transport' },
];

const companyLinks = [
  { label: 'About Univa', href: '/about' },
  { label: 'Contact', href: '/contact' },
];

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-main">
          <div className="footer-brand-column">
            <Link to="/" className="brand footer-brand" aria-label="Univa home">
              <span className="brand-mark">U</span>
              <span className="brand-name">univa</span>
            </Link>

            <p className="footer-description">
              One connected digital ecosystem bringing services, people,
              businesses, and opportunities closer together.
            </p>

            <div className="footer-socials" aria-label="Explore Univa">
              <Link to="/social" aria-label="Explore social">
                <Users size={18} />
              </Link>
              <Link to="/about" aria-label="About Univa">
                <Globe size={18} />
              </Link>
              <Link to="/contact" aria-label="Business enquiries">
                <BriefcaseBusiness size={18} />
              </Link>
            </div>
          </div>

          <div className="footer-link-column">
            <h3>Explore</h3>
            {serviceLinks.map((item) => (
              <Link key={item.href} to={item.href}>
                {item.label}
              </Link>
            ))}
          </div>

          <div className="footer-link-column">
            <h3>Company</h3>
            {companyLinks.map((item) => (
              <Link key={item.href} to={item.href}>
                {item.label}
              </Link>
            ))}
            <a href="#services">
              Our ecosystem <ArrowUpRight size={14} />
            </a>
          </div>

          <div className="footer-contact-column">
            <h3>Let's connect</h3>
            <p>
              Interested in Univa, a partnership, or working with us? We'd
              love to hear from you.
            </p>

            <Link to="/contact" className="footer-contact-link">
              Contact our team <ArrowUpRight size={17} />
            </Link>

            <div className="footer-contact-note">
              <Mail size={16} />
              <span>Use our contact page to reach the team.</span>
            </div>

            <div className="footer-contact-note">
              <MapPin size={16} />
              <span>Serving a connected digital community.</span>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <p>© {currentYear} Univa. All rights reserved.</p>

          <div className="footer-legal-links">
            <Link to="/privacy">Privacy</Link>
            <Link to="/terms">Terms</Link>
          </div>

          <a className="footer-back-to-top" href="#top">
            Back to top <ArrowUpRight size={15} />
          </a>
        </div>
      </div>
    </footer>
  );
}
