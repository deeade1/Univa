import React, { FormEvent } from 'react';
import { Card, Col, Row, Container, Form, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';

// Components
import SubHeader from '@/components/landing-modules/widgets/sub-header';

// Assets
import contactImage from '@/assets/images/home-4/contact.webp';

// Types
interface ContactCardProps {
  iconPath: string;
  title: string;
  content: string;
}

interface FormField {
  id: string;
  label: string;
  placeholder: string;
  type: string;
  required: boolean;
}

// Constants
const CONTACT_CARDS: ContactCardProps[] = [
  {
    iconPath: "M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0zM192 272c44.183 0 80-35.817 80-80s-35.817-80-80-80-80 35.817-80 80 35.817 80 80 80z",
    title: "Address",
    content: "234 North Avenue Luke Lane, IN 360001"
  },
  {
    iconPath: "M502.3 190.8c3.9-3.1 9.7-.2 9.7 4.7V400c0 26.5-21.5 48-48 48H48c-26.5 0-48-21.5-48-48V195.6c0-5 5.7-7.8 9.7-4.7 22.4 17.4 52.1 39.5 154.1 113.6 21.1 15.4 56.7 47.8 92.2 47.6 35.7.3 72-32.8 92.3-47.6 102-74.1 131.6-96.3 154-113.7zM256 320c23.2.4 56.6-29.2 73.4-41.4 132.7-96.3 142.8-104.7 173.4-128.7 5.8-4.5 9.2-11.5 9.2-18.9v-19c0-26.5-21.5-48-48-48H48C21.5 64 0 85.5 0 112v19c0 7.4 3.4 14.3 9.2 18.9 30.6 23.9 40.7 32.4 173.4 128.7 16.8 12.2 50.2 41.8 73.4 41.4z",
    title: "Email Us",
    content: "Mail@hopeui.com"
  },
  {
    iconPath: "M497.39 361.8l-112-48a24 24 0 0 0-28 6.9l-49.6 60.6A370.66 370.66 0 0 1 130.6 204.11l60.6-49.6a23.94 23.94 0 0 0 6.9-28l-48-112A24.16 24.16 0 0 0 122.6.61l-104 24A24 24 0 0 0 0 48c0 256.5 207.9 464 464 464a24 24 0 0 0 23.4-18.6l24-104a24.29 24.29 0 0 0-14.01-27.6z",
    title: "Call Us",
    content: "0 123 456 789"
  }
];

const FORM_FIELDS: FormField[] = [
  { id: 'full-name', label: 'Full Name', placeholder: 'Your Name', type: 'text', required: true },
  { id: 'your-email', label: 'Your Email', placeholder: 'Your Email', type: 'email', required: true },
  { id: 'your-subject', label: 'Your Subject', placeholder: 'Your Subject', type: 'text', required: false }
];

// Contact Card Component
const ContactCard: React.FC<ContactCardProps> = ({ iconPath, title, content }) => (
  <Card className="rounded-1 mb-4 mb-lg-0 shadow-sm">
    <Card.Body className="text-center py-4">
      <div className="bg-soft-primary rounded-pill d-inline-flex p-3 mb-3">
        <svg 
          width="32" 
          height="32"
          viewBox="0 0 512 512"
          aria-hidden="true"
        >
          <path fill="currentColor" d={iconPath} />
        </svg>
      </div>
      <h5 className="mb-2">{title}</h5>
      <p className="mb-0 text-muted">{content}</p>
    </Card.Body>
  </Card>
);

// Main Component
const ContactUs: React.FC = () => {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // Form submission logic would go here
    console.log('Form submitted');
  };

  return (
    <>
      <SubHeader title="Contact Us" />
      
      {/* Contact Cards Section */}
      <section className="py-5">
        <Container>
          <Row className="g-4">
            {CONTACT_CARDS.map((card, index) => (
              <Col key={index} xs={12} md={6} lg={4}>
                <ContactCard {...card} />
              </Col>
            ))}
          </Row>
        </Container>
      </section>
      
      {/* Contact Form Section */}
      <section className="py-5 bg-light">
        <Container>
          <Row className="align-items-center">
            <Col lg={6} className="mb-5 mb-lg-0">
              <div className="pe-lg-4">
                <p className="text-uppercase text-primary fw-bold mb-2">Contact Us</p>
                <h2 className="mb-4">Have any query? <br />Get in Touch.</h2>
                <img 
                  src={contactImage} 
                  alt="Contact illustration" 
                  className="img-fluid rounded" 
                  loading="lazy"
                  width={600}
                  height={400}
                />
              </div>
            </Col>
            
            <Col lg={6}>
              <Form onSubmit={handleSubmit} className="bg-white p-4 rounded shadow-sm">
                {FORM_FIELDS.map((field) => (
                  <Form.Group key={field.id} className="mb-3">
                    <Form.Label htmlFor={field.id}>{field.label}</Form.Label>
                    <Form.Control
                      type={field.type}
                      id={field.id}
                      placeholder={field.placeholder}
                      required={field.required}
                    />
                  </Form.Group>
                ))}
                
                <Form.Group className="mb-3">
                  <Form.Label htmlFor="your-message">Your Message</Form.Label>
                  <Form.Control 
                    as="textarea" 
                    id="your-message"
                    rows={5} 
                    placeholder="Type your message here..." 
                    required
                  />
                </Form.Group>
                
                <Form.Group className="mb-4">
                  <Form.Check
                    type="checkbox"
                    id="terms-agreement"
                    label="By clicking you agree to our Terms & Conditions"
                    required
                  />
                </Form.Group>
                
                <Button type="submit" variant="primary" className="w-100">
                  Submit
                </Button>
              </Form>
            </Col>
          </Row>
        </Container>
      </section>
      
      {/* Map Section */}
      <div className="bg-white">
        <iframe 
          title="Our Location"
          src="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d123505.75790910245!2d121.05573800000002!3d14.681181!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3397ba0942ef7375%3A0x4a9a32d9fe083d40!2sQuezon%20City%2C%20Metro%20Manila%2C%20Philippines!5e0!3m2!1sen!2sus!4v1676356596840!5m2!1sen!2sus" 
          width="100%" 
          height="450" 
          style={{ border: 0 }} 
          allowFullScreen 
          loading="lazy" 
          referrerPolicy="no-referrer-when-downgrade"
        />
      </div>
    </>
  );
};

export default ContactUs;