/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/DiscountBadge.jsx       */
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


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const DiscountBadge = memo(
  ({
    percentage,

    amount,

    label,

    size = "md", // xs | sm | md | lg

    variant = "filled", // filled | outlined | subtle

    color,

    textColor,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const badgeLabel =
      useMemo(() => {
        if (label) {
          return label;
        }

        if (
          percentage != null
        ) {
          return `-${percentage}%`;
        }

        if (
          amount != null
        ) {
          return `Save ${amount}`;
        }

        return "Sale";
      }, [
        label,
        percentage,
        amount,
      ]);

    /* ---------------------------------------------------------------------- */

    const metrics =
      useMemo(() => {
        switch (size) {
          case "xs":
            return {
              fontSize: 10,
              horizontal: 6,
              vertical: 2,
            };

          case "sm":
            return {
              fontSize: 11,
              horizontal: 8,
              vertical: 3,
            };

          case "lg":
            return {
              fontSize: 14,
              horizontal: 12,
              vertical: 6,
            };

          default:
            return {
              fontSize: 12,
              horizontal: 10,
              vertical: 4,
            };
        }
      }, [size]);

    /* ---------------------------------------------------------------------- */

    const backgroundColor =
      variant === "filled"
        ? color ??
          colors.error
        : variant ===
          "subtle"
        ? `${color ?? colors.error}15`
        : "transparent";

    const borderColor =
      color ??
      colors.error;

    const foreground =
      variant === "filled"
        ? textColor ??
          "#FFF"
        : color ??
          colors.error;

    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,

          {
            backgroundColor,

            borderColor,

            paddingHorizontal:
              metrics.horizontal,

            paddingVertical:
              metrics.vertical,

            borderWidth:
              variant ===
              "outlined"
                ? 1
                : 0,
          },

          style,
        ]}
      >
        <Text
          numberOfLines={1}
          style={[
            styles.text,

            {
              color:
                foreground,

              fontSize:
                metrics.fontSize,
            },
          ]}
        >
          {badgeLabel}
        </Text>
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

DiscountBadge.displayName =
  "DiscountBadge";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      borderRadius: 999,

      alignSelf:
        "flex-start",

      justifyContent:
        "center",

      alignItems:
        "center",
    },

    text: {
      fontWeight: "700",

      letterSpacing:
        0.25,
    },
  });

/* -------------------------------------------------------------------------- */

export default DiscountBadge;