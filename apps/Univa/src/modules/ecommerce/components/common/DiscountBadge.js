/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/DiscountBadge.jsx       */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import {
  StyleSheet,
  Text,
  View,
} from "react-native";

import PropTypes from "prop-types";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const formatDiscount = (
  value,
  type
) => {

  if (
    value == null ||
    value <= 0
  ) {
    return null;
  }

  switch (type) {

    case "amount":
      return `Save ₦${Number(
        value
      ).toLocaleString()}`;

    case "fixed":
      return `-₦${Number(
        value
      ).toLocaleString()}`;

    case "percentage":
    default:
      return `-${value}%`;

  }

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const DiscountBadge = memo(({

  value,

  type = "percentage",

  variant = "filled",

  showIcon = true,

  icon = "sale",

  size = "medium",

  style,

  textStyle,

}) => {

  const { colors } = theme();

  const label =
    useMemo(
      () =>
        formatDiscount(
          value,
          type
        ),
      [
        value,
        type,
      ]
    );

  if (!label) {
    return null;
  }

  const badgeStyles = [
  styles.badge,
  styles[size],

  variant === "filled" && {
    backgroundColor: colors.error,
    borderColor: colors.error,
  },

  variant === "outline" && {
    borderColor: colors.error,
    backgroundColor: "transparent",
  },

  variant === "soft" && {
    backgroundColor: `${colors.error}20`,
    borderColor: "transparent",
  },

  style,
];

  const labelStyles = [
    styles.label,
    styles[
      `${size}Text`
    ],
    {
      color:
        variant ===
        "filled"
          ? "#FFFFFF"
          : colors.error,
    },
    textStyle,
  ];

  return (
    <View
      style={
        badgeStyles
      }
    >
      {showIcon && (
        <MaterialCommunityIcons
          name={icon}
          size={
            size === "small"
              ? 12
              : size === "large"
              ? 18
              : 14
          }
          color={
            variant ===
            "filled"
              ? "#FFFFFF"
              : colors.error
          }
          style={
            styles.icon
          }
        />
      )}

      <Text
        numberOfLines={1}
        style={
          labelStyles
        }
      >
        {label}
      </Text>
    </View>
  );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

DiscountBadge.displayName =
  "DiscountBadge";

/* -------------------------------------------------------------------------- */
/* Prop Types                                                                 */
/* -------------------------------------------------------------------------- */

DiscountBadge.propTypes = {

  value:
    PropTypes.number
      .isRequired,

  type:
    PropTypes.oneOf([
      "percentage",
      "fixed",
      "amount",
    ]),

  variant:
    PropTypes.oneOf([
      "filled",
      "outline",
      "soft",
    ]),

  size:
    PropTypes.oneOf([
      "small",
      "medium",
      "large",
    ]),

  showIcon:
    PropTypes.bool,

  icon:
    PropTypes.string,

  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),

  textStyle:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),

};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({

    badge: {

      flexDirection:
        "row",

      alignItems:
        "center",

      alignSelf:
        "flex-start",

      borderRadius:
        999,

      borderWidth:
        1,

    },

    /* ------------------------------------------------------------------ */
    /* Variants                                                           */
    /* ------------------------------------------------------------------ */

    filled: {

      borderColor:
        "transparent",

    },

    outline: {

      backgroundColor:
        "transparent",

    },

    soft: {

      backgroundColor:
        "rgba(239,68,68,0.12)",

      borderColor:
        "transparent",

    },

    /* ------------------------------------------------------------------ */
    /* Sizes                                                              */
    /* ------------------------------------------------------------------ */

    small: {

      paddingHorizontal:
        8,

      paddingVertical:
        3,

    },

    medium: {

      paddingHorizontal:
        10,

      paddingVertical:
        5,

    },

    large: {

      paddingHorizontal:
        12,

      paddingVertical:
        7,

    },

    /* ------------------------------------------------------------------ */
    /* Typography                                                         */
    /* ------------------------------------------------------------------ */

    label: {

      fontWeight:
        "700",

      includeFontPadding:
        false,

    },

    smallText: {

      fontSize:
        11,

    },

    mediumText: {

      fontSize:
        13,

    },

    largeText: {

      fontSize:
        15,

    },

    icon: {

      marginRight:
        4,

    },

  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
DiscountBadge;