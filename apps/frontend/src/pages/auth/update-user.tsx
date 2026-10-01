import React, { useContext } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation } from '@apollo/client';
import { Row, Col, Card, Form, Button } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { UPDATE_USER } from '@/queries/accountQuery/mutations';
import { AuthContext } from '../../context/authContext';

interface FormValues {
  firstName: string;
  lastName: string;
  files: FileList | null;
  streetAddress1: string;
  companyName: string;
  city: string;
  state: string;
  country: string;
}

const UpdateUser = () => {
  const context = useContext(AuthContext);
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<FormValues>({
    defaultValues: {
      firstName: '',
      lastName: '',
      files: null,
      streetAddress1: '',
      companyName: '',
      city: '',
      state: '',
      country: '',
    },
  });

  const [updateUser] = useMutation(UPDATE_USER, {
    update(proxy, { data: { updateUser: userData } }) {
      context.login(userData.user);
      navigate('/');
    },
    onError({ graphQLErrors }) {
      graphQLErrors.forEach(({ message }) => {
        setError('root', {
          type: 'manual',
          message,
        });
      });
    },
  });

  const onSubmit = (data: FormValues) => {
    if (!context.user) return;
    updateUser({
      variables: {
        input: {
          userId: context.user.id,
          ...data,
        },
      },
    });
  };

  return (
    <div>
      <Row>
        <Col sm="12" lg="6">
          <Card>
            <Card.Header className="d-flex justify-content-between">
              <div className="header-title">
                <h4 className="card-title">Update User</h4>
              </div>
            </Card.Header>
            <Card.Body>
              <Form noValidate onSubmit={handleSubmit(onSubmit)}>
                {errors.root && (
                  <div className="alert alert-danger">
                    {errors.root.message}
                  </div>
                )}
                <Row>
                  <Col lg="6">
                    <Form.Group className="form-group">
                      <Form.Label htmlFor="firstName">First Name</Form.Label>
                      <Form.Control
                        type="text"
                        id="firstName"
                        {...register('firstName', {
                          required: 'Please enter your first name',
                        })}
                        isInvalid={!!errors.firstName}
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.firstName?.message}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                  <Col lg="6">
                    <Form.Group className="form-group">
                      <Form.Label htmlFor="lastName">Last Name</Form.Label>
                      <Form.Control
                        type="text"
                        id="lastName"
                        {...register('lastName', {
                          required: 'Please enter your last name',
                        })}
                        isInvalid={!!errors.lastName}
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.lastName?.message}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                </Row>
                <Row>
                  <Col lg="6">
                    <Form.Group className="form-group">
                      <Form.Label htmlFor="files">Profile Picture</Form.Label>
                      <Form.Control
                        type="file"
                        id="files"
                        {...register('files')}
                        isInvalid={!!errors.files}
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.files?.message}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                  <Col lg="6">
                    <Form.Group className="form-group">
                      <Form.Label htmlFor="streetAddress1">Address</Form.Label>
                      <Form.Control
                        type="text"
                        id="streetAddress1"
                        {...register('streetAddress1', {
                          required: 'Please enter your address',
                        })}
                        isInvalid={!!errors.streetAddress1}
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.streetAddress1?.message}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                </Row>
                <Row>
                  <Col lg="6">
                    <Form.Group className="form-group">
                      <Form.Label htmlFor="companyName">Company Name</Form.Label>
                      <Form.Control
                        type="text"
                        id="companyName"
                        {...register('companyName')}
                        isInvalid={!!errors.companyName}
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.companyName?.message}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                  <Col lg="6">
                    <Form.Group className="form-group">
                      <Form.Label htmlFor="city">City</Form.Label>
                      <Form.Control
                        type="text"
                        id="city"
                        {...register('city', {
                          required: 'Please enter your city',
                        })}
                        isInvalid={!!errors.city}
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.city?.message}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                </Row>
                <Row>
                  <Col lg="6">
                    <Form.Group className="form-group">
                      <Form.Label htmlFor="state">State</Form.Label>
                      <Form.Control
                        type="text"
                        id="state"
                        {...register('state', {
                          required: 'Please enter your state',
                        })}
                        isInvalid={!!errors.state}
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.state?.message}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                  <Col lg="6">
                    <Form.Group className="form-group">
                      <Form.Label htmlFor="country">Country</Form.Label>
                      <Form.Control
                        type="text"
                        id="country"
                        {...register('country', {
                          required: 'Please enter your country',
                        })}
                        isInvalid={!!errors.country}
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.country?.message}
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                </Row>
                <div className="d-flex justify-content-center">
                  <Button type="submit" variant="primary">
                    Update
                  </Button>
                </div>
              </Form>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default UpdateUser;