/**
 * Apollo HTTP transport.
 *
 * Responsible only for sending GraphQL operations to Django.
 * Authentication is handled separately by authLink.ts.
 */

import { HttpLink } from '@apollo/client';

import { apolloEnv } from '../env';

export const httpLink = new HttpLink({
  uri: apolloEnv.httpUri,
  fetchOptions: {
    headers: {
      Accept: 'application/graphql-response+json, application/json',
    },
  },
});
