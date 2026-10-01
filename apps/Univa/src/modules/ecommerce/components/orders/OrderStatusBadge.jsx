/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/orders/OrderStatusBadge.jsx    */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import {
  colors,
} from '../../../theme';

/* -------------------------------------------------------------------------- */
/* Status Configuration                                                       */
/* -------------------------------------------------------------------------- */

export const getStatusConfig = (themeColors) => ({
  PENDING: {
    label: "Pending",
    icon: "clock-outline",
    color: themeColors.warning || "#F59E0B",
  },

  CONFIRMED: {
    label: "Confirmed",
    icon: "check-decagram-outline",
    color: themeColors.primary || "#3B82F6",
  },

  PROCESSING: {
    label: "Processing",
    icon: "package-variant-closed",
    color: themeColors.info || "#6366F1",
  },

  PACKED: {
    label: "Packed",
    icon: "package-variant",
    color: themeColors.purple || "#8B5CF6",
  },

  SHIPPED: {
    label: "Shipped",
    icon: "truck-delivery-outline",
    color: themeColors.info || "#0EA5E9",
  },

  OUT_FOR_DELIVERY: {
    label: "Out for Delivery",
    icon: "truck-fast-outline",
    color: themeColors.cyan || "#06B6D4",
  },

  DELIVERED: {
    label: "Delivered",
    icon: "check-circle-outline",
    color: themeColors.success || "#22C55E",
  },

  COMPLETED: {
    label: "Completed",
    icon: "check-all",
    color: themeColors.success || "#16A34A",
  },

  RETURN_REQUESTED: {
    label: "Return Requested",
    icon: "backup-restore",
    color: themeColors.warning || "#F97316",
  },

  RETURNED: {
    label: "Returned",
    icon: "archive-refresh-outline",
    color: themeColors.purple || "#8B5CF6",
  },

  REFUNDED: {
    label: "Refunded",
    icon: "cash-refund",
    color: themeColors.teal || "#14B8A6",
  },

  FAILED: {
    label: "Failed",
    icon: "alert-circle-outline",
    color: themeColors.error || "#EF4444",
  },

  CANCELLED: {
    label: "Cancelled",
    icon: "close-circle-outline",
    color: themeColors.error || "#DC2626",
  },

  // Additional statuses used by OrderActions
  UNCONFIRMED: {
    label: "Unconfirmed",
    icon: "clock-alert-outline",
    color: themeColors.warning || "#F59E0B",
  },

  UNFULFILLED: {
    label: "Unfulfilled",
    icon: "package-remove-outline",
    color: themeColors.warning || "#F97316",
  },
});

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const OrderStatusBadge = memo(
  ({
    status = "PENDING",
    label,
    size = "medium",
    outlined = false,
    rounded = true,
    style,
    textStyle,
    iconSize,
  }) => {
    // Get status config with theme colors
    const STATUS_CONFIG = getStatusConfig(colors);

    // Normalize status to uppercase for case-insensitive matching
    const normalizedStatus = status?.toUpperCase();

    const config =
      STATUS_CONFIG[normalizedStatus] ??
      STATUS_CONFIG.PENDING;

    const isSmall = size === "small";
    const isLarge = size === "large";

    const iconSizeValue = iconSize ??
      (isSmall ? 14 : isLarge ? 20 : 16);

    const displayLabel = label ?? config.label;

    return (
      <View
        accessibilityRole="text"
        accessibilityLabel={`${displayLabel} order status`}
        style={[
          styles.container,
          rounded && styles.rounded,
          outlined
            ? {
                backgroundColor: "transparent",
                borderWidth: 1,
                borderColor: config.color,
              }
            : {
                backgroundColor: `${config.color}18`,
              },
          isSmall && styles.small,
          isLarge && styles.large,
          style,
        ]}
      >
        <MaterialCommunityIcons
          name={config.icon}
          size={iconSizeValue}
          color={config.color}
        />

        <Text
          style={[
            styles.text,
            {
              color: config.color,
            },
            isSmall && styles.smallText,
            isLarge && styles.largeText,
            textStyle,
          ]}
        >
          {displayLabel}
        </Text>
      </View>
    );
  }
);

OrderStatusBadge.displayName = "OrderStatusBadge";

/* -------------------------------------------------------------------------- */
/* Export Status Config                                                       */
/* -------------------------------------------------------------------------- */

// Pre-configured status config for external use (filters, timelines, etc.)
export const STATUS_CONFIG = getStatusConfig(colors);

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

OrderStatusBadge.propTypes = {
  /**
   * Status key from STATUS_CONFIG.
   * Examples: PENDING, CONFIRMED, SHIPPED, DELIVERED, etc.
   */
  status: PropTypes.string,

  /**
   * Custom label override.
   */
  label: PropTypes.string,

  /**
   * Badge size variant.
   */
  size: PropTypes.oneOf(['small', 'medium', 'large']),

  /**
   * Whether to use outlined style instead of filled.
   */
  outlined: PropTypes.bool,

  /**
   * Whether to round the corners.
   */
  rounded: PropTypes.bool,

  /**
   * Custom container style override.
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),

  /**
   * Custom text style override.
   */
  textStyle: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),

  /**
   * Custom icon size.
   */
  iconSize: PropTypes.number,
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

OrderStatusBadge.defaultProps = {
  status: 'PENDING',
  label: undefined,
  size: 'medium',
  outlined: false,
  rounded: true,
  style: undefined,
  textStyle: undefined,
  iconSize: undefined,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 6,
  },

  rounded: {
    borderRadius: 999,
  },

  small: {
    paddingHorizontal: 8,
    paddingVertical: 4,
  },

  large: {
    paddingHorizontal: 14,
    paddingVertical: 8,
  },

  text: {
    marginLeft: 6,
    fontSize: 12,
    fontWeight: "700",
  },

  smallText: {
    fontSize: 11,
  },

  largeText: {
    fontSize: 14,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default OrderStatusBadge;