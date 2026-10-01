/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/products/ProductBadge.jsx      */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";

import {
  Text,
  View,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Preset Badge Types                                                         */
/* -------------------------------------------------------------------------- */

const BADGE_PRESETS = {
  featured: {
    label: "Featured",
    color: "#F59E0B",
    icon: "star",
  },

  new: {
    label: "New",
    color: "#22C55E",
    icon: "sparkles",
  },

  sale: {
    label: "Sale",
    color: "#EF4444",
    icon: "sale",
  },

  hot: {
    label: "Hot",
    color: "#DC2626",
    icon: "fire",
  },

  trending: {
    label: "Trending",
    color: "#8B5CF6",
    icon: "trending-up",
  },

  limited: {
    label: "Limited",
    color: "#F97316",
    icon: "clock-outline",
  },

  bestSeller: {
    label: "Best Seller",
    color: "#2563EB",
    icon: "trophy",
  },

  outOfStock: {
    label: "Out of Stock",
    color: "#6B7280",
    icon: "close-circle",
  },

  preorder: {
    label: "Pre-order",
    color: "#14B8A6",
    icon: "truck-fast",
  },
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductBadge = memo(
  ({
    type,

    label,

    color,

    icon,

    size = "medium",

    outlined = false,

    style,

    textStyle,
  }) => {
    const { colors } = theme;


    const preset =
      BADGE_PRESETS[type] || {};

    const badgeColor =
      color ||
      preset.color ||
      colors.primary;

    const badgeLabel =
      label ||
      preset.label ||
      "";

    const badgeIcon =
      icon ||
      preset.icon;

    const small =
      size === "small";

    const large =
      size === "large";

    return (
      <View
        style={[
          styles.container,

          {
            backgroundColor:
              outlined
                ? "transparent"
                : badgeColor,

            borderColor:
              badgeColor,

            borderWidth: outlined
              ? 1
              : 0,

            paddingHorizontal:
              small
                ? 6
                : large
                ? 12
                : 10,

            paddingVertical:
              small
                ? 3
                : large
                ? 6
                : 5,
          },

          style,
        ]}
      >
        {badgeIcon && (
          <MaterialCommunityIcons
            name={badgeIcon}
            size={
              small
                ? 11
                : large
                ? 16
                : 13
            }
            color={
              outlined
                ? badgeColor
                : "#FFFFFF"
            }
            style={{
              marginRight: 4,
            }}
          />
        )}

        <Text
          style={[
            styles.label,

            {
              color: outlined
                ? badgeColor
                : "#FFFFFF",

              fontSize: small
                ? 10
                : large
                ? 14
                : 12,
            },

            textStyle,
          ]}
          numberOfLines={1}
        >
          {badgeLabel}
        </Text>
      </View>
    );
  }
);

ProductBadge.displayName =
  "ProductBadge";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",

    borderRadius: 999,

    marginBottom: 6,
  },

  label: {
    fontWeight: "700",
  },
});

export default ProductBadge;