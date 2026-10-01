// src/context/sessionTimeoutHandler.jsx
import React, { useEffect } from "react";
import { useAuth } from "./authContext";

export const SessionTimeoutHandler = () => {
  const { sessionExpiry, logout } = useAuth();

  useEffect(() => {
    if (!sessionExpiry) return;

    const checkExpiry = () => {
      const now = new Date();
      if (sessionExpiry <= now) {
        console.warn("🔒 Session expired");
        logout();
      }
    };

    const interval = setInterval(checkExpiry, 30 * 1000); // check every 30s
    return () => clearInterval(interval);
  }, [sessionExpiry, logout]);

  return null;
};
