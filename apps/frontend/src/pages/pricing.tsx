import { Col, Container, Row } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import Card from '../components/Card';
import ContactDetail from '../components/landing-modules/widgets/contact-detail';
import SubHeader from '../components/landing-modules/widgets/sub-header';

// ✅ 1. Define the Plan type fully
type Plan = {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  variant: string;
  buttonVariant: string;
  isHighlighted?: boolean;
};

// ✅ 2. Type the array of plans
const pricingPlans: Plan[] = [
  {
    name: 'Basic',
    price: '$25',
    period: '/month',
    description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
    features: ['10 users included', '2GB of storage', 'Email support'],
    variant: 'primary',
    buttonVariant: 'primary'
  },
  {
    name: 'Professional',
    price: '$25',
    period: '/month',
    description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
    features: ['10 users included', '2GB of storage', 'Email support'],
    variant: 'primary',
    buttonVariant: 'light',
    isHighlighted: true
  },
  {
    name: 'Startup',
    price: '$99',
    period: '/month',
    description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
    features: ['10 users included', '2GB of storage', 'Email support'],
    variant: 'primary',
    buttonVariant: 'primary'
  }
];

// ✅ 3. CheckIcon stays the same — it’s fine as is
const CheckIcon: React.FC<{ color?: string }> = ({ color = '#1AA053' }) => (
  <svg
    width="10"
    height="7"
    className="me-2"
    viewBox="0 0 10 7"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M3.81344 6.87296C3.58944 6.87296 3.36544 6.78796 3.19444 6.61696L0.821441 4.24396C0.479441 3.90196 0.479441 3.34797 0.821441 3.00696C1.16344 2.66496 1.71644 2.66396 2.05844 3.00596L3.81344 4.76096L7.94144 0.632965C8.28344 0.290965 8.83644 0.290965 9.17844 0.632965C9.52044 0.974965 9.52044 1.52896 9.17844 1.87096L4.43244 6.61696C4.26144 6.78796 4.03744 6.87296 3.81344 6.87296Z"
      fill={color}
    />
  </svg>
);

// ✅ 4. PricingCard with proper props typing
type PricingCardProps = {
  plan: Plan;
};

const PricingCard: React.FC<PricingCardProps> = ({ plan }) => {
  const textColor = plan.isHighlighted ? 'text-white' : 'text-primary';
  const iconColor = plan.isHighlighted ? '#ffffff' : '#1AA053';

  return (
    <Col>
      <Card className={plan.isHighlighted ? 'bg-primary' : ''}>
        <Card.Body>
          <p className={`mb-2 ${textColor}`}>{plan.name}</p>
          <h4 className={`mb-3 ${textColor}`}>
            {plan.price} <small>{plan.period}</small>
          </h4>
          <p className={`border-bottom pb-4 ${textColor}`}>{plan.description}</p>
          <ul className="list-unstyled pt-2">
            {plan.features.map((feature, index) => (
              <li key={index} className={`mb-2 ${textColor}`}>
                <CheckIcon color={iconColor} /> {feature}
              </li>
            ))}
          </ul>
          <Link
            to="#"
            className={`btn btn-${plan.buttonVariant} w-100 mt-4`}
          >
            Get Started
          </Link>
        </Card.Body>
      </Card>
    </Col>
  );
};

// ✅ 5. Pricing page — same but now fully typed!
const Pricing: React.FC = () => {
  return (
    <>
      <SubHeader title="Pricing Plan" />

      <div className="section-card-padding">
        <Container>
          <Row className="mb-5">
            <Col md={12} className="text-center">
              <p className="mb-2 text-uppercase text-primary">PRICE PLAN</p>
              <h2 className="text-secondary mb-4">
                Some Of Our <span className="text-primary">Selected Projects</span>
              </h2>
            </Col>
          </Row>

          <Row className="row-cols-1 row-cols-lg-3">
            {pricingPlans.map((plan, index) => (
              <PricingCard key={index} plan={plan} />
            ))}
          </Row>
        </Container>
      </div>

      <div className="section-padding bg-white">
        <ContactDetail />
      </div>
    </>
  );
};

export default Pricing;
