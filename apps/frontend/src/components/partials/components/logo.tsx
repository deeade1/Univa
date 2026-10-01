import React from 'react';
import univa from '@/assets/images/univa.png';

interface LogoProps {
  color?: boolean;
  className?: string; // Optional className prop
  // Add any other props you might need here
}

const Logo: React.FC<LogoProps> = ({ color = false, className = '' }) => {
  return (
    
     <img src={univa} alt="Univa Logo" className="logo-img"  width="30"  />
  );
};

export default Logo;