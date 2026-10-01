/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/AvailabilityBadge.jsx    */
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

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Status Configuration                                                       */
/* -------------------------------------------------------------------------- */

const STATUS = {

  AVAILABLE: "available",

  PREORDER: "preorder",

  BACKORDER: "backorder",

  COMING_SOON: "comingSoon",

  OUT_OF_STOCK: "outOfStock",

  DISCONTINUED: "discontinued",

};

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const getStatusConfig = (
  status,
  colors
) => {

  switch (status) {

    case STATUS.PREORDER:
      return {

        label:
          "Pre-order",

        icon:
          "clock-outline",

        color:
          colors.info,

      };

    case STATUS.BACKORDER:
      return {

        label:
          "Backorder",

        icon:
          "truck-fast",

        color:
          colors.warning,

      };

    case STATUS.COMING_SOON:
      return {

        label:
          "Coming Soon",

        icon:
          "rocket-launch",

        color:
          colors.primary,

      };

    case STATUS.OUT_OF_STOCK:
      return {

        label:
          "Out of Stock",

        icon:
          "close-circle",

        color:
          colors.error,

      };

    case STATUS.DISCONTINUED:
      return {

        label:
          "Discontinued",

        icon:
          "cancel",

        color:
          colors.textSecondary ??
          colors.text,

      };

    case STATUS.AVAILABLE:
    default:
      return {

        label:
          "Available",

        icon:
          "check-circle",

        color:
          colors.success,

      };

  }

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const AvailabilityBadge = memo(({

  status =
    STATUS.AVAILABLE,

  variant =
    "soft",

  size =
    "medium",

  showIcon = true,

  style,

  textStyle,

}) => {

  const { colors } = theme;

  const config =
    useMemo(
      () =>
        getStatusConfig(
          status,
          colors
        ),
      [
        status,
        colors,
      ]
    );

  const containerStyle = [

    styles.container,

    styles[size],

    variant ===
      "filled" && {

      backgroundColor:
        config.color,

      borderColor:
        config.color,

    },

    variant ===
      "outline" && {

      borderColor:
        config.color,

      backgroundColor:
        "transparent",

    },

    variant ===
      "soft" && {

      backgroundColor:
        `${config.color}20`,

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
          : config.color,

    },

    textStyle,

  ];

  const iconSize =

    size === "small"
      ? 12
      : size === "large"
      ? 18
      : 15;

  return (

    <View
      style={
        containerStyle
      }
    >

      {showIcon && (

        <MaterialCommunityIcons
          name={
            config.icon
          }
          size={
            iconSize
          }
          color={
            variant ===
            "filled"
              ? "#FFFFFF"
              : config.color
          }
          style={
            styles.icon
          }
        />

      )}

      <Text
        numberOfLines={1}
        style={
          labelStyle
        }
      >
        {config.label}
      </Text>

    </View>

  );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

AvailabilityBadge.displayName =
  "AvailabilityBadge";

/* -------------------------------------------------------------------------- */
/* Export Status Constants                                                    */
/* -------------------------------------------------------------------------- */

export {
  STATUS as AVAILABILITY_STATUS,
};

/* -------------------------------------------------------------------------- */
/* Prop Types                                                                 */
/* -------------------------------------------------------------------------- */

AvailabilityBadge.propTypes = {

  status:
    PropTypes.oneOf([
      STATUS.AVAILABLE,
      STATUS.PREORDER,
      STATUS.BACKORDER,
      STATUS.COMING_SOON,
      STATUS.OUT_OF_STOCK,
      STATUS.DISCONTINUED,
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

    icon: {

      marginRight:
        4,

    },

  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
AvailabilityBadge;