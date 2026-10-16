
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ShoppingBag,
  Clapperboard,
  MessageCircle,
  House,
  WalletCards,
  ChartNoAxesCombined,
  Truck,
  Compass,
  HeartHandshake,
  Lightbulb,
} from 'lucide-react';

const pillars = [
  {
    title: 'People first',
    description:
      'Create useful digital experiences around the needs of people and businesses.',
    icon: HeartHandshake,
  },
  {
    title: 'Connected by design',
    description:
      'Bring different services together in a wider, more coherent ecosystem.',
    icon: Compass,
  },
  {
    title: 'Built for possibility',
    description:
      'Make room for discovery, useful connections, and new opportunities.',
    icon: Lightbulb,
  },
];

const services = [
  { title: 'E-commerce', description: 'Products and shopping experiences.', icon: ShoppingBag, href: '/ecommerce' },
  { title: 'Social', description: 'Content, creators, and communities.', icon: Clapperboard, href: '/social' },
  { title: 'Chat', description: 'Conversations and group communication.', icon: MessageCircle, href: '/chat' },
  { title: 'Real Estate', description: 'Properties and location discovery.', icon: House, href: '/real-estate' },
  { title: 'Banking', description: 'Financial services and experiences.', icon: WalletCards, href: '/banking' },
  { title: 'Investments', description: 'Investment opportunities and information.', icon: ChartNoAxesCombined, href: '/investments' },
  { title: 'Transport & Logistics', description: 'Mobility, delivery, and logistics.', icon: Truck, href: '/transport' },
];

export default function About() {
  return (
    <main className="about-page">
      <section className="about-hero">
        <div className="container about-hero-layout">
          <div className="about-hero-copy">
            <span className="about-eyebrow">ABOUT UNIVA</span>
            <h1>
              Different needs.
              <span> One connected world.</span>
            </h1>
            <p>
              Univa brings a range of digital services together in one
              ecosystem, connecting everyday activities with new ways to
              discover, communicate, and do business.
            </p>
            <div className="about-hero-actions">
              <Link to="/#services" className="button button-primary">
                Explore our services <ArrowRight size={18} />
              </Link>
              <Link to="/contact" className="about-text-link">
                Talk to our team
              </Link>
            </div>
          </div>

          <div className="about-hero-art" aria-hidden="true">
            <div className="about-art-orbit about-art-orbit-one" />
            <div className="about-art-orbit about-art-orbit-two" />
            <div className="about-art-center">
              <span>U</span>
              <strong>univa</strong>
              <small>One connected ecosystem</small>
            </div>
            <span className="about-art-label about-art-label-one">People</span>
            <span className="about-art-label about-art-label-two">Business</span>
            <span className="about-art-label about-art-label-three">Opportunity</span>
          </div>
        </div>
      </section>

      <section className="about-intro section-padding">
        <div className="container about-intro-layout">
          <div>
            <span className="section-eyebrow">OUR PURPOSE</span>
            <h2>
              Make digital life
              <span> feel more connected.</span>
            </h2>
          </div>
          <div className="about-intro-copy">
            <p>
              People use different services to shop, communicate, explore
              property, manage financial activities, and move people or goods.
              Univa's vision is to bring these areas into a connected digital
              ecosystem.
            </p>
            <p>
              Each service has its own purpose, while contributing to a wider
              experience. We are building toward a platform where discovery
              and access feel more straightforward.
            </p>
          </div>
        </div>
      </section>

      <section className="about-pillars section-padding">
        <div className="container">
          <div className="about-section-heading">
            <span className="section-eyebrow">WHAT GUIDES US</span>
            <h2>Principles behind the platform.</h2>
            <p>
              The ideas that shape how we think about the Univa ecosystem.
            </p>
          </div>

          <div className="about-pillars-grid">
            {pillars.map(({ title, description, icon: Icon }, index) => (
              <article className="about-pillar-card" key={title}>
                <span className="about-pillar-number">0{index + 1}</span>
                <span className="about-pillar-icon">
                  <Icon size={25} />
                </span>
                <h3>{title}</h3>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="about-services section-padding" id="about-services">
        <div className="container">
          <div className="about-section-heading">
            <span className="section-eyebrow">THE ECOSYSTEM</span>
            <h2>Seven service areas. One wider vision.</h2>
            <p>
              Explore the areas that make up Univa's connected platform.
            </p>
          </div>

          <div className="about-services-grid">
            {services.map(({ title, description, icon: Icon, href }) => (
              <Link to={href} className="about-service-item" key={href}>
                <span className="about-service-icon">
                  <Icon size={21} />
                </span>
                <span className="about-service-text">
                  <strong>{title}</strong>
                  <small>{description}</small>
                </span>
                <ArrowRight size={17} className="about-service-arrow" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="about-closing">
        <div className="container">
          <div className="about-closing-panel">
            <div>
              <span className="about-eyebrow">LET'S CONNECT</span>
              <h2>Interested in what we're building?</h2>
              <p>
                Contact Univa to discuss business enquiries, partnerships,
                or other ways to connect with the team.
              </p>
            </div>
            <Link to="/contact" className="button about-closing-button">
              Contact Univa <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
