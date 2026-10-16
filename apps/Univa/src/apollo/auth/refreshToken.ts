/**
 * Refresh access tokens for Univa.
 *
 * Responsibilities:
 * - Refresh expired access tokens.
 * - Prevent concurrent duplicate refresh requests.
 * - Persist rotated tokens.
 * - Clear authentication only when refresh is rejected or invalid.
 *
 * This module uses fetch directly to avoid calling Apollo Client
 * from inside Apollo's authentication/error handling pipeline.
 */

import { apolloEnv } from '../env';
import { tokenStorage } from './tokenStorage';
import { setAuthStatus } from './authState';

interface RefreshTokenPayload {
  token: string;
  refreshToken?: string | null;
}

interface RefreshGraphQLResponse {
  data?: {
    refreshToken?: RefreshTokenPayload | null;
  } | null;
  errors?: Array<{
    message: string;
  }>;
}

const REFRESH_TOKEN_MUTATION = `
  mutation RefreshToken($refreshToken: String!) {
    refreshToken(input: { refreshToken: $refreshToken }) {
      token
      refreshToken
    }
  }
`;

let refreshPromise: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
  const currentRefreshToken = await tokenStorage.getRefreshToken();

  if (!currentRefreshToken) {
    await tokenStorage.clear();
    setAuthStatus('unauthenticated');
    return null;
  }

  let response: Response;

  try {
    response = await fetch(apolloEnv.httpUri, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        query: REFRESH_TOKEN_MUTATION,
        variables: {
          refreshToken: currentRefreshToken,
        },
      }),
    });
  } catch {
    // A network failure does not necessarily mean the token is invalid.
    // Preserve stored credentials so the user can retry when online.
    throw new Error('Unable to reach the authentication server.');
  }

  if (!response.ok) {
    // Server errors such as HTTP 500 should not automatically log
    // the user out. Treat an HTTP 401/403 as rejected credentials.
    if (response.status === 401 || response.status === 403) {
      await tokenStorage.clear();
      setAuthStatus('unauthenticated');
      return null;
    }

    throw new Error(
      `Token refresh failed with HTTP ${response.status}.`,
    );
  }

  let result: RefreshGraphQLResponse;

  try {
    result = (await response.json()) as RefreshGraphQLResponse;
  } catch {
    throw new Error('The authentication server returned invalid JSON.');
  }

  if (result.errors?.length) {
    // A GraphQL error can indicate an expired or invalid refresh token.
    // Keep this failure explicit rather than silently returning a token.
    await tokenStorage.clear();
    setAuthStatus('unauthenticated');
    return null;
  }

  const refreshed = result.data?.refreshToken;

  if (!refreshed?.token) {
    await tokenStorage.clear();
    setAuthStatus('unauthenticated');
    return null;
  }

  await tokenStorage.setAccessToken(refreshed.token);

  // Some JWT configurations rotate refresh tokens; others may not.
  // Preserve the existing token if the response omits a replacement.
  if (refreshed.refreshToken) {
    await tokenStorage.setRefreshToken(refreshed.refreshToken);
  }

  setAuthStatus('authenticated');

  return refreshed.token;
}

/**
 * Returns a fresh access token, or null when refresh is rejected.
 * Concurrent callers share the same in-flight refresh request.
 */
export function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = performRefresh().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}
