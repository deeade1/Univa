import React from 'react';

export const Client = ({ clientImage, altText = 'Client logo' }) => {
  return (
    <div className="client-item">
      <img 
        src={clientImage} 
        alt={altText} 
        className="img-fluid client-img" 
        loading="lazy"
        width={120}
        height={60}
      />
    </div>
  );
};

export default Client;