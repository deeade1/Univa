
import type { PropsWithChildren } from 'react';
import { ApolloProvider } from '@apollo/client/react';

import { apolloClient } from '../apollo';
import { AuthProvider } from '../contexts/AuthContext';

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <ApolloProvider client={apolloClient}>
      <AuthProvider>{children}</AuthProvider>
    </ApolloProvider>
  );
}
