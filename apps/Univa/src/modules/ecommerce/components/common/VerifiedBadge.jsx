/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/VerifiedBadge.jsx        */
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

import PropTypes
  from "prop-types";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Verification Types                                                         */
/* -------------------------------------------------------------------------- */

const VERIFIED_TYPE = {

  VERIFIED:
    "verified",

  OFFICIAL:
    "official",

  CERTIFIED:
    "certified",

  TRUSTED:
    "trusted",

  AUTHENTIC:
    "authentic",

};

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const getConfig = (
  type,
  colors
) => {

  switch (type) {

    case VERIFIED_TYPE.OFFICIAL:

      return {

        label:
          "Official",

        icon:
          "shield-crown",

        color:
          colors.primary,

      };

    case VERIFIED_TYPE.CERTIFIED:

      return {

        label:
          "Certified",

        icon:
          "certificate",

        color:
          colors.warning,

      };

    case VERIFIED_TYPE.TRUSTED:

      return {

        label:
          "Trusted",

        icon:
          "shield-check",

        color:
          colors.success,

      };

    case VERIFIED_TYPE.AUTHENTIC:

      return {

        label:
          "Authentic",

        icon:
          "check-decagram",

        color:
          colors.info,

      };

    case VERIFIED_TYPE.VERIFIED:
    default:

      return {

        label:
          "Verified",

        icon:
          "check-decagram",

        color:
          colors.success,

      };

  }

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const VerifiedBadge =
memo(({

  type =
    VERIFIED_TYPE.VERIFIED,

  variant =
    "soft",

  size =
    "medium",

  showIcon =
    true,

  label,

  style,

  textStyle,

}) => {

  const {
    colors,
  } = theme;

  const config =
    useMemo(
      () =>
        getConfig(
          type,
          colors
        ),
      [
        type,
        colors,
      ]
    );

  const badgeLabel =
    label ??
    config.label;

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

      backgroundColor:
        "transparent",

      borderColor:
        config.color,

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
        {badgeLabel}
      </Text>

    </View>

  );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

VerifiedBadge.displayName =
  "VerifiedBadge";

/* -------------------------------------------------------------------------- */
/* Export Types                                                               */
/* -------------------------------------------------------------------------- */

export {
  VERIFIED_TYPE,
};

/* -------------------------------------------------------------------------- */
/* Prop Types                                                                 */
/* -------------------------------------------------------------------------- */

VerifiedBadge.propTypes = {

  type:
    PropTypes.oneOf([
      VERIFIED_TYPE.VERIFIED,
      VERIFIED_TYPE.OFFICIAL,
      VERIFIED_TYPE.CERTIFIED,
      VERIFIED_TYPE.TRUSTED,
      VERIFIED_TYPE.AUTHENTIC,
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

  label:
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

  /* ---------------------------------------------------------------------- */
  /* Sizes                                                                   */
  /* ---------------------------------------------------------------------- */

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

  /* ---------------------------------------------------------------------- */
  /* Typography                                                              */
  /* ---------------------------------------------------------------------- */

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
VerifiedBadge;