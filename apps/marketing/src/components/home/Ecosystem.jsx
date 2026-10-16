
import {
  ArrowRight,
  ShoppingBag,
  Users,
  MessageCircle,
  House,
  WalletCards,
  Truck,
} from 'lucide-react';
import { Link } from 'react-router-dom';

const ecosystemItems = [
  { label: 'Commerce', icon: ShoppingBag },
  { label: 'Community', icon: Users },
  { label: 'Communication', icon: MessageCircle },
  { label: 'Property', icon: House },
  { label: 'Finance', icon: WalletCards },
  { label: 'Mobility', icon: Truck },
];

export default function Ecosystem() {
  return (
    <section className="ecosystem-section section-padding">
      <div className="container">
        <div className="ecosystem-panel">
          <div className="ecosystem-copy">
            <span className="ecosystem-eyebrow">
              MORE THAN INDIVIDUAL SERVICES
            </span>

            <h2>
              One ecosystem.
              <span> Countless possibilities.</span>
            </h2>

            <p>
              Everyday needs are connected. Univa brings shopping,
              communication, community, property, financial services, and
              mobility into a shared digital ecosystem designed to make
              discovering and accessing services simpler.
            </p>

            <Link to="/about" className="button ecosystem-button">
              Get to know Univa <ArrowRight size={18} />
            </Link>
          </div>

          <div className="ecosystem-visual">
            <div className="ecosystem-orbit ecosystem-orbit-outer" />
            <div className="ecosystem-orbit ecosystem-orbit-inner" />

            <div className="ecosystem-center">
              <span className="ecosystem-center-mark">U</span>
              <span>univa</span>
              <small>Connected by design</small>
            </div>

            {ecosystemItems.map(({ label, icon: Icon }, index) => (
              <div
                className={`ecosystem-node ecosystem-node-${index + 1}`}
                key={label}
              >
                <span className="ecosystem-node-icon">
                  <Icon size={19} />
                </span>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
