// apps/Univa/src/theme/index.js
import colors from "./colors";
import spacing from "./spacing";
import typography from "./typography";
import radius from "./radius";
import shadows from "./shadows";

// Create a simple useTheme hook
export const useTheme = () => {
  return {
    colors,
    spacing,
    typography,
    radius,
    shadows,
  };
};

// Export all theme values
export {
  colors,
  spacing,
  typography,
  radius,
  shadows,
};

// Default export
export default {
  colors,
  spacing,
  typography,
  radius,
  shadows,
};