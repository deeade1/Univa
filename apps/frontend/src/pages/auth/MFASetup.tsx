// components/auth/MFASetup.tsx
import React, { useState } from 'react';
import { Button, Form } from 'react-bootstrap';
import { useAuth } from '@/context/authContext';

type MFAMethod = 'sms' | 'email' | 'authenticator';

export const MFASetup: React.FC = () => {
  const { user, logAuthEvent } = useAuth();
  const [method, setMethod] = useState<MFAMethod>('email');
  const [step, setStep] = useState<'select' | 'verify' | 'complete'>('select');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');

  const handleSetup = async () => {
    try {
      // Replace with your actual API call
      const response = await fetch('/api/auth/mfa/setup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ method, userId: user?.id })
      });

      if (response.ok) {
        setStep('verify');
        logAuthEvent({
          type: 'mfa_setup_initiated',
          metadata: { method }
        });
      } else {
        setError('Failed to initiate MFA setup');
      }
    } catch (err) {
      setError('Network error during MFA setup');
    }
  };

  const handleVerify = async () => {
    try {
      // Replace with your actual API call
      const response = await fetch('/api/auth/mfa/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ code, method, userId: user?.id })
      });

      if (response.ok) {
        setStep('complete');
        logAuthEvent({
          type: 'mfa_verified',
          metadata: { method }
        });
      } else {
        setError('Invalid verification code');
      }
    } catch (err) {
      setError('Network error during verification');
    }
  };

  return (
    <div className="mfa-setup">
      {step === 'select' && (
        <>
          <h3>Set Up Multi-Factor Authentication</h3>
          <Form.Group className="mb-3">
            {(['email', 'sms', 'authenticator'] as MFAMethod[]).map((m) => (
              <Form.Check
                key={m}
                type="radio"
                id={`mfa-${m}`}
                label={
                  m === 'sms' ? 'SMS Verification' :
                  m === 'email' ? 'Email Verification' :
                  'Authenticator App'
                }
                checked={method === m}
                onChange={() => setMethod(m)}
              />
            ))}
          </Form.Group>
          <Button onClick={handleSetup}>Continue</Button>
        </>
      )}

      {step === 'verify' && (
        <>
          <h3>Verify Your {method === 'sms' ? 'Phone' : method === 'email' ? 'Email' : 'Authenticator'}</h3>
          <p>Enter the verification code sent to your {method}</p>
          <Form.Control
            type="text" 
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Verification code"
            className="mb-3"
          />
          <Button onClick={handleVerify}>Verify</Button>
          {error && <div className="alert alert-danger mt-3">{error}</div>}
        </>
      )}

      {step === 'complete' && (
        <>
          <h3 className="text-success">MFA Setup Complete!</h3>
          <p>Your {method} verification is now active.</p>
        </>
      )}
    </div>
  );
};