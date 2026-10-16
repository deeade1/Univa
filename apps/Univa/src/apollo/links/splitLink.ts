/**
 * Route GraphQL subscriptions to WebSocket.
 * Route queries and mutations through the authenticated HTTP chain.
 */

import { ApolloLink } from '@apollo/client';
import { getMainDefinition } from '@apollo/client/utilities';

import { authLink } from './authLink';
import { errorLink } from './errorLink';
import { httpLink } from './httpLink';
import { loggerLink } from './loggerLink';
import { retryLink } from './retryLink';
import { wsLink } from './wsLink';

const httpChain = ApolloLink.from([
  loggerLink,
  errorLink,
  retryLink,
  authLink,
  httpLink,
]);

export const splitLink = wsLink
  ? ApolloLink.split(
      ({ query }) => {
        const definition = getMainDefinition(query);

        return (
          definition.kind === 'OperationDefinition' &&
          definition.operation === 'subscription'
        );
      },
      wsLink,
      httpChain,
    )
  : httpChain;
