// components/auth/WebAuthnAuth.tsx
import React from 'react';
import { Button } from 'react-bootstrap';

interface WebAuthnAuthProps {
  onAuthenticate: () => void;
  onRegister: () => void;
  onBackToPassword: () => void;
  mode: 'authenticate' | 'register';
}

export const WebAuthnAuth: React.FC<WebAuthnAuthProps> = ({
  onAuthenticate,
  onRegister,
  onBackToPassword,
  mode
}) => (
  <div className="webauthn-auth">
    <h3 className="text-center">Security Key</h3>
    <p className="text-center">
      {mode === 'authenticate' 
        ? 'Use your WebAuthn security key' 
        : 'Register a new security key'}
    </p>
    
    <div className="text-center mb-3">
      <Button 
        variant="primary"
        onClick={mode === 'authenticate' ? onAuthenticate : onRegister}
        className="me-2"
      >
        {mode === 'authenticate' ? 'Authenticate' : 'Register Key'}
      </Button>
    </div>
    
    <div className="text-center">
      <Button 
        variant="secondary"
        onClick={onBackToPassword}
      >
        Back to Password
      </Button>
    </div>
  </div>
);