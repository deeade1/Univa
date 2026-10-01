// src/context/authRequirements.jsx

/**
 * @typedef {'guest' | 'basic' | 'verified' | 'transaction' | 'real_estate' | 'ride' | 'logistics'} AuthLevel
 * Represents the user's authentication level.
 */

/**
 * @typedef {Object} ServiceRequirement
 * @property {AuthLevel} level - The required authentication level for the service.
 * @property {number} [timeout] - Optional timeout in minutes before session expiry.
 */

/**
 * @type {Record<string, ServiceRequirement>}
 */
export const serviceAuthRequirements = {
  general: { level: 'basic' },
  ecommerce: { level: 'basic' },
  taxi: { level: 'ride', timeout: 30 },
  logistics: { level: 'logistics', timeout: 60 },
  real_estate: { level: 'real_estate' },
  banking: { level: 'transaction', timeout: 15 },
};
