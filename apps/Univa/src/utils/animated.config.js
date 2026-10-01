import { Platform } from 'react-native';

// Only use native driver on native platforms
export const getAnimatedConfig = () => ({
  useNativeDriver: Platform.OS !== 'web',
});

// For animations
export const getAnimationConfig = (config = {}) => ({
  ...config,
  useNativeDriver: Platform.OS !== 'web',
});


/*import { getAnimationConfig } from '@/utils/animated.config';

Animated.timing(animation, {
  toValue: 1,
  duration: 300,
  ...getAnimationConfig(),
}).start();*/



