
// @ts-ignore CSS side-effect imports are handled by the bundler.
import '@/global.css';
import { Platform } from 'react-native';

const univaColors = {
  text: '#172033',
  background: '#F7F8FC',
  backgroundElement: '#FFFFFF',
  backgroundSelected: '#E8EEFF',
  textSecondary: '#697386',
  primary: '#3659E3',
  primaryDark: '#2445C5',
  border: '#E7EAF1',
  success: '#16865C',
  surfaceBlue: '#EDF1FF',
} as const;

export const Colors = {
  light: { ...univaColors },
  dark: { ...univaColors },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

export const Fonts = Platform.select({
  ios: {
    sans: 'system-ui',
    serif: 'ui-serif',
    rounded: 'ui-rounded',
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: 'var(--font-display)',
    serif: 'var(--font-serif)',
    rounded: 'var(--font-rounded)',
    mono: 'var(--font-mono)',
  },
});

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const Radius = {
  small: 10,
  medium: 16,
  large: 24,
  pill: 999,
} as const;

export const BottomTabInset = Platform.select({
  ios: 92,
  android: 88,
  default: 88,
}) ?? 88;

export const MaxContentWidth = 800;
