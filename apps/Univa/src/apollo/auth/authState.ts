/**
 * Lightweight in-memory authentication state.
 *
 * This is not the source of truth for credentials:
 * tokenStorage remains responsible for persistent storage.
 */

import { tokenStorage } from './tokenStorage';

export type AuthStatus =
  | 'unknown'
  | 'authenticated'
  | 'unauthenticated';

type AuthStateListener = (status: AuthStatus) => void;

let authStatus: AuthStatus = 'unknown';

const listeners = new Set<AuthStateListener>();

export function getAuthStatus(): AuthStatus {
  return authStatus;
}

export function setAuthStatus(nextStatus: AuthStatus): void {
  if (authStatus === nextStatus) {
    return;
  }

  authStatus = nextStatus;

  for (const listener of listeners) {
    listener(authStatus);
  }
}

export function subscribeAuthState(
  listener: AuthStateListener,
): () => void {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

/**
 * Call during application startup to restore the initial
 * authentication status from persistent token storage.
 */
export async function initializeAuthState(): Promise<AuthStatus> {
  const accessToken = await tokenStorage.getAccessToken();

  const nextStatus: AuthStatus = accessToken
    ? 'authenticated'
    : 'unauthenticated';

  setAuthStatus(nextStatus);

  return nextStatus;
}
