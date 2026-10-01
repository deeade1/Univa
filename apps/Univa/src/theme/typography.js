/* -------------------------------------------------------------------------- */
/* apps/Univa/src/theme/typography.js                                          */
/* -------------------------------------------------------------------------- */

const typography = {
  // ==========================================================================
  // Semantic Styles
  // ==========================================================================

  h1: {
    fontSize: 32,
    fontWeight: "800",
  },

  h2: {
    fontSize: 24,
    fontWeight: "700",
  },

  h3: {
    fontSize: 20,
    fontWeight: "700",
  },

  h4: {
    fontSize: 18,
    fontWeight: "600",
  },

  body: {
    fontSize: 16,
    fontWeight: "400",
  },

  bodyMedium: {
    fontSize: 16,
    fontWeight: "500",
  },

  caption: {
    fontSize: 12,
    fontWeight: "400",
  },

  small: {
    fontSize: 10,
    fontWeight: "500",
  },

  button: {
    fontSize: 15,
    fontWeight: "600",
  },

  // ==========================================================================
  // Font Size Constants (Backward Compatibility)
  // ==========================================================================

  fontSize: {
    xs: 10,      // Extra Small
    sm: 12,      // Small
    md: 14,      // Medium
    lg: 16,      // Large (Body size)
    xl: 18,      // Extra Large (h4 size)
    xxl: 20,     // Extra Extra Large (h3 size)
    xxxl: 24,    // Extra Extra Extra Large (h2 size)
    xxxxl: 32,   // Extra Extra Extra Extra Large (h1 size)
  },

  // ==========================================================================
  // Font Weight Constants (Backward Compatibility)
  // ==========================================================================

  fontWeight: {
    normal: "400",
    medium: "500",
    semibold: "600",
    bold: "700",
    extrabold: "800",
  },

  // ==========================================================================
  // Line Height Constants (Optional)
  // ==========================================================================

  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
};

export default typography;