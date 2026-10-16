/**
 * Apollo Client DevTools registration for VS Code.
 *
 * Development-only integration.
 * Does not run in production or when no DevTools URI is configured.
 */

import type { ApolloClient } from '@apollo/client';
import {
  connectApolloClientToVSCodeDevTools,
} from '@apollo/client-devtools-vscode';

import { apolloEnv } from '../env';

type DevToolsRegistration = ReturnType<
  typeof connectApolloClientToVSCodeDevTools
>;

let registration: DevToolsRegistration | undefined;
let registeredClient: ApolloClient | undefined;

export function registerApolloDevTools(
  client: ApolloClient,
): DevToolsRegistration | undefined {
  if (!__DEV__ || !apolloEnv.devtoolsUri) {
    return undefined;
  }

  // Avoid registering the same client more than once.
  if (registeredClient === client) {
    return registration;
  }

  registration = connectApolloClientToVSCodeDevTools(
    client,
    apolloEnv.devtoolsUri,
  );

  registeredClient = client;

  return registration;
}
