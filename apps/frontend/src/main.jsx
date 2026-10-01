import React from "react";
import ReactDOM from "react-dom/client";
import { ApolloProvider } from "@apollo/client/react";
import client from "@/apollo/client";
import { SettingsProvider } from '@/store/settings/SettingsContext';
import { RouterProvider } from "react-router";
import router from "@/router";


// Ensure root element exists
const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Root element not found!");

// Render
ReactDOM.createRoot(rootElement).render(
  <ApolloProvider client={client}>
    <React.StrictMode>
      <SettingsProvider>
        <RouterProvider router={router} />
      </SettingsProvider>
    </React.StrictMode>
  </ApolloProvider>
);