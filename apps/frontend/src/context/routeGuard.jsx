// src/context/RouteGuard.jsx
import React, { useContext } from "react";
import { Navigate, Outlet } from "react-router-dom";
import AuthContext from "@/context/authContext";

/**
 * RouteGuard ensures that only authenticated users can access protected routes.
 * If the user is not authenticated, they are redirected to the login page.
 */
const RouteGuard = () => {
  const { state } = useContext(AuthContext);

  if (!state?.isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

export default RouteGuard;
