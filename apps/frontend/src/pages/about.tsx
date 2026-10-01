import { Fragment } from 'react';
import { Col, Row, Container, Card } from 'react-bootstrap';
import Client from '@/components/landing-modules/widgets/client';
import SubHeader from '@/components/landing-modules/widgets/sub-header';
import TestimonialOne from '@/components/landing-modules/widgets/testimonial-one';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation } from 'swiper/modules';
import { Link } from 'react-router-dom';

// Import styles
import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/pagination';

// Import images
import image from '@/assets/images/home-4/service.webp';
import Image1 from '@/assets/images/home-4/banner-left.webp';
import Image2 from '@/assets/images/home-4/banner-right.webp';
import Image4 from '@/assets/images/home-4/Image-1.webp';
import image5 from '@/assets/images/home-1/07.webp';
import image6 from '@/assets/images/home-1/08.webp';
import image7 from '@/assets/images/home-1/09.webp';
import image8 from '@/assets/images/home-1/10.webp';
import image9 from '@/assets/images/home-1/11.webp';
import image10 from '@/assets/images/home-2/user-1.webp';
import image11 from '@/assets/images/home-2/user-2.webp';
import image12 from '@/assets/images/home-2/user-2.webp';

// SVG Component for repeated checkmark icon
type CheckIconProps = React.SVGProps<SVGSVGElement>;

const CheckIcon: React.FC<CheckIconProps> = (props) => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    {...props} // ⬅️ important!
  >
    <path opacity="0.4" d="..." fill="#3A57E8" />
    <path d="..." fill="#3A57E8" />
  </svg>
);

const services = [
  { title: 'Branding', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.' },
  { title: 'Design', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.' },
  { title: 'Development', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.' },
  { title: 'Marketing', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.' }
];

const features = [
  'Easy Communication',
  'Security Assured',
  'Expert Advise',
  'Pocket Friendly Prices'
];

const testimonials = [
  { 
    title: 'A true game changer', 
    text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...', 
    image: image10, 
    name: 'Eleen Rogers', 
    id: '01'
  },
  { 
    title: 'Best you can Get', 
    text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...', 
    image: image11, 
    name: 'Brooklyn Simmons', 
    id: '02'
  },
  { 
    title: 'Perfect product for your business', 
    text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...', 
    image: image12, 
    name: 'Jenny Wilson', 
    id: '03'
  }
];

const clients = [image5, image6, image7, image8, image9];

const About = () => {
  return (
    <Fragment>
      <SubHeader title="About Us" />
      
      {/* About Section */}
      <div className="section-padding bg-white">
        <Container>
          <Row className="align-items-center">
            <Col md={6}>
              <p className="mb-3 text-uppercase text-primary">About us</p>
              <h2 className="mb-4">
                Get <span className="text-primary">Unique<br />Solutions</span> With Us!
              </h2>
            </Col>
            <Col md={6}>
              <p className="mb-0">
                Lorem ipsum dolor sit amet, consectetur adipiscing elit...
              </p>
              <Link to="#" className="btn btn-primary mt-4">Know More</Link>
            </Col>
            
            <Col md={8} className="mt-4 mt-md-0">
              <img src={Image1} alt="" className="img-fluid" loading="lazy" />
            </Col>
            <Col md={4} className="mt-4 mt-md-0">
              <img src={Image2} alt="" className="img-fluid" loading="lazy" />
            </Col>
            
            {['Our Vision', 'Our Mission', 'Our Strategies'].map((title, index) => (
              <Col md={4} key={index}>
                <Card className="mb-lg-0">
                  <Card.Body>
                    <h4 className="mb-2">{title}</h4>
                    <p className="mb-0">
                      It is a long established fact that a reader will be distracted...
                    </p>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>
        </Container>
      </div>
      
      {/* Services Section */}
      <div className="section-padding bg-secondary">
        <Container>
          <Row className="align-items-center">
            <Col md={6}>
              <p className="mb-3 text-uppercase text-primary">our services</p>
              <h2 className="mb-4 text-white">
                Services <span className="text-primary">We Offer</span>
              </h2>
              <p className="mb-0">It is a long established fact...</p>
              <Link to="#" className="btn btn-primary mt-4">Know More</Link>
              <img src={image} alt="" className="img-fluid mt-4" loading="lazy" />
            </Col>
            <Col md={6}>
              <Row className="row-cols-1 row-cols-lg-2">
                {services.map((service, index) => (
                  <Col key={index}>
                    <Card className="services-box rounded-1">
                      <Card.Body>
                        <h5 className="mb-3">{service.title}</h5>
                        <p>{service.description}</p>
                        <Link to="#">Read More</Link>
                      </Card.Body>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Col>
          </Row>
        </Container>
      </div>
      
      {/* Features Section */}
      <div className="section-padding bg-white">
        <Container>
          <Row className="align-items-center">
            <Col md={6}>
              <p className="mb-3 text-uppercase text-primary">Why choose us?</p>
              <h2 className="mb-4">
                We Make <span className="text-primary">Your<br />Idea Come True</span>
              </h2>
              <p className="mb-4">Orci ipsum tempus amet libero turpis enim sed quis...</p>
              
              <Row className="row-cols-1 row-cols-lg-2">
                {features.map((feature, index) => (
                  <Col className="mb-4" key={index}>
                    <div className="d-flex align-items-center">
                      <CheckIcon className="me-2" />
                      {feature}
                    </div>
                  </Col>
                ))}
              </Row>
              
              <Link to="#" className="btn btn-primary">Know More</Link>
            </Col>
            <Col md={6} className="mt-4">
              <img src={Image4} alt="" className="img-fluid" loading="lazy" />
            </Col>
          </Row>
        </Container>
      </div>
      
      {/* Clients Section */}
      <div className="inner-box bg-secondary">
        <Container>
          <Row className="row-cols-1 row-cols-sm-2 row-cols-md-5 align-items-center">
            {clients.map((client, index) => (
              <Col className="mb-lg-0 mb-5 d-flex justify-content-center" key={index}>
                <Client clientImage={client} />
              </Col>
            ))}
          </Row>
        </Container>
      </div>
      
      {/* Testimonials Section */}
      <div className="section-card-padding">
        <Container>
          <Row className="align-items-center">
            <Col lg={12} className="text-center">
              <p className="mb-3 text-primary">Reviews</p>
              <h2 className="mb-5 text-secondary">
                What our <span className="text-primary">Customer's are saying</span>
              </h2>
            </Col>
            
            <div className="overflow-hidden slider-circle-btn" id="testimonial-one-slider">
              <Swiper
                className="p-0 m-0 swiper-wrapper list-inline"
                slidesPerView={3}
                spaceBetween={32}
                modules={[Navigation]}
                navigation={{
                  nextEl: '.swiper-button-next',
                  prevEl: '.swiper-button-prev'
                }}
                breakpoints={{
                  320: { slidesPerView: 1 },
                  550: { slidesPerView: 2 },
                  991: { slidesPerView: 3 },
                  1400: { slidesPerView: 3 },
                  1500: { slidesPerView: 3 },
                  1920: { slidesPerView: 3 },
                  2040: { slidesPerView: 3 },
                  2440: { slidesPerView: 3 }
                }}
              >
                {[...testimonials, ...testimonials].map((testimonial, index) => (
                  <SwiperSlide className="card-slide overflow-hidden" key={`${testimonial.id}-${index}`}>
                    <Card>
                      <TestimonialOne 
                        testTitle={testimonial.title}
                        testText={testimonial.text}
                        testImage={testimonial.image}
                        userTitle={testimonial.name}
                        Id={testimonial.id}
                      />
                    </Card>
                  </SwiperSlide>
                ))}
              </Swiper>
              <div className="swiper-button swiper-button-next"></div>
              <div className="swiper-button swiper-button-prev"></div>
            </div>
          </Row>
        </Container>
      </div>
    </Fragment>
  );
};

export default About;