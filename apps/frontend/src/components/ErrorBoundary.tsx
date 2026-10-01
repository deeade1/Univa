import React from 'react';
import { useRouteError, isRouteErrorResponse } from 'react-router-dom';

const ErrorBoundary: React.FC = () => {
  const error = useRouteError();
  
  if (isRouteErrorResponse(error)) {
    return (
      <div className="error-boundary">
        <h1>Oops! Something went wrong</h1>
        <h2>{error.status} {error.statusText}</h2>
        {error.data?.message && <p>{error.data.message}</p>}
      </div>
    );
  }

  return (
    <div className="error-boundary">
      <h1>Oops! Unexpected error</h1>
      <p>Something went wrong. Please try again later.</p>
    </div>
  );
};

export default ErrorBoundary;