import React from 'react'
import { Link } from 'react-router-dom'

const FeatureWidget = (props) => {
  return (
    <Fragment>
        <h6 className="mb-3 text-center">{props.featurTitle}</h6>
        <p className="text-center">{props.featurText}</p>
        <Link className="d-flex justify-content-center" to="#">Know More</Link>
    </Fragment>
  )
}
FeatureWidget.displayName = "FeatureWidget"
export default FeatureWidget
