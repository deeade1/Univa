import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { Navbar, Container, Nav } from "react-bootstrap";
import Logo from "@/components/partials/components/logo";

// Primary navigation — marketing routes only
const MARKETING_NAV_ITEMS = [
  { path: "/", label: "Home", exact: true },
  { path: "/about", label: "About" },
  { path: "/features", label: "Features" },
  { path: "/pricing", label: "Pricing" },
  { path: "/faq", label: "FAQ" },
  { path: "/contact", label: "Contact" },
];

export default function LandingHeader() {
  const location = useLocation();
  const [expanded, setExpanded] = useState(false);

  const handleToggle = () => setExpanded(!expanded);
  const handleClose = () => setExpanded(false);

  const isActive = (path: string, exact?: boolean) =>
    exact ? location.pathname === path : location.pathname.startsWith(path);

  return (
    <Navbar
      bg="dark"
      expand="lg"
      variant="dark"
      expanded={expanded}
      onToggle={handleToggle}
      className="fixed-top navbar"
      aria-label="Main navigation"
    >
      <Container fluid>
        <Link to="/" className="navbar-brand d-flex align-items-center">
          <Logo color={true} />
          <h4 className="logo-title text-light ms-3 mb-0">Univa</h4>
        </Link>

        <Navbar.Toggle
          className="p-0 border-0"
          aria-controls="navbarSideCollapse"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon">
            <span className="navbar-toggler-bar bar1 mt-2"></span>
            <span className="navbar-toggler-bar bar2"></span>
            <span className="navbar-toggler-bar bar3"></span>
          </span>
        </Navbar.Toggle>

        <Navbar.Collapse
          id="navbarSideCollapse"
          className="navbar-collapse offcanvas-collapse open"
        >
          <Nav as="ul" className="navbar-nav me-auto mb-2 mb-lg-0 align-items-center">
            {MARKETING_NAV_ITEMS.map((item) => (
              <Nav.Item as="li" key={item.path}>
                <Link
                  to={item.path}
                  className={`nav-link ${isActive(item.path, item.exact) ? "active" : ""}`}
                  onClick={handleClose}
                >
                  {item.label}
                </Link>
              </Nav.Item>
            ))}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}