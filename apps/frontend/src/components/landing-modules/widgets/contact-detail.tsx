import React from 'react';
import { Col, Container, Row } from 'react-bootstrap';

interface ContactDetailProps {
  // You can add any props here if needed
}

const ContactDetail: React.FC<ContactDetailProps> = () => {
  // For better TypeScript support with images, consider adding a declaration file
  const contactImage: string = require('@/assets/images/home2/banner-contact.webp').default;

  return (
    <Container className="contact-section">
      <Row className="align-items-center">
        <Col xs={12} className="mb-5">
          <img 
            src={contactImage} 
            alt="Contact us illustration" 
            className="img-fluid rounded-3 shadow-sm"
            loading="lazy"
            width={1200}
            height={600}
          />
        </Col>
        
        <Col lg={7} className="text-lg-start text-center mb-4 mb-lg-0">
          <p className="text-primary text-uppercase fw-semibold mb-3">
            Contact
          </p>
          <h2 className="display-5 fw-bold">
            Let's Stay <br/>
            <span className="text-primary">In Touch</span>
          </h2>
        </Col>
        
        <Col lg={5} className="contact-info">
          <h5 className="fw-semibold mb-3">
            Themes, E-commerce website, Dashboard and Apps.
          </h5>
          <div className="d-flex flex-column gap-2">
            <p className="mb-0">
              <a 
                href="mailto:contact@hopeui.com" 
                className="text-decoration-none"
                aria-label="Email us at contact@hopeui.com"
              >
                contact@hopeui.com
              </a>
            </p>
            <p className="mb-0">
              <a 
                href="tel:2395550108" 
                className="text-decoration-none"
                aria-label="Call us at (239) 555-0108"
              >
                (239) 555-0108
              </a>
            </p>
          </div>
        </Col>
      </Row>
    </Container>
  );
};

export default ContactDetail;