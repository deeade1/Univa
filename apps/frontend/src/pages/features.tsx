import { Card, Col, Container, Row } from 'react-bootstrap'
import { Swiper, SwiperSlide } from 'swiper/react'
import { Navigation } from 'swiper/modules'
import 'swiper/css'
import 'swiper/css/navigation'

import BlogWidget from '@/components/landing-modules/widgets/blog-widget';
import SubHeader from '@/components/landing-modules/widgets/sub-header'
import TestimonialOne from '@/components/landing-modules/widgets/testimonial-one'
import FeatureSection from '@/components/landing-modules/widgets/header-section'

// Images
import Image1 from '@/assets/images/home-3/02.webp'
import Image2 from '@/assets/images/home-3/03.webp'
import Image3 from '@/assets/images/home-3/04.webp'
import User1 from '@/assets/images/home-2/user-1.webp'
import User2 from '@/assets/images/home-2/user-2.webp'
import User3 from '@/assets/images/home-2/user-3.webp'
// Image imports
import image1 from '@/assets/images/blog/01.webp';
import image2 from '@/assets/images/blog/02.webp';
import image3 from '@/assets/images/blog/03.webp';
import image4 from '@/assets/images/blog/04.webp';
import image5 from '@/assets/images/blog/05.webp';
import image6 from '@/assets/images/blog/06.webp';
import image7 from '@/assets/images/blog/07.webp';
import image8 from '@/assets/images/blog/08.webp';
import image9 from '@/assets/images/blog/09.webp';

interface Testimonial {
  id: string;
  title: string;
  text: string;
  image: string;
  user: string;
}

interface BlogPost {
  id: number;
  image: string;
  date: string;
  title: string;
  author: string;
  description: string;
}

const testimonials: Testimonial[] = [
  {
    id: '01',
    title: 'A true game changer.',
    text: '“Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vitae, eget condimentum luctus nec nec tellus sem sed. Diam elementum tellus posuere ipsum tortor.”',
    image: User1,
    user: 'Eleen Rogers'
  },
  // ... other testimonials
];

const blogPosts: BlogPost[] = [
  {
    id: 1,
    image: image1,
    date: "December 26, 2022",
    title: "The Cheapest Destinations Of All Time, A List Of Beauty And Budget.",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  },
  {
    id: 2,
    image: image2,
    date: "December 20, 2022",
    title: "A Year From Now You May Wish You Had Started Today.",
    author: "Video",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  },
  {
    id: 3,
    image: image3,
    date: "December 20, 2022",
    title: "Travelers Like To Know Which Public Transportation Options Are Best.",
    author: "Video",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  },
  {
    id: 4,
    image: image4,
    date: "December 20, 2022",
    title: "Travelers Like To Know Which Public Transportation Options Are Best.",
    author: "Video",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  },
  {
    id: 5,
    image: image5,
    date: "December 20, 2022",
    title: "WIT AND DELIGHT: The Advice From A Twenty Something",
    author: "Video",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  },
  {
    id: 6,
    image: image6,
    date: "December 20, 2022",
    title: "Paranomal And Ghost Experience: The Man Behind The Musical",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  },
  {
    id: 7,
    image: image7,
    date: "December 20, 2022",
    title: "I Do Indeed Write On The Road. My Laptop Goes With Me Everywhere.",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  },
  {
    id: 8,
    image: image8,
    date: "December 20, 2022",
    title: "The Cheapest Destinations Of All Time, A List Of Beauty And Budget.",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  },
  {
    id: 9,
    image: image9,
    date: "December 20, 2022",
    title: "The Ultimate Travel Guide: What To Do, See & Eat.",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry..."
  }
];


const breakpoints = {
  320: { slidesPerView: 1 },
  550: { slidesPerView: 2 },
  991: { slidesPerView: 3 },
  1400: { slidesPerView: 3 },
  1500: { slidesPerView: 3 },
  1920: { slidesPerView: 3 },
  2040: { slidesPerView: 3 },
  2440: { slidesPerView: 3 }
}

const Features = () => {
  return (
    <>
      {/* ... other sections ... */}

      <div className="section-padding pt-0">
        <Container>
          <Row className="align-items-center">
            <Col md={12} className="text-center">
              <p className="mb-2 text-uppercase text-primary">Blog</p>
              <h2 className="text-secondary mb-4">
                All the <span className="text-primary">Support you Need</span>
              </h2>
            </Col>
            
            <div className="overflow-hidden slider-circle-btn mt-5" id="app-slider">
              <Swiper
                className="p-0 m-0 mb-2 swiper-wrapper list-inline"
                slidesPerView={3}
                spaceBetween={32}
                modules={[Navigation]}
                navigation={{
                  nextEl: '#app-slider-next',
                  prevEl: '#app-slider-prev'
                }}
                breakpoints={breakpoints}
              >
                {[...blogPosts, ...blogPosts].map((post, index) => (
                  <SwiperSlide className="card-slide overflow-hidden" key={`${post.title}-${index}`}>
                    <Card>
                 <BlogWidget
                    blogImage={post.image}
                    blogTitle={post.title}
                    blogDate="..."
                    blogAuthor="..."
                    blogDescription="..."
                  />
                    </Card>
                  </SwiperSlide>
                ))}
              </Swiper>
              <div className="swiper-button swiper-button-next" id="app-slider-next"></div>
              <div className="swiper-button swiper-button-prev" id="app-slider-prev"></div>
            </div>
          </Row>
        </Container>
      </div>
    </>
  )
}

export default Features