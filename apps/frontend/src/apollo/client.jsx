// src/apollo/client.js
import {
  ApolloClient,
  InMemoryCache,
  ApolloLink,
  HttpLink,
} from "@apollo/client";
import { onError } from "@apollo/client/link/error";
import { setContext } from "@apollo/client/link/context";
import { GraphQLWsLink } from "@apollo/client/link/subscriptions";
import { getMainDefinition } from "@apollo/client/utilities";
import { createClient } from "graphql-ws";
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "./auth";
import { REFRESH_TOKEN } from "@/queries/accountQuery/mutations";
import { print } from "graphql";

// GraphQL endpoints
const httpUri = import.meta.env.VITE_GRAPHQL_HTTP_URI;
const wsUri = import.meta.env.VITE_GRAPHQL_WS_URI;

// HTTP link
const httpLink = new HttpLink({
  uri: httpUri,
  credentials: "include",
});

// Refresh token logic
async function refreshTokens() {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) throw new Error("No refresh token found");

  const response = await fetch(httpUri, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: print(REFRESH_TOKEN),
      variables: { refreshToken },
    }),
  });

  const result = await response.json();

  if (result.errors || !result.data?.refreshToken) {
    throw new Error("Failed to refresh token");
  }

  const { token, refreshToken: newRefresh } = result.data.refreshToken;
  await setTokens(token, newRefresh);
  return token;
}

// Auth link
const authLink = setContext(async (_, { headers }) => {
  const token = await getAccessToken();
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : "",
    },
  };
});

// Error handling link
const errorLink = onError(({ graphQLErrors, networkError, operation, forward }) => {
  if (graphQLErrors) {
    for (const err of graphQLErrors) {
      if (err.message.includes("expired")) {
        return refreshTokens()
          .then((newToken) => {
            operation.setContext(({ headers = {} }) => ({
              headers: {
                ...headers,
                authorization: `Bearer ${newToken}`,
              },
            }));
            return forward(operation);
          })
          .catch(() => {
            clearTokens();
            window.location.href = "/login";
            return forward(operation);
          });
      }
    }
  }

  if (networkError) {
    console.error(`[Network error]: ${networkError}`);
  }
});

// WebSocket link
const wsLink = new GraphQLWsLink(
  createClient({
    url: wsUri,
    connectionParams: async () => ({
      authToken: await getAccessToken(),
    }),
    lazy: true,
    retryAttempts: 5,
  })
);

// Split HTTP vs WS
const splitLink = ApolloLink.split(
  ({ query }) => {
    const def = getMainDefinition(query);
    return def.kind === "OperationDefinition" && def.operation === "subscription";
  },
  wsLink,
  ApolloLink.from([errorLink, authLink, httpLink])
);

const client = new ApolloClient({
  link: splitLink,
  cache: new InMemoryCache(),
});

export default client;
