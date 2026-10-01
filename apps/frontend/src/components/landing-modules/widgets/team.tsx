import { Card } from 'react-bootstrap'

const Team = ({ teamImage, teamTitle, teamText }) => {
  return (
    <>
      <img 
        src={teamImage} 
        alt="team-details" 
        className="img-fluid rounded-top" 
        loading="lazy"
      />
      <Card.Body>
        <h6 className="my-2">{teamTitle}</h6>
        <p className="mb-0">{teamText}</p>
      </Card.Body>
    </>
  )
}

export default Team