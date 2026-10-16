/**
 * Apollo cache type policies for Univa.
 *
 * Keep entity identification and field policies centralized.
 * Add custom policies only when they match the backend schema.
 */

import type { TypePolicies } from '@apollo/client';

export const typePolicies: TypePolicies = {
  Query: {
    fields: {
      // Add field-specific cache policies here when required.
    },
  },

  Mutation: {
    fields: {
      // Mutation results are not cached as a separate root store.
      // Add field policies here only when explicitly needed.
    },
  },
};
