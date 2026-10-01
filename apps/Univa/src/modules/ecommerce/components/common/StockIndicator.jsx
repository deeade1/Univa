/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/StockIndicator.jsx       */
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

import { MaterialCommunityIcons }
  from "@expo/vector-icons";

import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Configuration                                                              */
/* -------------------------------------------------------------------------- */

const DEFAULT_LOW_STOCK = 20;

const DEFAULT_CRITICAL_STOCK = 5;

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const getStatus = (
  quantity,
  lowThreshold,
  criticalThreshold
) => {

  if (
    quantity <= 0
  ) {
    return "out";
  }

  if (
    quantity <=
    criticalThreshold
  ) {
    return "critical";
  }

  if (
    quantity <=
    lowThreshold
  ) {
    return "low";
  }

  return "available";

};

const getLabel = (
  status,
  quantity
) => {

  switch (status) {

    case "out":
      return "Out of Stock";

    case "critical":
      return `Only ${quantity} left`;

    case "low":
      return "Low Stock";

    default:
      return "In Stock";

  }

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const StockIndicator = memo(({

  quantity = 0,

  maxQuantity,

  lowStockThreshold =
    DEFAULT_LOW_STOCK,

  criticalStockThreshold =
    DEFAULT_CRITICAL_STOCK,

  showIcon = true,

  showProgress = false,

  showQuantity = false,

  variant = "soft",

  size = "medium",

  style,

  textStyle,

}) => {

  const { colors } = theme;

  const status =
    useMemo(
      () =>
        getStatus(
          quantity,
          lowStockThreshold,
          criticalStockThreshold
        ),
      [
        quantity,
        lowStockThreshold,
        criticalStockThreshold,
      ]
    );

  const label =
    useMemo(
      () =>
        getLabel(
          status,
          quantity
        ),
      [
        status,
        quantity,
      ]
    );

  const progress =
    useMemo(() => {

      if (
        !maxQuantity ||
        maxQuantity <= 0
      ) {
        return 0;
      }

      return Math.min(
        quantity /
        maxQuantity,
        1
      );

    }, [
      quantity,
      maxQuantity,
    ]);

  const palette =
    useMemo(() => {

      switch (status) {

        case "critical":
          return {
            color:
              colors.error,
          };

        case "low":
          return {
            color:
              colors.warning,
          };

        case "out":
          return {
            color:
              colors.error,
          };

        default:
          return {
            color:
              colors.success,
          };

      }

    }, [
      status,
      colors,
    ]);
      /* ---------------------------------------------------------------------- */
  /* Variant Styles                                                         */
  /* ---------------------------------------------------------------------- */

  const containerStyle = [

    styles.container,

    styles[size],

    variant === "filled" && {

      backgroundColor:
        palette.color,

      borderColor:
        palette.color,

    },

    variant === "outline" && {

      backgroundColor:
        "transparent",

      borderColor:
        palette.color,

    },

    variant === "soft" && {

      backgroundColor:
        `${palette.color}20`,

      borderColor:
        "transparent",

    },

    style,

  ];

  const labelStyle = [

    styles.label,

    styles[
      `${size}Text`
    ],

    {

      color:
        variant ===
        "filled"
          ? "#FFFFFF"
          : palette.color,

    },

    textStyle,

  ];

  const iconSize =

    size === "small"
      ? 12
      : size === "large"
      ? 18
      : 15;

  const iconName =

    status === "available"
      ? "check-circle"

    : status === "low"
      ? "alert-circle"

    : status === "critical"
      ? "alert"

    : "close-circle";

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (

    <View>

      <View
        style={containerStyle}
      >

        {showIcon && (

          <MaterialCommunityIcons
            name={iconName}
            size={iconSize}
            color={
              variant ===
              "filled"
                ? "#FFFFFF"
                : palette.color
            }
            style={
              styles.icon
            }
          />

        )}

        <Text
          numberOfLines={1}
          style={labelStyle}
        >
          {label}
        </Text>

        {showQuantity &&
          quantity > 0 && (

          <Text
            style={[
              labelStyle,
              styles.quantity,
            ]}
          >
            ({quantity})
          </Text>

        )}

      </View>

      {showProgress &&
        maxQuantity >
        0 && (

        <View
          style={[
                styles.progressTrack,
                {
                backgroundColor:
                    colors.border,
                },
          ]}
        >

          <View
            style={[

              styles.progressFill,

              {

                width:
                  `${progress * 100}%`,

                backgroundColor:
                  palette.color,

              },

            ]}
          />

        </View>

      )}

    </View>

  );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

StockIndicator.displayName =
  "StockIndicator";

/* -------------------------------------------------------------------------- */
/* Prop Types                                                                 */
/* -------------------------------------------------------------------------- */

StockIndicator.propTypes = {

  quantity:
    PropTypes.number,

  maxQuantity:
    PropTypes.number,

  lowStockThreshold:
    PropTypes.number,

  criticalStockThreshold:
    PropTypes.number,

  showIcon:
    PropTypes.bool,

  showProgress:
    PropTypes.bool,

  showQuantity:
    PropTypes.bool,

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

    container: {

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
        "600",

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

    quantity: {

      marginLeft:
        4,

      opacity:
        0.85,

    },

    icon: {

      marginRight:
        4,

    },

    /* ------------------------------------------------------------------ */
    /* Progress                                                           */
    /* ------------------------------------------------------------------ */

    progressTrack: {

      marginTop:
        6,

      height:
        4,

      borderRadius:
        999,

      overflow:
        "hidden",

      backgroundColor:
        "#E5E7EB",

    },

    progressFill: {

      height:
        "100%",

      borderRadius:
        999,

    },

  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
StockIndicator;