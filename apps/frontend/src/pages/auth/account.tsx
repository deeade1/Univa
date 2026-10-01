import React, { useContext, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation } from '@apollo/client/react';
import { Row, Col, Card, Form, Button, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
//import { AuthContext } from '@/context/authContext';
// @ts-expect-error authContext.jsx does not have a TypeScript declaration file.
import { useAuth } from '@/context/authContext';
// @ts-expect-error validation.js does not have a TypeScript declaration file.
import { validateContact } from '@/context/validation';
import { SIGNIN, SIGNUP } from '@/queries/accountQuery/mutations';
import * as yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';

interface AuthValues {
  contact: string;
  password: string;
  rememberMe?: boolean;
}

const Account = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const authSchema = yup.object({
    contact: yup.string()
      .required('Email or phone is required')
      .test('valid-contact', 'Invalid email or phone', (value) => 
        validateContact(value || '').isValid
      ),
    password: yup.string()
      .required('Password is required')
      .min(8, 'Password must be at least 8 characters')
  });

  const signInSchema = authSchema.concat(yup.object({
    rememberMe: yup.boolean().default(false)
  }));

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset
  } = useForm<AuthValues>({
    resolver: yupResolver(activeTab === 'signin' ? signInSchema : authSchema)
  });

  const [signUp] = useMutation(SIGNUP);
  const [signIn] = useMutation(SIGNIN);

  const handleAuth = async (data: AuthValues) => {
  setIsLoading(true);
  setError('');

  try {
    const mutation = activeTab === 'signin' ? signIn : signUp;
    const variables = activeTab === 'signin' ? {
      contact: data.contact,
      password: data.password,
      rememberMe: data.rememberMe
    } : {
      input: {
        contact: data.contact,
        password: data.password
      }
    };

    const result = await mutation({ variables });

    const authData = (result.data as Record<string, any> | undefined)?.[
      activeTab === 'signin' ? 'signIn' : 'signUp'
    ];
    if (authData?.token) {
      login({
        token: authData.token,
        refreshToken: authData.refreshToken,
        user: authData.user
      });

      if (activeTab === 'signup' && authData.verificationSent) {
        navigate('/verify-email', { state: { contact: data.contact } });
      } else {
        navigate('/');
      }
    }
  } catch (err) {
    let errorMessage = 'Authentication failed';
    
    if (err instanceof Error) {
      errorMessage = err.message;
    } else if (typeof err === 'string') {
      errorMessage = err;
    }

    setError(activeTab === 'signin' 
      ? 'Invalid credentials' 
      : errorMessage);
  } finally {
    setIsLoading(false);
  }
};

  const switchTab = (tab: 'signin' | 'signup') => {
    setActiveTab(tab);
    setError('');
    reset();
  };

  return (
    <Row className="justify-content-center mt-5">
      <Col md={8} lg={6}>
        <Card>
          <Card.Header className="d-flex">
            <Button 
              variant={activeTab === 'signin' ? 'primary' : 'outline-primary'} 
              className="flex-grow-1"
              onClick={() => switchTab('signin')}
            >
              Sign In
            </Button>
            <Button 
              variant={activeTab === 'signup' ? 'primary' : 'outline-primary'} 
              className="flex-grow-1"
              onClick={() => switchTab('signup')}
            >
              Sign Up
            </Button>
          </Card.Header>
          
          <Card.Body>
            {error && (
              <div className="alert alert-danger">
                {error}
              </div>
            )}

            <Form onSubmit={handleSubmit(handleAuth)}>
              <Form.Group className="mb-3">
                <Form.Label>Email or Phone</Form.Label>
                <Form.Control
                  {...register('contact')}
                  type="text"
                  placeholder="Enter email or phone"
                  isInvalid={!!errors.contact}
                />
                <Form.Control.Feedback type="invalid">
                  {errors.contact?.message}
                </Form.Control.Feedback>
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label>Password</Form.Label>
                <Form.Control
                  {...register('password')}
                  type="password"
                  placeholder={`Password ${activeTab === 'signup' ? '(min 8 characters)' : ''}`}
                  isInvalid={!!errors.password}
                />
                <Form.Control.Feedback type="invalid">
                  {errors.password?.message}
                </Form.Control.Feedback>
              </Form.Group>

              {activeTab === 'signin' && (
                <Form.Group className="mb-3">
                  <Form.Check
                    {...register('rememberMe')}
                    type="checkbox"
                    label="Remember me"
                  />
                </Form.Group>
              )}

              <Button 
                type="submit" 
                className="w-100"
                disabled={isLoading}
              >
                {isLoading ? (
                  <Spinner animation="border" size="sm" />
                ) : (
                  activeTab === 'signin' ? 'Sign In' : 'Sign Up'
                )}
              </Button>
            </Form>

            <div className="text-center mt-3">
              <Button 
                variant="link" 
                onClick={() => navigate('/forgot-password')}
              >
                Forgot password?
              </Button>
            </div>
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
};

export default Account;