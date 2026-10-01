/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/StockBadge.jsx          */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const StockBadge = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Stock                                                                   */
    /* ---------------------------------------------------------------------- */

    inStock = true,

    quantity,

    lowStockThreshold = 5,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                 */
    /* ---------------------------------------------------------------------- */

    showIcon = true,

    showQuantity = false,

    size = "md", // xs | sm | md | lg

    variant = "filled", // filled | outlined | subtle

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const status =
      useMemo(() => {
        if (!inStock) {
          return {
            label: "Out of Stock",
            icon: "close-circle",
            color: colors.error,
          };
        }

        if (
          quantity != null &&
          quantity <=
            lowStockThreshold
        ) {
          return {
            label: showQuantity
              ? `${quantity} Left`
              : "Low Stock",

            icon: "alert-circle",

            color:
              colors.warning ??
              "#F59E0B",
          };
        }

        return {
          label: showQuantity &&
            quantity != null
            ? `${quantity} In Stock`
            : "In Stock",

          icon:
            "check-circle",

          color:
            colors.success ??
            "#10B981",
        };
      }, [
        inStock,
        quantity,
        lowStockThreshold,
        showQuantity,
        colors,
      ]);

    /* ---------------------------------------------------------------------- */

    const metrics =
      useMemo(() => {
        switch (size) {
          case "xs":
            return {
              font: 10,
              icon: 12,
              px: 6,
              py: 2,
            };

          case "sm":
            return {
              font: 11,
              icon: 14,
              px: 8,
              py: 3,
            };

          case "lg":
            return {
              font: 14,
              icon: 18,
              px: 12,
              py: 6,
            };

          default:
            return {
              font: 12,
              icon: 16,
              px: 10,
              py: 4,
            };
        }
      }, [size]);

    /* ---------------------------------------------------------------------- */

    const backgroundColor =
      variant ===
      "filled"
        ? status.color
        : variant ===
          "subtle"
        ? `${status.color}15`
        : "transparent";

    const textColor =
      variant ===
      "filled"
        ? "#FFF"
        : status.color;

    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,

          {
            backgroundColor,

            borderColor:
              status.color,

            borderWidth:
              variant ===
              "outlined"
                ? 1
                : 0,

            paddingHorizontal:
              metrics.px,

            paddingVertical:
              metrics.py,
          },

          style,
        ]}
      >
        {showIcon && (
          <MaterialCommunityIcons
            name={status.icon}
            size={
              metrics.icon
            }
            color={textColor}
          />
        )}

        <Text
          numberOfLines={1}
          style={[
            styles.label,

            {
              color:
                textColor,

              fontSize:
                metrics.font,

              marginLeft:
                showIcon
                  ? 4
                  : 0,
            },
          ]}
        >
          {status.label}
        </Text>
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

StockBadge.displayName =
  "StockBadge";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection:
        "row",

      alignItems:
        "center",

      alignSelf:
        "flex-start",

      borderRadius: 999,
    },

    label: {
      fontWeight: "600",
    },
  });

/* -------------------------------------------------------------------------- */

export default StockBadge;