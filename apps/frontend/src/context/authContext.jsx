// src/context/authContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/apollo/auth";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpiry, setSessionExpiry] = useState();

  useEffect(() => {
    const loadTokens = async () => {
      const token = await getAccessToken();
      const refresh = await getRefreshToken();
      setAccessToken(token);
      setRefreshToken(refresh);
      setLoading(false);
    };
    loadTokens();
  }, []);

  const login = async ({ token, refreshToken, user }) => {
    await setTokens(token, refreshToken);
    setAccessToken(token);
    setRefreshToken(refreshToken ?? null);
    setUser(user ?? null);
  };

  const logout = async () => {
    await clearTokens();
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    setSessionExpiry(undefined);
  };

  const checkSession = () => {
    if (!sessionExpiry) return true;
    return new Date() < sessionExpiry;
  };

  const getRemainingSessionTime = () => {
    if (!sessionExpiry) return 0;
    return sessionExpiry.getTime() - Date.now();
  };

  const logAuthEvent = (event) => {
    console.log("Auth event:", event);
  };

  const authLevel = user?.authLevel || "guest";

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        refreshToken,
        user,
        loading,
        authLevel,
        sessionExpiry,
        login,
        logout,
        checkSession,
        getRemainingSessionTime,
        logAuthEvent,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
