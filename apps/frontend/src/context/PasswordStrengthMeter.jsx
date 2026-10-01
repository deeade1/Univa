// src/context/PasswordStrengthMeter.jsx
import { useEffect, useState } from "react";

/**
 * Calculates a password strength score from 0–100.
 * @param {string} password
 * @returns {number}
 */
const calculateStrength = (password) => {
  let score = 0;
  if (!password) return 0;

  // Length scoring
  if (password.length > 5) score += 1;
  if (password.length > 8) score += 1;
  if (password.length > 12) score += 1;

  // Complexity scoring
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  return Math.min(score, 5) * 20; // Cap at 100
};

/**
 * Determines the color level for the strength bar.
 * @param {number} strength
 * @returns {'danger' | 'warning' | 'success'}
 */
const getStrengthColor = (strength) => {
  if (strength < 40) return "danger";
  if (strength < 70) return "warning";
  return "success";
};

/**
 * Returns a descriptive label for the password strength.
 * @param {number} strength
 * @returns {string}
 */
const getStrengthLabel = (strength) => {
  if (strength < 20) return "Very Weak";
  if (strength < 40) return "Weak";
  if (strength < 60) return "Fair";
  if (strength < 80) return "Good";
  return "Strong";
};

/**
 * @param {{ password: string }} props
 */
export const PasswordStrengthMeter = ({ password }) => {
  const [strength, setStrength] = useState(0);

  useEffect(() => {
    setStrength(calculateStrength(password));
  }, [password]);

  return (
    <div className="password-strength mt-2">
      <div className="progress" style={{ height: "5px" }}>
        <div
          className={`progress-bar bg-${getStrengthColor(strength)}`}
          role="progressbar"
          style={{ width: `${strength}%` }}
          aria-valuenow={strength}
          aria-valuemin={0}
          aria-valuemax={100}
        ></div>
      </div>
      <small className={`text-${getStrengthColor(strength)}`}>
        {getStrengthLabel(strength)}
      </small>
    </div>
  );
};
