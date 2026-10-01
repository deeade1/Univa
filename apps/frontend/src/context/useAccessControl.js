// src/context/useAccessControl.js
import { useNavigate } from "react-router-dom";
import { useAuth } from "./authContext";
import { getRequiredLevel, hasSufficientAuth, serviceAuthRequirements } from "./authUtils";

/**
 * Custom hook to manage access control logic.
 *
 * @param {Object} params
 * @param {string} params.to - The target route.
 * @param {string} [params.level] - Minimum required auth level.
 * @param {string} [params.service] - Service name for access check.
 * @param {boolean} [params.sensitive] - Whether this route requires re-authentication.
 * @returns {{ validate: () => boolean }}
 */
export function useAccessControl({ to, level, service, sensitive }) {
  const {
    user,
    authLevel: userAuthLevel,
    checkSession,
    getRemainingSessionTime,
    logAuthEvent,
  } = useAuth();

  const navigate = useNavigate();
  const requiredLevel = getRequiredLevel(service, level);
  const serviceConfig = service ? serviceAuthRequirements[service] : undefined;

  const validate = () => {
    // Log access attempt
    logAuthEvent({
      type: "login",
      service,
      metadata: {
        attempt: true,
        requiredLevel,
        sensitive,
        from: to,
      },
    });

    // Not logged in → redirect to login
    if (!user) {
      navigate("/login", {
        state: {
          from: to,
          requiredAuthLevel: requiredLevel,
          service,
          sensitive,
        },
      });
      return false;
    }

    // Auth level too low → redirect to upgrade page
    if (!hasSufficientAuth(userAuthLevel, requiredLevel)) {
      navigate("/upgrade-auth", {
        state: {
          requiredLevel,
          service,
          from: to,
          sensitive,
        },
      });
      return false;
    }

    // Sensitive route + session expired → reauth
    if (sensitive && !checkSession()) {
      navigate("/reauthenticate", {
        state: {
          from: to,
          remainingTime: getRemainingSessionTime(),
          service,
        },
      });
      return false;
    }

    // Optional: extend session for services with timeout
    if (serviceConfig?.timeout) {
      const expiry = new Date(Date.now() + serviceConfig.timeout * 60 * 1000);
      console.log(`Extending session for ${service} to ${expiry}`);
    }

    return true;
  };

  return { validate };
}
