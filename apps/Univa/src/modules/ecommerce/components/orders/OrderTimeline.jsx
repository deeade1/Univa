/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/orders/OrderTimeline.jsx       */
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

import { MaterialCommunityIcons } from "@expo/vector-icons";

import {
  colors,
  spacing,
  typography,
  radius,
} from "../../../theme";

import OrderStatusBadge, {
  getStatusConfig,
  STATUS_CONFIG,
} from "./OrderStatusBadge";

/* -------------------------------------------------------------------------- */
/* Default Timeline                                                           */
/* -------------------------------------------------------------------------- */

const DEFAULT_STEPS = [
  {
    key: "PENDING",
    title: "Order Placed",
    icon: "cart-check",
  },
  {
    key: "CONFIRMED",
    title: "Confirmed",
    icon: "check-decagram-outline",
  },
  {
    key: "PROCESSING",
    title: "Processing",
    icon: "package-variant-closed",
  },
  {
    key: "SHIPPED",
    title: "Shipped",
    icon: "truck-delivery-outline",
  },
  {
    key: "OUT_FOR_DELIVERY",
    title: "Out for Delivery",
    icon: "truck-fast-outline",
  },
  {
    key: "DELIVERED",
    title: "Delivered",
    icon: "check-circle-outline",
  },
  {
    key: "CANCELLED",
    title: "Cancelled",
    icon: "close-circle-outline",
  },
  {
    key: "REFUNDED",
    title: "Refunded",
    icon: "cash-refund",
  },
  {
    key: "FAILED",
    title: "Failed",
    icon: "alert-circle-outline",
  },
  {
    key: "RETURNED",
    title: "Returned",
    icon: "archive-refresh-outline",
  },
];

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const OrderTimeline = memo(
  ({
    currentStatus = "PENDING",
    steps = DEFAULT_STEPS,
    events = [],
    showHeader = true,
    showBadge = true,
    style,
  }) => {
    // Get theme-aware status config
    const statusConfig = useMemo(() => getStatusConfig(colors), []);

    // Normalize status to uppercase for case-insensitive matching
    const normalizedStatus = currentStatus?.toUpperCase();

    const currentIndex = steps.findIndex(
      (step) => step.key === normalizedStatus
    );

    // Safe index: if status not found, default to 0
    const safeCurrentIndex = currentIndex === -1 ? 0 : currentIndex;

    // Create event map for O(1) lookup
    const eventMap = useMemo(
      () =>
        Object.fromEntries(
          events.map((event) => [event.status?.toUpperCase(), event])
        ),
      [events]
    );

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
          style,
        ]}
      >
        {/* ------------------------------------------------------------ */}
        {/* Header                                                       */}
        {/* ------------------------------------------------------------ */}

        {showHeader && (
          <View style={styles.header}>
            <Text
              style={[
                styles.title,
                {
                  color: colors.text,
                },
              ]}
            >
              Order Timeline
            </Text>

            {showBadge && (
              <OrderStatusBadge status={normalizedStatus} />
            )}
          </View>
        )}

        {/* ------------------------------------------------------------ */}
        {/* Timeline                                                     */}
        {/* ------------------------------------------------------------ */}

        {steps.map((step, index) => {
          const completed = index < safeCurrentIndex;
          const active = index === safeCurrentIndex;

          const event = eventMap[step.key];

          // Get color from status config or use theme colors
          const configColor = statusConfig[step.key]?.color;
          const color =
            completed || active
              ? configColor || colors.primary
              : colors.border;

          return (
            <View key={step.key} style={styles.timelineRow}>
              {/* Left */}
              <View style={styles.left}>
                <View
                  style={[
                    styles.circle,
                    {
                      backgroundColor: completed
                        ? color
                        : active
                        ? `${color}20`
                        : colors.background,
                      borderColor: color,
                    },
                  ]}
                >
                  <MaterialCommunityIcons
                    name={completed ? "check" : step.icon}
                    size={18}
                    color={completed ? colors.white : color}
                  />
                </View>

                {index < steps.length - 1 && (
                  <View
                    style={[
                      styles.line,
                      {
                        backgroundColor: completed ? color : colors.border,
                      },
                    ]}
                  />
                )}
              </View>

              {/* Right */}
              <View style={styles.content}>
                <Text
                  style={[
                    styles.stepTitle,
                    {
                      color: colors.text,
                    },
                  ]}
                >
                  {step.title}
                </Text>

                {event?.date && (
                  <Text
                    style={[
                      styles.date,
                      {
                        color: colors.textSecondary,
                      },
                    ]}
                  >
                    {event.date}
                  </Text>
                )}

                {event?.description && (
                  <Text
                    style={[
                      styles.description,
                      {
                        color: colors.textSecondary,
                      },
                    ]}
                  >
                    {event.description}
                  </Text>
                )}
              </View>
            </View>
          );
        })}
      </View>
    );
  }
);

OrderTimeline.displayName = "OrderTimeline";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

OrderTimeline.propTypes = {
  /**
   * Current order status
   */
  currentStatus: PropTypes.string,

  /**
   * Timeline steps configuration
   */
  steps: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string,
      title: PropTypes.string,
      icon: PropTypes.string,
    })
  ),

  /**
   * Events for each step
   */
  events: PropTypes.arrayOf(
    PropTypes.shape({
      status: PropTypes.string,
      date: PropTypes.string,
      description: PropTypes.string,
    })
  ),

  /**
   * Show header section
   */
  showHeader: PropTypes.bool,

  /**
   * Show status badge in header
   */
  showBadge: PropTypes.bool,

  /**
   * Additional styles
   */
  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

OrderTimeline.defaultProps = {
  currentStatus: "PENDING",
  steps: DEFAULT_STEPS,
  events: [],
  showHeader: true,
  showBadge: true,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.lg,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.lg,
  },

  title: {
    fontSize: typography.fontSize.xl,
    fontWeight: typography.fontWeight.bold,
  },

  timelineRow: {
    flexDirection: "row",
    alignItems: "flex-start",
  },

  left: {
    width: 42,
    alignItems: "center",
  },

  circle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 2,
    justifyContent: "center",
    alignItems: "center",
  },

  line: {
    width: 2,
    flex: 1,
    minHeight: 48,
  },

  content: {
    flex: 1,
    paddingBottom: spacing.md,
    paddingLeft: spacing.sm,
  },

  stepTitle: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
  },

  date: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
  },

  description: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.md,
    lineHeight: 20,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default OrderTimeline;