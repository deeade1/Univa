import React from 'react';
import { Row, Col } from 'react-bootstrap';
import PropTypes from 'prop-types';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Autoplay } from 'swiper/modules';
import 'swiper/css';

/**
 * Client/partner logo carousel component
 */
const Client = ({ partners, title, description }) => {
  return (
    <div className="client-section py-5">
      <Row className="mb-4">
        <Col className="text-center">
          {title && <h2 className="mb-3">{title}</h2>}
          {description && <p className="text-muted">{description}</p>}
        </Col>
      </Row>
      
      <Row>
        <Col>
          <Swiper
            modules={[Autoplay]}
            spaceBetween={30}
            slidesPerView={2}
            autoplay={{ 
              delay: 2500,
              disableOnInteraction: false
            }}
            loop={true}
            breakpoints={{
              576: {
                slidesPerView: 3
              },
              768: {
                slidesPerView: 4
              },
              992: {
                slidesPerView: 5
              },
              1200: {
                slidesPerView: 6
              }
            }}
          >
            {partners.map((partner, index) => (
              <SwiperSlide key={index}>
                <div className="client-logo-wrapper d-flex align-items-center justify-content-center p-3">
                  <img 
                    src={partner.logo} 
                    alt={partner.name} 
                    className="img-fluid client-logo" 
                    style={{ maxHeight: '80px', maxWidth: '160px' }}
                  />
                </div>
              </SwiperSlide>
            ))}
          </Swiper>
        </Col>
      </Row>
    </div>
  );
};

Client.propTypes = {
  partners: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      logo: PropTypes.string.isRequired
    })
  ).isRequired,
  title: PropTypes.string,
  description: PropTypes.string
};

// Default props with sample data
Client.defaultProps = {
  partners: [
    { name: 'Visa', logo: '/path/to/visa-logo.webp' },
    { name: 'Mastercard', logo: '/path/to/mastercard-logo.webp' },
    { name: 'DHL', logo: '/path/to/dhl-logo.webp' },
    { name: 'FedEx', logo: '/path/to/fedex-logo.webp' },
    { name: 'PayPal', logo: '/path/to/paypal-logo.webp' },
    { name: 'Uber', logo: '/path/to/uber-logo.webp' }
  ],
  title: 'Trusted By Industry Leaders',
  description: 'We partner with the best to bring you seamless experiences'
};

export default Client;