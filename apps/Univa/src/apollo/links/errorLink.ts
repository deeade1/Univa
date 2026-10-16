/**
 * Apollo Client 4 error handling.
 *
 * - Detects GraphQL authentication failures.
 * - Refreshes the access token at most once per operation.
 * - Retries the failed operation with the new token.
 * - Avoids retry loops.
 */

import {
  CombinedGraphQLErrors,
} from '@apollo/client/errors';
import { ErrorLink } from '@apollo/client/link/error';
import { Observable } from 'rxjs';

import { setAuthStatus } from '../auth/authState';
import { refreshAccessToken } from '../auth/refreshToken';
import { tokenStorage } from '../auth/tokenStorage';

const AUTH_ERROR_MESSAGES = [
  'unauthenticated',
  'authentication credentials were not provided',
  'invalid token',
  'signature has expired',
  'token has expired',
  'permission denied',
];

function isAuthenticationError(message: string): boolean {
  const normalized = message.toLowerCase();

  return AUTH_ERROR_MESSAGES.some((phrase) =>
    normalized.includes(phrase),
  );
}

export const errorLink = new ErrorLink(
  ({ error, operation, forward }) => {
    const alreadyRetried =
      operation.getContext().authRetryAttempted === true;

    if (alreadyRetried || !CombinedGraphQLErrors.is(error)) {
      return;
    }

    const hasAuthenticationError = error.errors.some(
      (graphQLError) =>
        isAuthenticationError(graphQLError.message),
    );

    if (!hasAuthenticationError) {
      return;
    }

    operation.setContext({
      authRetryAttempted: true,
    });

    return new Observable((observer) => {
      let cancelled = false;
      let subscription:
        | { unsubscribe: () => void }
        | undefined;

      refreshAccessToken()
        .then(async (newAccessToken) => {
          if (cancelled) {
            return;
          }

          if (!newAccessToken) {
            await tokenStorage.clear();
            setAuthStatus('unauthenticated');
            observer.complete();
            return;
          }

          operation.setContext(({ headers = {} }) => ({
            headers: {
              ...headers,
              Authorization: `Bearer ${newAccessToken}`,
            },
          }));

          subscription = forward(operation).subscribe({
            next: (value) => observer.next(value),
            error: (retryError) => observer.error(retryError),
            complete: () => observer.complete(),
          });
        })
        .catch((refreshError: unknown) => {
          if (!cancelled) {
            observer.error(refreshError);
          }
        });

      return () => {
        cancelled = true;
        subscription?.unsubscribe();
      };
    });
  },
);
