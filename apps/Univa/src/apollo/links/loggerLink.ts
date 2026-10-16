/**
 * Apollo development logger.
 *
 * Logs operation names and outcomes only.
 * Does not log headers, variables, or authentication tokens.
 */

import { ApolloLink } from '@apollo/client';
import { tap } from 'rxjs';

export const loggerLink = new ApolloLink(
  (operation, forward) => {
    const operationName =
      operation.operationName || 'AnonymousOperation';

    if (__DEV__) {
      console.debug(`[Apollo] → ${operationName}`);
    }

    return forward(operation).pipe(
      tap({
        next: (result) => {
          if (!__DEV__) {
            return;
          }

          if (result.errors?.length) {
            console.warn(
              `[Apollo] GraphQL errors in ${operationName}`,
            );
          } else {
            console.debug(`[Apollo] ✓ ${operationName}`);
          }
        },

        error: () => {
          if (__DEV__) {
            console.warn(
              `[Apollo] Request failed: ${operationName}`,
            );
          }
        },
      }),
    );
  },
);
