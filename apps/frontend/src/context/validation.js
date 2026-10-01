// src/context/validation.js

/**
 * Validate an email string using a basic regex pattern.
 * @param {string} email
 * @returns {boolean}
 */
export const validateEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

/**
 * Validate a phone number with optional "+" and simple digit format.
 * @param {string} phone
 * @returns {boolean}
 */
export const validatePhone = (phone) => {
  return /^\+?[\d\s-]{10,}$/.test(phone);
};

/**
 * Validate a general contact (email or phone).
 * @param {string} contact
 * @returns {{ isValid: boolean, isEmail: boolean, isPhone: boolean }}
 */
export const validateContact = (contact) => {
  const isEmail = validateEmail(contact);
  const isPhone = validatePhone(contact);
  return {
    isValid: isEmail || isPhone,
    isEmail,
    isPhone
  };
};
