/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ShippingBadge.jsx        */
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
/* Shipping Types                                                             */
/* -------------------------------------------------------------------------- */

const SHIPPING = {

  FREE: "free",

  EXPRESS: "express",

  SAME_DAY: "sameDay",

  NEXT_DAY: "nextDay",

  PICKUP: "pickup",

  INTERNATIONAL: "international",

  COD: "cashOnDelivery",

};

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const getShippingConfig = (
  type,
  colors
) => {

  switch (type) {

    case SHIPPING.EXPRESS:
      return {

        label:
          "Express Delivery",

        icon:
          "truck-fast",

        color:
          colors.warning,

      };

    case SHIPPING.SAME_DAY:
      return {

        label:
          "Same-Day Delivery",

        icon:
          "clock-fast",

        color:
          colors.success,

      };

    case SHIPPING.NEXT_DAY:
      return {

        label:
          "Next-Day Delivery",

        icon:
          "calendar-clock",

        color:
          colors.primary,

      };

    case SHIPPING.PICKUP:
      return {

        label:
          "Pickup Available",

        icon:
          "store",

        color:
          colors.info,

      };

    case SHIPPING.INTERNATIONAL:
      return {

        label:
          "International Shipping",

        icon:
          "earth",

        color:
          colors.secondary ??
          colors.primary,

      };

    case SHIPPING.COD:
      return {

        label:
          "Cash on Delivery",

        icon:
          "cash",

        color:
          colors.success,

      };

    case SHIPPING.FREE:
    default:
      return {

        label:
          "Free Shipping",

        icon:
          "truck-check",

        color:
          colors.success,

      };

  }

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ShippingBadge = memo(({

  type =
    SHIPPING.FREE,

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
        getShippingConfig(
          type,
          colors
        ),
      [
        type,
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

ShippingBadge.displayName =
  "ShippingBadge";

/* -------------------------------------------------------------------------- */
/* Export Shipping Types                                                      */
/* -------------------------------------------------------------------------- */

export {
  SHIPPING as SHIPPING_TYPE,
};

/* -------------------------------------------------------------------------- */
/* Prop Types                                                                 */
/* -------------------------------------------------------------------------- */

ShippingBadge.propTypes = {

  type:
    PropTypes.oneOf([
      SHIPPING.FREE,
      SHIPPING.EXPRESS,
      SHIPPING.SAME_DAY,
      SHIPPING.NEXT_DAY,
      SHIPPING.PICKUP,
      SHIPPING.INTERNATIONAL,
      SHIPPING.COD,
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
ShippingBadge;