
/**
 * Apollo environment configuration.
 *
 * Keep environment variables in one place.
 * Expo public variables are bundled into the client app,
 * so never put secrets in EXPO_PUBLIC_* variables.
 */

const DEFAULT_HTTP_URI = "http://10.0.2.2:8000/graphql/";
const DEFAULT_WS_URI = "ws://10.0.2.2:8000/graphql/";

function normalizeEndpoint(value: string): string {
  return value.trim();
}

const offline = process.env.EXPO_OFFLINE === "true";

export const apolloEnv = {
  httpUri: normalizeEndpoint(
    process.env.EXPO_PUBLIC_GRAPHQL_HTTP_URI || DEFAULT_HTTP_URI,
  ),

  wsUri: normalizeEndpoint(
    process.env.EXPO_PUBLIC_GRAPHQL_WS_URI || DEFAULT_WS_URI,
  ),

  devtoolsUri: normalizeEndpoint(
    process.env.EXPO_PUBLIC_APOLLO_DEVTOOLS_WS_URI || "",
  ),

  offline,

  enableLogging: __DEV__,
  enableWebSocket: !offline,
} as const;
