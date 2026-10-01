import React from 'react';

const Counter1 = ({ 
  couterValue,  // Fixed typo in prop name (was couterVlue)
  counterTitle 
}) => {
  return (
    <div className="counter-item text-center">
      <h2 className="mb-2 display-4 fw-bold text-white">
        {couterValue}
      </h2>
      <h6 className="text-white text-uppercase fs-6 letter-spacing-1">
        {counterTitle}
      </h6>
    </div>
  );
};

export default Counter1;