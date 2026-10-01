import React from "react";
import { Col, Container, Row } from "react-bootstrap";
import BlogWidget, { BlogPost } from "@/components/landing-modules/widgets/blog-widget";
import SubHeader from "@/components/landing-modules/widgets/sub-header";

// Images
import image1 from "@/assets/images/blog/01.webp";
import image2 from "@/assets/images/blog/02.webp";
import image3 from "@/assets/images/blog/03.webp";
import image4 from "@/assets/images/blog/04.webp";
import image5 from "@/assets/images/blog/05.webp";
import image6 from "@/assets/images/blog/06.webp";
import image7 from "@/assets/images/blog/07.webp";
import image8 from "@/assets/images/blog/08.webp";
import image9 from "@/assets/images/blog/09.webp";

const blogPosts: BlogPost[] = [
  {
    id: 1,
    image: image1,
    date: "December 26, 2022",
    title: "The Cheapest Destinations Of All Time, A List Of Beauty And Budget.",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
  {
    id: 2,
    image: image2,
    date: "December 20, 2022",
    title: "A Year From Now You May Wish You Had Started Today.",
    author: "Video",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
  {
    id: 3,
    image: image3,
    date: "December 20, 2022",
    title: "Travelers Like To Know Which Public Transportation Options Are Best.",
    author: "Video",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
  {
    id: 4,
    image: image4,
    date: "December 20, 2022",
    title: "Travelers Like To Know Which Public Transportation Options Are Best.",
    author: "Video",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
  {
    id: 5,
    image: image5,
    date: "December 20, 2022",
    title: "WIT AND DELIGHT: The Advice From A Twenty Something",
    author: "Video",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
  {
    id: 6,
    image: image6,
    date: "December 20, 2022",
    title: "Paranomal And Ghost Experience: The Man Behind The Musical",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
  {
    id: 7,
    image: image7,
    date: "December 20, 2022",
    title: "I Do Indeed Write On The Road. My Laptop Goes With Me Everywhere.",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
  {
    id: 8,
    image: image8,
    date: "December 20, 2022",
    title: "The Cheapest Destinations Of All Time, A List Of Beauty And Budget.",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
  {
    id: 9,
    image: image9,
    date: "December 20, 2022",
    title: "The Ultimate Travel Guide: What To Do, See & Eat.",
    author: "Travel",
    description: "Lorem Ipsum Is Simply Dummy Text Of The Printing And Typesetting Industry...",
  },
];

const Blog = () => {
  return (
    <>
      <SubHeader title="Blog" />
      <div className="inner-card-box">
        <Container>
          <Row>
            {blogPosts.map((post) => (
              <Col lg={4} md={6} key={post.id} className="mb-4">
                <BlogWidget blog={post} />
              </Col>
            ))}
          </Row>
        </Container>
      </div>
    </>
  );
};

export default Blog;
