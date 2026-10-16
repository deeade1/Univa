/**
 * GraphQL WebSocket transport for Univa subscriptions.
 *
 * Uses graphql-ws and authenticates each connection with the
 * latest stored access token.
 */

import { GraphQLWsLink } from '@apollo/client/link/subscriptions';
import { createClient } from 'graphql-ws';

import { apolloEnv } from '../env';
import { tokenStorage } from '../auth/tokenStorage';

export const wsLink = apolloEnv.enableWebSocket
  ? new GraphQLWsLink(
      createClient({
        url: apolloEnv.wsUri,

        connectionParams: async () => {
          const token = await tokenStorage.getAccessToken();

          return token
            ? {
                authorization: `Bearer ${token}`,
              }
            : {};
        },

        retryAttempts: 5,

        shouldRetry: () => apolloEnv.enableWebSocket,

        on: {
          connected: () => {
            if (__DEV__) {
              console.debug('[Apollo WS] Connected');
            }
          },

        closed: () => {
        if (__DEV__) {
            console.debug('[Apollo WS] Closed');
        }
        },

        },
      }),
    )
  : null;
