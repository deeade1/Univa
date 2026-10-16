
import {
  ShoppingBag,
  Clapperboard,
  MessageCircle,
  House,
  WalletCards,
  Truck,
  ArrowUpRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';

const services = [
  {
    number: '01',
    title: 'E-commerce',
    description:
      'Discover products, explore shops, and bring the shopping experience together.',
    href: '/ecommerce',
    label: 'Explore shopping',
    icon: ShoppingBag,
    className: 'service-blue',
  },
  {
    number: '02',
    title: 'Social',
    description:
      'Discover content, follow creators, share ideas, and find your community.',
    href: '/social',
    label: 'Discover social',
    icon: Clapperboard,
    className: 'service-violet',
  },
  {
    number: '03',
    title: 'Chat',
    description:
      'Bring conversations and group communication into your connected world.',
    href: '/chat',
    label: 'Explore chat',
    icon: MessageCircle,
    className: 'service-teal',
  },
  {
    number: '04',
    title: 'Real Estate',
    description:
      'Explore properties, discover locations, and connect with property opportunities.',
    href: '/real-estate',
    label: 'Discover properties',
    icon: House,
    className: 'service-orange',
  },
  {
    number: '05',
    title: 'Banking & Investments',
    description:
      'Discover financial services and investment opportunities within the ecosystem.',
    href: '/banking',
    label: 'Explore finance',
    icon: WalletCards,
    className: 'service-green',
  },
  {
    number: '06',
    title: 'Transport & Logistics',
    description:
      'Connect mobility, deliveries, and logistics through a unified platform.',
    href: '/transport',
    label: 'Explore mobility',
    icon: Truck,
    className: 'service-pink',
  },
];

export default function ServiceGrid() {
  return (
    <section className="services-section section-padding" id="services">
      <div className="container">
        <div className="section-heading-row">
          <div className="section-heading-content">
            <span className="section-eyebrow">THE UNIVA ECOSYSTEM</span>
            <h2>
              More of life,
              <span className="text-primary"> connected.</span>
            </h2>
            <p>
              Explore a growing ecosystem designed to bring everyday services,
              digital experiences, and new opportunities closer together.
            </p>
          </div>

          <Link to="/about" className="text-link services-overview-link">
            About Univa <ArrowUpRight size={18} />
          </Link>
        </div>

        <div className="services-grid">
          {services.map(({ number, title, description, href, label, icon: Icon, className }) => (
            <article className={`service-card ${className}`} key={href}>
              <div className="service-card-top">
                <span className="service-icon">
                  <Icon size={25} strokeWidth={1.8} />
                </span>
                <span className="service-number">{number}</span>
              </div>

              <div className="service-card-body">
                <h3>{title}</h3>
                <p>{description}</p>
              </div>

              <Link to={href} className="service-card-link" aria-label={label}>
                <span>{label}</span>
                <ArrowUpRight size={18} />
              </Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
