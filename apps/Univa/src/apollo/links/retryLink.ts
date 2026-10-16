/**
 * Apollo retry link.
 *
 * Retries transient network failures with exponential backoff.
 * GraphQL errors are not retried by this link.
 */

import { RetryLink } from '@apollo/client/link/retry';

export const retryLink = new RetryLink({
  attempts: {
    max: 3,

    retryIf: (error) => {
      // Retry transport/network failures only.
      // GraphQL execution errors are handled separately.
      return Boolean(error);
    },
  },

  delay: {
    initial: 300,
    max: 3000,
    jitter: true,
  },
});
