import { Col, Container, Row } from 'react-bootstrap';
import { Link } from 'react-router-dom';

// Social media icons
import facebookIcon from '@/assets/images/brands/08.png';
import googleIcon from '@/assets/images/brands/09.png';
import instagramIcon from '@/assets/images/brands/10.png';
import linkedinIcon from '@/assets/images/brands/13.png';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  // TODO: replace placeholder URLs with real social profiles
  const socialIcons = [
    { src: facebookIcon, alt: 'Facebook', href: 'https://facebook.com/' },
    { src: googleIcon,   alt: 'Google',   href: 'https://google.com/' },
    { src: instagramIcon, alt: 'Instagram', href: 'https://instagram.com/' },
    { src: linkedinIcon, alt: 'LinkedIn', href: 'https://linkedin.com/' },
  ];

  // Real routes for links section
  const linksSection = [
    {
      title: 'Company',
      items: [
        { label: 'About us', to: '/about' },
        { label: 'Features', to: '/features' },
        { label: 'Pricing',  to: '/pricing' },
        { label: 'Contact',  to: '/contact' },
      ],
    },
    {
      title: 'Help',
      items: [
        { label: 'My Account', to: '/account' },
        { label: 'FAQ',        to: '/faq' },
        // Add these routes when the pages exist:
        // { label: 'Returns & Refunds', to: '/refunds' },
        // { label: 'Payment Policy',    to: '/payment-policy' },
      ],
    },
  ];

  return (
    <footer className="footer">
      <div className="inner-box">
        <Container>
          <Row>
            <Col md={4}>
              <Link to="/" className="navbar-brand d-flex align-items-center">
                <svg
                  className="icon-30 text-primary"
                  width="30"
                  viewBox="0 0 30 30"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  {/* Logo paths */}
                </svg>
                <h4 className="logo-title ms-3">Univa</h4>
              </Link>

              {/* TODO: replace with real product description */}
              <p className="my-4">
                Unified banking, payments, and commerce — in one app.
              </p>

              {/* TODO: replace with real business address */}
              <div className="d-flex align-items-center mb-4">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  {/* Address icon */}
                </svg>
                <p className="ms-4 mb-0">2798 Meadow Lane, Napa, California- 94559</p>
              </div>

              {/* TODO: replace with real phone number */}
              <div className="d-flex align-items-center">
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
                  {/* Phone icon */}
                </svg>
                <p className="ms-4 mb-0">(808) 555-0111</p>
              </div>
            </Col>

            {linksSection.map((section, index) => (
              <Col md={2} className="mt-md-0 mt-4" key={index}>
                <h5 className="mb-4">{section.title}</h5>
                <ul className="m-0 p-0 list-unstyled">
                  {section.items.map((item, itemIndex) => (
                    <li className="mb-3" key={itemIndex}>
                      <Link to={item.to}>{item.label}</Link>
                    </li>
                  ))}
                </ul>
              </Col>
            ))}

            <Col md={4} className="mt-md-0 mt-4">
              <h5 className="mb-4">Newsletter</h5>
              {/* TODO: wire up subscribe handler */}
              <form
                className="input-group mb-4"
                onSubmit={(e) => e.preventDefault()}
              >
                <input
                  type="email"
                  className="form-control input-email ps-0"
                  placeholder="Email Address"
                  aria-label="Email Address"
                  required
                />
                <button className="input-group-text input-email-btn" type="submit">
                  Subscribe
                </button>
              </form>

              <ul className="list-unstyled p-0 m-0 d-flex mt-4">
                {socialIcons.map((icon, index) => (
                  <li className={index > 0 ? "ps-3" : ""} key={index}>
                    <a
                      href={icon.href}
                      target="_blank"
                      rel="noreferrer noopener"
                      aria-label={icon.alt}
                    >
                      <img
                        src={icon.src}
                        alt={icon.alt}
                        loading="lazy"
                        className="rounded-pill"
                        width="40"
                        height="40"
                      />
                    </a>
                  </li>
                ))}
              </ul>
            </Col>
          </Row>
        </Container>
      </div>

      <div className="footer-bottom">
        <Container>
          <Row>
            <Col md={12} className="text-center">
              <p className="mb-0">© {currentYear} Univa. All rights reserved.</p>
            </Col>
          </Row>
        </Container>
      </div>
    </footer>
  );
};

export default Footer;