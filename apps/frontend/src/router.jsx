import React, { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";
import Root from "@/root/Root";
import ErrorBoundary from "@/components/ErrorBoundary";

// Marketing
const Home = lazy(() => import("@/pages/home"));
const About = lazy(() => import("@/pages/about"));
const Pricing = lazy(() => import("@/pages/pricing"));
const Features = lazy(() => import("@/pages/features"));
const ContactUs = lazy(() => import("@/pages/contact-us"));
const FAQ = lazy(() => import("@/pages/faq"));
const Error404 = lazy(() => import("@/pages/error404"));

// Auth
const Account = lazy(() => import("@/pages/auth/account"));

const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    ErrorBoundary,
    children: [
      // Marketing
      { index: true, element: <Home /> },
      { path: "about", element: <About /> },
      { path: "pricing", element: <Pricing /> },
      { path: "features", element: <Features /> },
      { path: "contact", element: <ContactUs /> },
      { path: "faq", element: <FAQ /> },

      // Auth
      { path: "account", element: <Account /> },

      // Catch-all
      { path: "*", element: <Error404 /> },
    ],
  },
]);

export default router;