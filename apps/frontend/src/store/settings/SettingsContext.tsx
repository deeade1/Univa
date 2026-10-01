// apps/frontend/src/store/settings/SettingsContext.tsx

import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { SettingState } from './interface';
import { initialState } from './state';
import { settingsReducer } from './settingsReducer';
import { getStorage } from '@/utilities/setting';

// Type guard to check if the loaded settings are valid
function isSettingState(obj: unknown): obj is SettingState {
  return typeof obj === 'object' && obj !== null && 'saveLocal' in obj && 'setting' in obj;
}

// Ensure fallback values for required settings
function ensureSafeSettings(settings: SettingState['setting']): SettingState['setting'] {
  return {
    ...settings,
    theme_scheme_direction: {
      ...settings.theme_scheme_direction,
      value: settings.theme_scheme_direction.value || 'ltr',
    },
    body_font_family: {
      ...settings.body_font_family,
      value: settings.body_font_family.value || 'Inter',
    },
    heading_font_family: {
      ...settings.heading_font_family,
      value: settings.heading_font_family.value || 'Inter',
    },
  };
}

// Context type
type SettingsContextType = {
  state: SettingState;
  reset: () => void;
  updateSetting: <K extends keyof SettingState['setting']>(
    key: K,
    value: SettingState['setting'][K]['value']
  ) => void;
  updateThemeColor: (payload: { colors: Record<string, string>; value: string }) => void;
  saveLocal: (location: SettingState['saveLocal']) => void;
};

// Create context
const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

// Provider
export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(settingsReducer, initialState);

  useEffect(() => {
    const json = getStorage(state.storeKey);
    if (json !== 'none' && isSettingState(json)) {
      const safeSettings = ensureSafeSettings(json.setting);
      dispatch({
        type: 'UPDATE_SETTING',
        payload: {
          key: 'theme_scheme_direction',
          value: safeSettings.theme_scheme_direction.value,
        },
      });
    }
  }, []);

  const reset = () => dispatch({ type: 'RESET' });

  const updateSetting = <K extends keyof SettingState['setting']>(
    key: K,
    value: SettingState['setting'][K]['value']
  ): void => {
    dispatch({
      type: 'UPDATE_SETTING',
      payload: { key, value },
    });
  };

  const updateThemeColor = (payload: { colors: Record<string, string>; value: string }) => {
    dispatch({ type: 'UPDATE_THEME_COLOR', payload });
  };

  const saveLocal = (location: SettingState['saveLocal']) => {
    dispatch({ type: 'SET_SAVE_LOCATION', payload: location });
  };

  return (
    <SettingsContext.Provider
      value={{ state, reset, updateSetting, updateThemeColor, saveLocal }}
    >
      {children}
    </SettingsContext.Provider>
  );
};

// Hook
export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};
