
import { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Menu, X, ArrowUpRight } from 'lucide-react';

const navigation = [
  { label: 'E-commerce', href: '/ecommerce' },
  { label: 'Social', href: '/social' },
  { label: 'Chat', href: '/chat' },
  { label: 'Real Estate', href: '/real-estate' },
  { label: 'Banking', href: '/banking' },
  { label: 'Transport', href: '/transport' },
];

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  return (
    <header className="site-header">
      <nav className="navbar container" aria-label="Main navigation">
        <Link
          to="/"
          className="brand"
          aria-label="Univa home"
          onClick={closeMenu}
        >
          <span className="brand-mark">U</span>
          <span className="brand-name">univa</span>
        </Link>

        <div className={`nav-links ${menuOpen ? 'nav-links-open' : ''}`}>
          {navigation.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                `nav-link${isActive ? ' nav-link-active' : ''}`
              }
              onClick={closeMenu}
            >
              {item.label}
            </NavLink>
          ))}

          <Link
            to="/contact"
            className="button button-primary nav-mobile-cta"
            onClick={closeMenu}
          >
            Get in touch <ArrowUpRight size={17} />
          </Link>
        </div>

        <Link to="/contact" className="button button-primary nav-desktop-cta">
          Get in touch <ArrowUpRight size={17} />
        </Link>

        <button
          type="button"
          className="mobile-menu-toggle"
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={menuOpen}
          aria-controls="mobile-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </nav>
      <div
        id="mobile-navigation"
        className={`mobile-nav-panel${menuOpen ? ' mobile-nav-panel-open' : ''}`}
      >
        <div className="container mobile-nav-inner">
          {navigation.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                `mobile-nav-link${isActive ? ' nav-link-active' : ''}`
              }
              onClick={closeMenu}
            >
              {item.label}
              <ArrowUpRight size={16} />
            </NavLink>
          ))}
          <Link
            to="/contact"
            className="mobile-nav-link"
            onClick={closeMenu}
          >
            Contact Univa <ArrowUpRight size={16} />
          </Link>
        </div>
      </div>
    </header>
  );
}
