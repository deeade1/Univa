import { ApolloClient } from '@apollo/client';

import { apolloCache } from './cache';
import { apolloEnv } from './env';
import { splitLink } from './links/splitLink';
import { registerApolloDevTools } from './devtools/register';

export const apolloClient = new ApolloClient({
  cache: apolloCache,
  link: splitLink,
  devtools: {
    enabled: __DEV__,
  },
});

registerApolloDevTools(apolloClient);
