// apps/frontend/src/utilities/setting.ts
import { getColorShadeTint } from './colors';
import { getRootVars, setRootVariables, setFontFamily } from './root-var';
import { addClass, removeClass, setAttr, setContent } from './dom';

// Update body classes: remove old, add new
export const updateBodyClass = (choices: string[], value: string | string[]): void => {
  if (choices.length > 0) {
    choices.forEach((other) => removeClass('body', other));
  }
  if (Array.isArray(value)) {
    value.forEach((val) => addClass('body', val));
  } else {
    addClass('body', value);
  }
};

// Update HTML tag attributes
export const updateHtmlAttr = (value: { prop: string; value: string }): void => {
  setAttr('html', value);
};

// Update HTML classes: remove old, add new
export const updateHtmlClass = (choices: string[], value: string): void => {
  if (choices.length > 0) {
    choices.forEach((other) => removeClass('html', other));
  }
  addClass('html', value);
};

// Update app title in DOM
export const updateTitle = (value: string): void => {
  setContent('[data-setting="app_name"]', value);
};

// Update root variables for theme color & scheme
export const updateColorRootVar = (
  themeScheme: string,
  themeColor: { colors: Record<string, string>; value: string },
  choices: string[]
): void => {
  const prefix = getRootVars("--prefix") || "bs-";
  let newColors: Record<string, string> = {};
  const isDark = themeScheme !== 'light' && themeScheme !== 'auto';

  for (const [keyRaw, value] of Object.entries(themeColor.colors)) {
    try {
      const key = keyRaw.replace("{{prefix}}", prefix);
      Object.assign(newColors, getColorShadeTint(key, value, isDark));
    } catch (error) {
      console.error(`Error processing color ${keyRaw}:`, error);
    }
  }

  setRootVariables(newColors);
  removeClass("body", ...choices);
  addClass("body", themeColor.value);
};

// Type for the setting object structure
interface AppSetting {
  theme_scheme_direction: { value: string };
  theme_scheme: { value: string };
  theme_font_size: { value: string };
  theme_style_appearance: { value: string | string[] };
  theme_transition: { value: string };
  app_name: { value: string };
  body_font_family: { value: string | null };
  heading_font_family: { value: string | null };
  theme_color: { colors: Record<string, string>; value: string };
}

// Apply settings to DOM
export const updateDomValueBySetting = (
  setting: AppSetting,
  Choices: Record<string, string[]>
): void => {
  updateHtmlAttr({ prop: 'dir', value: setting.theme_scheme_direction.value });
  updateThemeScheme(setting.theme_scheme.value, Choices, setting.theme_color);
  updateHtmlClass(Choices.FSChoice, setting.theme_font_size.value);
  updateBodyClass(Choices.StyleAppearanceChoice, setting.theme_style_appearance.value);
  updateBodyClass(Choices.Animation, setting.theme_transition.value);
  updateTitle(setting.app_name.value);
  
  if (setting.body_font_family.value) {
    setFontFamily('body', setting.body_font_family.value);
  }
  
  if (setting.heading_font_family.value) {
    setFontFamily('heading', setting.heading_font_family.value);
  }
};

// Storage types
type StorageType = 'localStorage' | 'sessionStorage' | 'none';

// Save to localStorage/sessionStorage
export const updateStorage = (
  storage: StorageType,
  key: string,
  value: unknown
): void => {
  if (typeof key !== 'string' || key.trim() === '') {
    console.error('Invalid storage key');
    return;
  }

  try {
    if (storage === 'localStorage') {
      sessionStorage.removeItem(key);
      localStorage.setItem(key, JSON.stringify(value));
    } else if (storage === 'sessionStorage') {
      localStorage.removeItem(key);
      sessionStorage.setItem(key, JSON.stringify(value));
    } else {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
      localStorage.setItem(key, 'none');
      sessionStorage.setItem(key, 'none');
    }
  } catch (error) {
    console.error('Error updating storage:', error);
  }
};

// Get from localStorage/sessionStorage
export const getStorage = (key: string): unknown => {
  if (typeof key !== 'string' || key.trim() === '') {
    console.error('Invalid storage key');
    return null;
  }

  try {
    if (localStorage.getItem(key) === 'none' || sessionStorage.getItem(key) === 'none') {
      return 'none';
    }

    const value = localStorage.getItem(key) || sessionStorage.getItem(key);

    if (value !== null && value !== '') {
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    }
    return null;
  } catch (error) {
    console.error('Error accessing storage:', error);
    return null;
  }
};

// Update theme scheme and re-apply colors
export const updateThemeScheme = (
  value: string,
  Choices: Record<string, string[]>,
  themeColor: { colors: Record<string, string>; value: string }
): void => {
  const classNames: string[] = [];
  if (value === 'auto') {
    classNames.push('auto');
    if (window.matchMedia("(prefers-color-scheme: light)").matches) {
      classNames.push('light');
    } else {
      classNames.push('dark');
    }
  } else {
    classNames.push(value);
  }

  const filterValue = classNames.filter((x) => x !== 'auto');
  updateBodyClass(Choices.SchemeChoice, classNames);
  updateColorRootVar(filterValue[0] || '', themeColor, Choices.ColorChoice);
};