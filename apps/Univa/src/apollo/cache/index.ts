/**
 * Central Apollo cache instance for Univa.
 */

import { InMemoryCache } from '@apollo/client';

import { typePolicies } from './typePolicies';

export const apolloCache = new InMemoryCache({
  typePolicies,
});
