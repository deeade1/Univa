import React, { Fragment, useState } from 'react';
import FsLightbox from 'fslightbox-react';
import { Row, Col, Image, Form, Nav, Dropdown, Tab } from 'react-bootstrap';
import Card from '@/components/Card';
import { Link } from 'react-router-dom';

// Image imports
import avatars1 from '@/assets/images/avatars/01.png';
import avatars22 from '@/assets/images/avatars/avtar_1.png';
import avatars33 from '@/assets/images/avatars/avtar_2.png';
import avatars44 from '@/assets/images/avatars/avtar_3.png';
import avatars55 from '@/assets/images/avatars/avtar_4.png';
import avatars66 from '@/assets/images/avatars/avtar_5.png';
import avatars2 from '@/assets/images/avatars/02.png';
import avatars3 from '@/assets/images/avatars/03.png';
import avatars4 from '@/assets/images/avatars/04.png';
import avatars5 from '@/assets/images/avatars/05.png';

import icon1 from '@/assets/images/icons/01.png';
import icon2 from '@/assets/images/icons/02.png';
import icon3 from '@/assets/images/icons/03.png';
import icon4 from '@/assets/images/icons/04.png';
import icon8 from '@/assets/images/icons/08.png';
import icon6 from '@/assets/images/icons/06.png';
import icon7 from '@/assets/images/icons/07.png';
import icon5 from '@/assets/images/icons/05.png';

import shap2 from '@/assets/images/shapes/02.png';
import shap4 from '@/assets/images/shapes/04.png';
import shap6 from '@/assets/images/shapes/06.png';
import pages2 from '@/assets/images/pages/02-page.png';

// Type declaration for FsLightbox props
interface FsLightboxProps {
  toggler: boolean;
  sources: string[];
  type?: 'image' | 'video' | 'youtube' | 'vimeo';
  sourceIndex?: number;
  onOpen?: () => void;
  onClose?: () => void;
}



const UserProfile = () => {
  const [toggler, setToggler] = useState<boolean>(false);

  return (
    <Fragment>
      <FsLightbox
        toggler={toggler}
        sources={[icon4, shap2, icon8, shap4, icon2, shap6, icon5, shap4, icon1]}
      />
      
      <Tab.Container defaultActiveKey="first">
        <Row>
          <Col lg="12">
            <Card>
              <Card.Body>
                <div className="d-flex flex-wrap align-items-center justify-content-between">
                  <div className="d-flex flex-wrap align-items-center">
                    <div className="profile-img position-relative me-3 mb-3 mb-lg-0 profile-logo profile-logo1">
                      <Image className="theme-color-default-img img-fluid rounded-pill avatar-100" src={avatars1} alt="profile-pic"/>
                      <Image className="theme-color-purple-img img-fluid rounded-pill avatar-100" src={avatars22} alt="profile-pic"/>
                      <Image className="theme-color-blue-img img-fluid rounded-pill avatar-100" src={avatars33} alt="profile-pic"/>
                      <Image className="theme-color-green-img img-fluid rounded-pill avatar-100" src={avatars55} alt="profile-pic"/>
                      <Image className="theme-color-yellow-img img-fluid rounded-pill avatar-100" src={avatars66} alt="profile-pic"/>
                      <Image className="theme-color-pink-img img-fluid rounded-pill avatar-100" src={avatars44} alt="profile-pic"/>
                    </div>
                    <div className="d-flex flex-wrap align-items-center mb-3 mb-sm-0">
                      <h4 className="me-2 h4">Austin Robertson</h4>
                      <span> - Web Developer</span>
                    </div>
                  </div>
                  <Nav as="ul" className="d-flex nav-pills mb-0 text-center profile-tab" id="profile-pills-tab" role="tablist">
                    <Nav.Item as="li">
                      <Nav.Link eventKey="first">Feed</Nav.Link>
                    </Nav.Item>
                    <Nav.Item as="li">
                      <Nav.Link eventKey="second">Activity</Nav.Link>
                    </Nav.Item>
                    <Nav.Item as="li">
                      <Nav.Link eventKey="third">Friends</Nav.Link>
                    </Nav.Item>
                    <Nav.Item as="li">
                      <Nav.Link eventKey="fourth">Profile</Nav.Link>
                    </Nav.Item>
                  </Nav>
                </div>
              </Card.Body>
            </Card>
          </Col>

          <Col lg="3">
            {/* Left Column Content */}
            <Card>
              <Card.Header>
                <div className="header-title">
                  <h4 className="card-title">News</h4>
                </div>
              </Card.Header>
              <Card.Body>
                <ul className="list-inline p-0 m-0">
                  <li className="d-flex mb-2">
                    <div className="news-icon me-3">
                      <svg width="20" viewBox="0 0 24 24">
                        <path fill="currentColor" d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4C22,2.89 21.1,2 20,2Z" />
                      </svg>
                    </div>
                    <p className="news-detail mb-0">there is a meetup in your city on fryday at 19:00. <Link to="#">see details</Link></p>
                  </li>
                  <li className="d-flex">
                    <div className="news-icon me-3">
                      <svg width="20" viewBox="0 0 24 24">
                        <path fill="currentColor" d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4C22,2.89 21.1,2 20,2Z" />
                      </svg>
                    </div>
                    <p className="news-detail mb-0">20% off coupon on selected items at pharmaprix </p>
                  </li>
                </ul>
              </Card.Body>
            </Card>

            <Card>
              <Card.Header className="d-flex align-items-center justify-content-between">
                <div className="header-title">
                  <h4 className="card-title">Gallery</h4>
                </div>
                <span>132 pics</span>
              </Card.Header>
              <Card.Body>
                <div className="d-grid gap-card grid-cols-3">
                  {[icon4, shap2, icon8, shap4, icon2, shap6, icon5, shap4, icon1].map((img, index) => (
                    <Link key={index} onClick={() => setToggler(!toggler)} to="#">
                      <Image src={img} className="img-fluid bg-soft-info rounded" alt="profile-image"/>
                    </Link>
                  ))}
                </div>
              </Card.Body>
            </Card>

            {/* More left column cards... */}
          </Col>

          <Col lg="6">
            {/* Middle Column Content */}
            <Tab.Content className="profile-content">
              <Tab.Pane eventKey="first" id="profile-feed">
                {/* Feed content... */}
              </Tab.Pane>
              <Tab.Pane eventKey="second" id="profile-activity">
                {/* Activity content... */}
              </Tab.Pane>
              <Tab.Pane eventKey="third" id="profile-friends">
                {/* Friends content... */}
              </Tab.Pane>
              <Tab.Pane eventKey="fourth" id="profile-profile">
                {/* Profile content... */}
              </Tab.Pane>
            </Tab.Content>
          </Col>

          <Col lg="3">
            {/* Right Column Content */}
            <Card>
              <Card.Header>
                <div className="header-title">
                  <h4 className="card-title">About</h4>
                </div>
              </Card.Header>
              <Card.Body>
                <p>Lorem ipsum dolor sit amet, contur adipiscing elit.</p>
                <div className="mb-1">Email: <Link to="#" className="ms-3">nikjone@demoo.com</Link></div>
                <div className="mb-1">Phone: <Link to="#" className="ms-3">001 2351 256 12</Link></div>
                <div>Location: <span className="ms-3">USA</span></div>
              </Card.Body>
            </Card>

            {/* More right column cards... */}
          </Col>
        </Row>
      </Tab.Container>
    </Fragment>
  );
};

export default UserProfile;