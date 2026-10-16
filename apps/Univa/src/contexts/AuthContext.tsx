
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react';

import { tokenStorage } from '../apollo/auth/tokenStorage';
import {
  getAuthStatus,
  initializeAuthState,
  setAuthStatus,
  subscribeAuthState,
  type AuthStatus,
} from '../apollo/auth/authState';

export type AuthUser = {
  id: string;
  email: string | null;
  firstName?: string | null;
  lastName?: string | null;
  phoneNumber?: string | null;
  displayName?: string | null;
  isEmailVerified?: boolean | null;
};

type AuthContextValue = {
  user: AuthUser | null;
  authStatus: AuthStatus;
  isAuthenticated: boolean;
  isInitializing: boolean;
  login: (user: AuthUser) => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authStatus, setLocalAuthStatus] =
    useState<AuthStatus>(getAuthStatus);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    let active = true;

    const unsubscribe = subscribeAuthState((status) => {
      if (active) {
        setLocalAuthStatus(status);
      }
    });

    async function restoreSession() {
      try {
        const status = await initializeAuthState();

        if (!active) return;

        if (status === 'authenticated') {
          const storedUser = await tokenStorage.getUserData();

          if (!active) return;

          if (storedUser) {
            try {
              setUser(JSON.parse(storedUser) as AuthUser);
            } catch {
              await tokenStorage.clear();
              setUser(null);
              setAuthStatus('unauthenticated');
            }
          } else {
            setUser(null);
          }
        } else {
          setUser(null);
        }
      } catch (error) {
        if (__DEV__) {
          console.error('[Auth] Session initialization failed.', error);
        }
        if (active) {
          setUser(null);
          setAuthStatus('unauthenticated');
        }
      } finally {
        if (active) {
          setIsInitializing(false);
        }
      }
    }

    void restoreSession();

    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const login = useCallback((authenticatedUser: AuthUser) => {
    setUser(authenticatedUser);
    setAuthStatus('authenticated');
  }, []);

  const logout = useCallback(async () => {
    await tokenStorage.clear();
    setUser(null);
    setAuthStatus('unauthenticated');
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      authStatus,
      isAuthenticated: authStatus === 'authenticated',
      isInitializing,
      login,
      logout,
    }),
    [user, authStatus, isInitializing, login, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }

  return context;
}
