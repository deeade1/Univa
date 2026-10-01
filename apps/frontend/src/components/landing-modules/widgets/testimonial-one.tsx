import React from 'react'
import { Card } from 'react-bootstrap'
import RatingStar from './rating-star'

// image
// import Image from '../../../assets//images/home-2/shape.png'



interface TestimonialProps {
  id: number;
  text: string;        // Previously testTitle
  author: string;      // Previously testText/testOwner
  role: string;        // Previously testSubtitle/userTitle
  rating: number;      // New rating prop
  image?: string;      // Previously testImage (made optional)
}
const TestimonialOne: React.FC<TestimonialProps> = ({ text, 
  author, 
  role, 
  rating,
  image  }) => {

  return (
    <>
        <div className=" position-relative">
    <div className="shape">
        {/* <img src={props.testImage} alt={props.id} className="img-fluid"/> */}
    </div>
     <Card.Body className='position-relative'>
        <h6 className="mb-3 mt-3">{text}</h6>
        <p>{author}</p>
        <div className="border-bottom"></div>
        <div className="d-flex align-items-center mt-3">
          {image && (
            <img src={image} alt={author} className="img-fluid rounded-pill"/>
          )}
          <div className="ms-3">
            <p className="mb-2">{role}</p>
            <RatingStar fillStar={rating} unfillStar={5 - rating} />
          </div>
        </div>
      </Card.Body>
        </div>
    </>
  )
}

export default TestimonialOne