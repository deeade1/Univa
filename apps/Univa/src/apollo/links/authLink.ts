/**
 * Apollo authentication link.
 *
 * Adds the current access token to outgoing HTTP operations.
 * The token is read for each operation so refreshed credentials
 * are used by subsequent requests.
 */

import { SetContextLink } from '@apollo/client/link/context';

import { tokenStorage } from '../auth/tokenStorage';

export const authLink = new SetContextLink(
  async (previousContext) => {
    const token = await tokenStorage.getAccessToken();

    return {
      headers: {
        ...previousContext.headers,
        ...(token
          ? { Authorization: `Bearer ${token}` }
          : {}),
      },
    };
  },
);
