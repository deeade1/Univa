import React from 'react';

const Counter = ({ 
  counterValue,  // Fixed prop name (from couterVlue)
  counterTitle,
  className = '' 
}) => {
  return (
    <div className={`counter-wrapper ${className}`}>
      <h2 className="mb-3 display-4 fw-bold text-primary">
        {counterValue}
      </h2>
      <h6 className="text-muted text-uppercase fs-6 letter-spacing-1">
        {counterTitle}
      </h6>
    </div>
  );
};

export default Counter;