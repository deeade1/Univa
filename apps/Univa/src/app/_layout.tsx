
import { DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';

import { AnimatedSplashOverlay } from '@/components/animated-icon';
import { ShoppingCartProvider } from '@/contexts/shopping-cart-context';
import { AppProviders } from '@/providers/AppProviders';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  return (
    <ThemeProvider value={DefaultTheme}>
      <AppProviders>
        <ShoppingCartProvider>
          <AnimatedSplashOverlay />

          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="shopping" />
            <Stack.Screen name="auth" />
          </Stack>
        </ShoppingCartProvider>
      </AppProviders>
    </ThemeProvider>
  );
}
