/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/SellerBadge.jsx         */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Safely applies opacity to a color
 * Supports hex, rgb, rgba, and named colors
 */
const withOpacity = (color, opacity) => {
  if (!color) return color;

  // If it's already a hex color
  if (color.startsWith('#')) {
    const hex = color.replace('#', '');
    const alpha = Math.round(opacity * 255).toString(16).padStart(2, '0');
    return `#${hex}${alpha}`;
  }

  // If it's rgb/rgba
  if (color.startsWith('rgb')) {
    const matches = color.match(/\d+/g);
    if (matches && matches.length >= 3) {
      const [r, g, b] = matches;
      return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }
  }

  // Fallback: return original color
  return color;
};

/* -------------------------------------------------------------------------- */
/* Badge Configuration                                                        */
/* -------------------------------------------------------------------------- */

const BADGE_CONFIG = {
  VERIFIED: {
    label: "Verified",
    icon: "check-decagram",
    color: theme.colors?.success || "#10B981",
  },

  OFFICIAL_STORE: {
    label: "Official Store",
    icon: "store-check",
    color: theme.colors?.primary || "#3B82F6",
  },

  TOP_SELLER: {
    label: "Top Seller",
    icon: "trophy-award",
    color: theme.colors?.warning || "#F59E0B",
  },

  PREMIUM: {
    label: "Premium",
    icon: "diamond-stone",
    color: theme.colors?.purple || "#8B5CF6",
  },

  TRUSTED: {
    label: "Trusted",
    icon: "shield-check",
    color: theme.colors?.success || "#22C55E",
  },

  FAST_SHIPPER: {
    label: "Fast Shipper",
    icon: "truck-fast",
    color: theme.colors?.cyan || "#06B6D4",
  },

  RECOMMENDED: {
    label: "Recommended",
    icon: "thumb-up",
    color: theme.colors?.error || "#EF4444",
  },

  NEW: {
    label: "New Seller",
    icon: "star-outline",
    color: theme.colors?.pink || "#EC4899",
  },
};

// Freeze for immutability
Object.freeze(BADGE_CONFIG);

/* -------------------------------------------------------------------------- */
/* Size Configuration                                                         */
/* -------------------------------------------------------------------------- */

const SIZE_MAP = {
  small: {
    iconSize: 12,
    fontSize: 11,
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  medium: {
    iconSize: 14,
    fontSize: 13,
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  large: {
    iconSize: 18,
    fontSize: 15,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
};

Object.freeze(SIZE_MAP);

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerBadge = memo(({
  /* ---------------------------------------------------------------------- */
  /* Badge Configuration                                                    */
  /* ---------------------------------------------------------------------- */

  type = "VERIFIED",
  label,
  icon,
  color,

  /* ---------------------------------------------------------------------- */
  /* Display                                                                */
  /* ---------------------------------------------------------------------- */

  variant = "soft", // soft | filled | outline
  size = "medium", // small | medium | large
  showIcon = true,
  iconOnly = false,
  rounded = true,

  /* ---------------------------------------------------------------------- */
  /* Children                                                               */
  /* ---------------------------------------------------------------------- */

  children,

  /* ---------------------------------------------------------------------- */
  /* Styling                                                                */
  /* ---------------------------------------------------------------------- */

  style,
  textStyle,

  /* ---------------------------------------------------------------------- */
  /* Accessibility                                                          */
  /* ---------------------------------------------------------------------- */

  accessibilityLabel,
}) => {
  const { colors } = theme;

  // Memoize badge configuration
  const config = useMemo(() => {
    const badge = BADGE_CONFIG[type] || BADGE_CONFIG.VERIFIED;
    const badgeColor = color || badge.color;
    const badgeIcon = icon || badge.icon;
    const badgeLabel = label || badge.label;
    const sizeConfig = SIZE_MAP[size] || SIZE_MAP.medium;

    return {
      badge,
      badgeColor,
      badgeIcon,
      badgeLabel,
      sizeConfig,
    };
  }, [type, label, icon, color, size]);

  const { badgeColor, badgeIcon, badgeLabel, sizeConfig } = config;

  // Memoize styles for performance
  const containerStyle = useMemo(() => {
    const baseStyle = {
      paddingVertical: sizeConfig.paddingVertical,
      paddingHorizontal: iconOnly
        ? sizeConfig.paddingVertical
        : sizeConfig.paddingHorizontal,
      borderRadius: rounded ? 999 : 8,
      borderWidth: 1,
      flexDirection: "row",
      alignItems: "center",
      alignSelf: "flex-start",
    };

    // Variant styles
    switch (variant) {
      case "filled":
        return {
          ...baseStyle,
          backgroundColor: badgeColor,
          borderColor: badgeColor,
        };

      case "outline":
        return {
          ...baseStyle,
          backgroundColor: "transparent",
          borderColor: badgeColor,
        };

      case "soft":
      default:
        return {
          ...baseStyle,
          backgroundColor: withOpacity(badgeColor, 0.12),
          borderColor: "transparent",
        };
    }
  }, [badgeColor, rounded, variant, sizeConfig, iconOnly]);

  // Text color based on variant
  const textColor = useMemo(() => {
    switch (variant) {
      case "filled":
        return "#FFFFFF";
      case "outline":
      case "soft":
      default:
        return badgeColor;
    }
  }, [variant, badgeColor]);

  // Render content
  const renderContent = useMemo(() => {
    // If children are provided, render them instead of configured content
    if (children) {
      return children;
    }

    // Icon only mode
    if (iconOnly) {
      return (
        <MaterialCommunityIcons
          name={badgeIcon}
          size={sizeConfig.iconSize}
          color={textColor}
        />
      );
    }

    // Full badge with icon and label
    return (
      <>
        {showIcon && (
          <MaterialCommunityIcons
            name={badgeIcon}
            size={sizeConfig.iconSize}
            color={textColor}
            style={styles.icon}
          />
        )}

        <Text
          numberOfLines={1}
          style={[
            styles.text,
            {
              color: textColor,
              fontSize: sizeConfig.fontSize,
            },
            textStyle,
          ]}
        >
          {badgeLabel}
        </Text>
      </>
    );
  }, [children, iconOnly, badgeIcon, badgeLabel, sizeConfig, textColor, showIcon, textStyle]);

  return (
    <View
      accessible
      accessibilityRole="text"
      accessibilityLabel={accessibilityLabel || badgeLabel}
      style={[
        styles.container,
        containerStyle,
        style,
      ]}
    >
      {renderContent}
    </View>
  );
});

SellerBadge.displayName = "SellerBadge";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const BADGE_TYPES = Object.keys(BADGE_CONFIG);

SellerBadge.propTypes = {
  /**
   * Badge type from SellerBadgeTypes
   */
  type: PropTypes.oneOf(BADGE_TYPES),

  /**
   * Custom label (overrides type label)
   */
  label: PropTypes.string,

  /**
   * Custom icon name (overrides type icon)
   */
  icon: PropTypes.string,

  /**
   * Custom color (overrides type color)
   */
  color: PropTypes.string,

  /**
   * Badge variant style
   */
  variant: PropTypes.oneOf(["soft", "filled", "outline"]),

  /**
   * Badge size
   */
  size: PropTypes.oneOf(["small", "medium", "large"]),

  /**
   * Whether to show the icon
   */
  showIcon: PropTypes.bool,

  /**
   * Icon-only mode (hides label)
   */
  iconOnly: PropTypes.bool,

  /**
   * Whether to round the corners
   */
  rounded: PropTypes.bool,

  /**
   * Optional custom content (overrides default badge content)
   */
  children: PropTypes.node,

  /**
   * Optional style overrides for the container
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),

  /**
   * Optional style overrides for the text
   */
  textStyle: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),

  /**
   * Accessibility label override
   */
  accessibilityLabel: PropTypes.string,
};

SellerBadge.defaultProps = {
  type: "VERIFIED",
  label: null,
  icon: null,
  color: null,
  variant: "soft",
  size: "medium",
  showIcon: true,
  iconOnly: false,
  rounded: true,
  children: null,
  style: null,
  textStyle: null,
  accessibilityLabel: null,
};

/* -------------------------------------------------------------------------- */
/* Exports                                                                    */
/* -------------------------------------------------------------------------- */

// Export badge types as frozen enum (backward compatibility)
export const SellerBadgeTypes = Object.freeze(
  BADGE_TYPES.reduce((acc, type) => {
    acc[type] = type;
    return acc;
  }, {})
);

// Export SELLER_BADGE for backward compatibility
export const SELLER_BADGE = Object.freeze(
  BADGE_TYPES.reduce((acc, type) => {
    acc[type] = type;
    return acc;
  }, {})
);

// Export BADGE_CONFIG for external use
export { BADGE_CONFIG };

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
  },

  icon: {
    marginRight: 4,
  },

  text: {
    fontWeight: "600",
    includeFontPadding: false,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default SellerBadge;