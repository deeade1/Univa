// src/context/authUtils.js

export const authHierarchy = {
  guest: 0,
  basic: 1,
  verified: 2,
  ride: 3,
  logistics: 3,
  transaction: 4,
  real_estate: 5,
};

export const serviceAuthRequirements = {
  general: { level: "basic", timeout: 1440, idleTimeout: 30, mfaRequired: false },
  ecommerce: { level: "basic", timeout: 1440, idleTimeout: 30, mfaRequired: false },
  taxi: { level: "ride", timeout: 30, idleTimeout: 10, mfaRequired: false },
  logistics: { level: "logistics", timeout: 60, idleTimeout: 15, mfaRequired: false },
  real_estate: { level: "real_estate", timeout: 240, idleTimeout: 15, mfaRequired: true },
  banking: { level: "transaction", timeout: 120, idleTimeout: 5, mfaRequired: true },
};

/**
 * Get the required authentication level for a given service.
 * @param {string} [service] - The service name (optional)
 * @param {string} [level] - Explicit auth level (optional)
 * @returns {string} - The required auth level
 */
export function getRequiredLevel(service, level) {
  if (level) return level;
  if (service) return serviceAuthRequirements[service]?.level || "basic";
  return "basic";
}

/**
 * Check if a user's auth level meets or exceeds the required level.
 * @param {string} userLevel
 * @param {string} requiredLevel
 * @returns {boolean}
 */
export function hasSufficientAuth(userLevel, requiredLevel) {
  return authHierarchy[userLevel] >= authHierarchy[requiredLevel];
}
