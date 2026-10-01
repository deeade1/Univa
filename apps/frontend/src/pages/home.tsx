import React from "react";
import { Container, Row, Col, Card, Button } from "react-bootstrap";
import { LinkContainer } from "react-router-bootstrap";
import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation, Autoplay, Pagination } from "swiper/modules";
import { FaCar, FaTruck, FaShoppingBag, FaHome, FaUsers } from "react-icons/fa";
import { BsWallet2 } from "react-icons/bs";

// Widgets
import Team from "@/components/landing-modules/widgets/team";
import BlogWidget, { BlogPost } from "@/components/landing-modules/widgets/blog-widget";
import TestimonialOne from "@/components/landing-modules/widgets/testimonial-one";
import Client from "@/components/landing-modules/widgets/partner";

// Assets
import heroImage from "@/assets/images/home-1/01.webp";
import partnerLogo1 from "@/assets/images/home-1/appstore.webp";
import partnerLogo2 from "@/assets/images/home-1/three.webp";
import partnerLogo3 from "@/assets/images/home-1/one.webp";

import "swiper/css";
import "swiper/css/navigation";
import "swiper/css/pagination";

const AUTOPLAY_DELAY = 5000;

// Dummy Data
const blogs: BlogPost[] = [
  {
    id: 1,
    image: "/images/blog/01.webp",
    date: "August 10, 2025",
    title: "Univa Launches Wallet Feature",
    author: "Admin",
    description: "You can now make seamless payments with Univa Wallet...",
  },
  {
    id: 2,
    image: "/images/blog/02.webp",
    date: "August 5, 2025",
    title: "Delivery Expansion",
    author: "Admin",
    description: "We’ve expanded our delivery service to new cities...",
  },
  {
    id: 3,
    image: "/images/blog/03.webp",
    date: "July 28, 2025",
    title: "Ride Hailing Safety",
    author: "Admin",
    description: "Univa introduces new safety measures for riders...",
  },
];

const services = [
  { title: "Ride Hailing", description: "Book rides with ease across the city.", icon: <FaCar size={32} /> },
  { title: "Delivery", description: "Fast and reliable package delivery.", icon: <FaTruck size={32} /> },
  { title: "Marketplace", description: "Shop and sell products on our marketplace.", icon: <FaShoppingBag size={32} /> },
  { title: "Real Estate", description: "Find homes and properties to rent or buy.", icon: <FaHome size={32} /> },
  { title: "Wallet", description: "Seamless payments with our wallet system.", icon: <BsWallet2 size={32} /> },
  { title: "Community", description: "Connect with people around you.", icon: <FaUsers size={32} /> },
];

const features = [
  { icon: <FaCar size={28} />, title: "On-demand Rides", description: "Request a ride anytime, anywhere." },
  { icon: <FaTruck size={28} />, title: "Reliable Delivery", description: "Deliver packages securely and on time." },
  { icon: <BsWallet2 size={28} />, title: "Digital Wallet", description: "Pay easily within the app." },
];

const counters = [
  { title: "Rides Completed", value: 12000, suffix: "+" },
  { title: "Active Users", value: 4500, suffix: "+" },
  { title: "Deliveries", value: 8000, suffix: "+" },
  { title: "Partners", value: 500, suffix: "+" },
];

const testimonials = [
  { name: "Jane Doe", role: "Rider", text: "The rides are always smooth and drivers are professional." },
  { name: "John Smith", role: "Vendor", text: "I sell daily on the marketplace, it's been amazing." },
  { name: "Ada Obi", role: "Delivery User", text: "Fast delivery service! Highly recommend." },
];

const teamData = [
  { teamImage: "/images/team1.jpg", teamTitle: "Alice Johnson", teamText: "CEO" },
  { teamImage: "/images/team2.jpg", teamTitle: "Bob Williams", teamText: "CTO" },
  { teamImage: "/images/team3.jpg", teamTitle: "Jane Smith", teamText: "Lead Designer" },
];

const partners = [partnerLogo1, partnerLogo2, partnerLogo3];

const UnivaHomepage: React.FC = () => {
  return (
    <main className="homepage">
      {/* 1. Hero */}
      <section className="hero bg-light text-center py-5">
        <Container>
          <Row className="align-items-center">
            <Col md={6} className="text-md-start text-center">
              <h1 className="mb-4">Welcome to Univa</h1>
              <p className="lead mb-4">Your all-in-one platform for rides, delivery, shopping, and more.</p>
              <LinkContainer to="/auth/account">
                <Button variant="primary">Get Started</Button>
              </LinkContainer>
            </Col>
            <Col md={6}>
              <img src={heroImage} alt="Univa Hero" className="img-fluid" />
            </Col>
          </Row>
        </Container>
      </section>

      {/* 2. Services */}
      <section className="services bg-white py-5">
        <Container>
          <Row className="text-center mb-5">
            <Col>
              <h2>Our Services</h2>
              <p className="text-muted">Discover everything Univa has to offer.</p>
            </Col>
          </Row>
          <Row>
            {services.map((service, idx) => (
              <Col md={4} className="mb-4" key={idx}>
                <Card className="h-100 shadow-sm text-center">
                  <Card.Body>
                    <div className="mb-3 text-primary">{service.icon}</div>
                    <Card.Title>{service.title}</Card.Title>
                    <Card.Text>{service.description}</Card.Text>
                    <LinkContainer
                      to={`/services/${service.title.toLowerCase().replace(/\s+/g, "-")}`}
                    >
                      <Button variant="outline-primary" size="sm">
                        Learn More
                      </Button>
                    </LinkContainer>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>
        </Container>
      </section>

      {/* 3. Why Choose Us (features + counters merged) */}
      <section className="why-choose bg-alt py-5">
        <Container>
          <Row className="text-center mb-5">
            <Col>
              <h2>Why Choose Us</h2>
              <p className="text-muted">Experience convenience and reliability with Univa.</p>
            </Col>
          </Row>
          <Row>
            {features.map((feature, idx) => (
              <Col md={4} className="mb-4" key={idx}>
                <div className="p-4 bg-white shadow-sm rounded text-center h-100">
                  <div className="mb-3 text-primary">{feature.icon}</div>
                  <h5>{feature.title}</h5>
                  <p className="text-muted">{feature.description}</p>
                </div>
              </Col>
            ))}
          </Row>
          <Row className="mt-5 text-center text-white">
            {counters.map((counter, idx) => (
              <Col md={3} sm={6} key={idx}>
                <h2>
                  {counter.value}
                  {counter.suffix}
                </h2>
                <p>{counter.title}</p>
              </Col>
            ))}
          </Row>
        </Container>
      </section>

      {/* 4. Testimonials */}
      <section className="testimonials bg-white py-5 text-center">
        <Container>
          <Row className="mb-5">
            <Col>
              <h2>What Our Users Say</h2>
              <p className="text-muted">Hear directly from people using Univa every day.</p>
            </Col>
          </Row>
          <Swiper
            modules={[Navigation, Autoplay]}
            autoplay={{ delay: AUTOPLAY_DELAY }}
            loop={testimonials.length > 1}
            navigation
            spaceBetween={30}
            slidesPerView={1}
          >
            {testimonials.map((t, idx) => (
              <SwiperSlide key={idx}>
                <TestimonialOne id={idx} text={t.text} author={t.name} role={t.role} rating={5} />
              </SwiperSlide>
            ))}
          </Swiper>
        </Container>
      </section>

      {/* 5. Blog */}
      <section className="blog bg-alt py-5">
        <Container>
          <Row className="text-center mb-5">
            <Col>
              <h2>Latest Updates</h2>
              <p className="text-muted">Stay informed with our blog.</p>
            </Col>
          </Row>
          <Swiper
            modules={[Pagination, Autoplay]}
            pagination={{ clickable: true }}
            autoplay={{ delay: 3000 }}
            spaceBetween={30}
            slidesPerView={3}
            breakpoints={{
              320: { slidesPerView: 1 },
              768: { slidesPerView: 2 },
              1024: { slidesPerView: 3 },
            }}
          >
            {blogs.map((b) => (
              <SwiperSlide key={b.id}>
                <BlogWidget blog={b} />
              </SwiperSlide>
            ))}
          </Swiper>
        </Container>
      </section>

      {/* 6. Team + Partners */}
      <section className="trust bg-white py-5 text-center">
        <Container>
          <Row className="mb-5">
            <Col>
              <h2>Meet the Team</h2>
              <p className="text-muted">The people behind Univa’s success.</p>
            </Col>
          </Row>
          <Row>
            {teamData.map((member, idx) => (
              <Col md={4} key={idx}>
                <Card className="shadow-sm">
                  <Team
                    teamImage={member.teamImage}
                    teamTitle={member.teamTitle}
                    teamText={member.teamText}
                  />
                </Card>
              </Col>
            ))}
          </Row>
          <Row className="mt-5">
            <Col>
              <Client partners={partners} />
            </Col>
          </Row>
        </Container>
      </section>

      {/* 7. Final CTA */}
      <section className="final-cta bg-primary text-center text-white py-5">
        <Container>
          <h2 className="mb-4">Ready to Get Started?</h2>
          <p className="lead mb-4">Join thousands of users already enjoying Univa.</p>
          <LinkContainer to="/auth/account">
            <Button variant="light" size="lg">
              Sign Up Now
            </Button>
          </LinkContainer>
        </Container>
      </section>
    </main>
  );
};

export default UnivaHomepage;
