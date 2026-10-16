/**
 * Persistent authentication storage for Univa.
 *
 * Storage keys are centralized to prevent inconsistencies
 * between login, logout, refresh, HTTP, and WebSocket auth.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

export const AUTH_STORAGE_KEYS = {
  accessToken: 'auth_token',
  refreshToken: 'refresh_token',
  userData: 'user_data',
} as const;

export type AuthStorageKey =
  (typeof AUTH_STORAGE_KEYS)[keyof typeof AUTH_STORAGE_KEYS];

export const tokenStorage = {
  async getAccessToken(): Promise<string | null> {
    return AsyncStorage.getItem(AUTH_STORAGE_KEYS.accessToken);
  },

  async setAccessToken(token: string): Promise<void> {
    await AsyncStorage.setItem(
      AUTH_STORAGE_KEYS.accessToken,
      token,
    );
  },

  async getRefreshToken(): Promise<string | null> {
    return AsyncStorage.getItem(AUTH_STORAGE_KEYS.refreshToken);
  },

  async setRefreshToken(token: string): Promise<void> {
    await AsyncStorage.setItem(
      AUTH_STORAGE_KEYS.refreshToken,
      token,
    );
  },

  async getUserData(): Promise<string | null> {
    return AsyncStorage.getItem(AUTH_STORAGE_KEYS.userData);
  },

  async setUserData(userData: string): Promise<void> {
    await AsyncStorage.setItem(
      AUTH_STORAGE_KEYS.userData,
      userData,
    );
  },

  async removeAccessToken(): Promise<void> {
    await AsyncStorage.removeItem(AUTH_STORAGE_KEYS.accessToken);
  },

  async removeRefreshToken(): Promise<void> {
    await AsyncStorage.removeItem(AUTH_STORAGE_KEYS.refreshToken);
  },

  async removeUserData(): Promise<void> {
    await AsyncStorage.removeItem(AUTH_STORAGE_KEYS.userData);
  },

  async clear(): Promise<void> {
    await AsyncStorage.multiRemove([
      AUTH_STORAGE_KEYS.accessToken,
      AUTH_STORAGE_KEYS.refreshToken,
      AUTH_STORAGE_KEYS.userData,
    ]);
  },
};