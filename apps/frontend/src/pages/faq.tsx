import { Col, Container, Row } from 'react-bootstrap'
import ContactDetail from '../components/landing-modules/widgets/contact-detail'
import SubHeader from '../components/landing-modules/widgets/sub-header'

const faqItems = [
  {
    id: 'collapseOne',
    headingId: 'headingOne',
    title: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit?',
    content: 'Amet minim mollit non deserunt ullamco est sit aliqua dolor do amet sint. Velit officia consequat duis enim velit mollit. Exercitation veniam consequat.',
    show: true
  },
  {
    id: 'collapseTwo',
    headingId: 'headingTwo',
    title: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit?',
    content: 'Amet minim mollit non deserunt ullamco est sit aliqua dolor do amet sint. Velit officia consequat duis enim velit mollit. Exercitation veniam consequat.'
  },
  {
    id: 'collapseThree',
    headingId: 'headingThree',
    title: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit?',
    content: 'Amet minim mollit non deserunt ullamco est sit aliqua dolor do amet sint. Velit officia consequat duis enim velit mollit. Exercitation veniam consequat.'
  },
  {
    id: 'collapseFour',
    headingId: 'headingFour',
    title: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit?',
    content: 'Amet minim mollit non deserunt ullamco est sit aliqua dolor do amet sint. Velit officia consequat duis enim velit mollit. Exercitation veniam consequat.'
  },
  {
    id: 'collapseFive',
    headingId: 'headingFive',
    title: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit?',
    content: 'Amet minim mollit non deserunt ullamco est sit aliqua dolor do amet sint. Velit officia consequat duis enim velit mollit. Exercitation veniam consequat.'
  }
]

const Faq = () => {
  return (
    <>
      <SubHeader title="Faq" />
      <div className="section-padding">
        <Container>
          <Row>
            <Col lg={6}>
              <p className="mb-2 text-uppercase text-primary">faq</p>
              <h2 className="text-secondary mb-4">
                Foremost Common <span className="text-primary">Questions</span>
              </h2>
              <p className="mb-0">
                Amet minim mollit non deserunt ullamco est sit aliqua dolor do amet sint. Velit officia consequat duis enim velit mollit. Exercitation veniam consequat.
              </p>
            </Col>
            <Col lg={6}>
              <div className="accordion custom-accordion" id="accordionExample">
                {faqItems.map((item, index) => (
                  <div className="accordion-item" key={item.id}>
                    <h2 className="accordion-header" id={item.headingId}>
                      <button
                        className={`accordion-button ${item.show ? '' : 'collapsed'}`}
                        type="button"
                        data-bs-toggle="collapse"
                        data-bs-target={`#${item.id}`}
                        aria-expanded={item.show ? 'true' : 'false'}
                        aria-controls={item.id}
                      >
                        {item.title}
                      </button>
                    </h2>
                    <div
                      id={item.id}
                      className={`accordion-collapse collapse ${item.show ? 'show' : ''}`}
                      aria-labelledby={item.headingId}
                      data-bs-parent="#accordionExample"
                    >
                      <div className="accordion-body">
                        <p className="mb-0">{item.content}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Col>
          </Row>
        </Container>
      </div>
      <div className="section-padding pt-0">
        <ContactDetail />
      </div>
    </>
  )
}

export default Faq