// components/auth/MagicLinkAuth.tsx
import React from 'react';
import { Button, Form } from 'react-bootstrap';

interface MagicLinkAuthProps {
  email: string;
  isSent: boolean;
  onSubmit: (contact: string) => void;
  onBackToPassword: () => void;
  errors?: { contact?: { message?: string } };
}

export const MagicLinkAuth: React.FC<MagicLinkAuthProps> = ({
  email,
  isSent,
  onSubmit,
  onBackToPassword,
  errors
}) => {
  const [contact, setContact] = React.useState(email);

  return (
    <div className="magic-link-auth">
      <h3 className="text-center">Magic Link</h3>
      {isSent ? (
        <>
          <p className="text-center">We sent a link to {email}</p>
          <div className="text-center">
            <Button 
              variant="secondary"
              className="me-2"
              onClick={onBackToPassword}
            >
              Back to Password
            </Button>
            <Button 
              variant="primary"
              onClick={() => onSubmit(email)}
            >
              Resend Link
            </Button>
          </div>
        </>
      ) : (
        <>
          <p className="text-center">Get a secure login link sent to your email or phone</p>
          <Form.Group className="mb-3">
            <Form.Label>Email or Phone</Form.Label>
            <Form.Control
              type="text"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              isInvalid={!!errors?.contact}
              placeholder="Enter email or phone" 
            />
            {errors?.contact && (
              <Form.Control.Feedback type="invalid">
                {errors.contact.message}
              </Form.Control.Feedback>
            )}
          </Form.Group>
          <div className="text-center">
            <Button 
              variant="secondary"
              className="me-2"
              onClick={onBackToPassword}
            >
              Back to Password
            </Button>
            <Button 
              variant="primary"
              onClick={() => onSubmit(contact)}
            >
              Send Magic Link
            </Button>
          </div>
        </>
      )}
    </div>
  );
};