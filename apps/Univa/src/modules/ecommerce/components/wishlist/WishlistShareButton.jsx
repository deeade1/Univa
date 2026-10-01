/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistShareButton.jsx */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  Pressable,
  Text,
  StyleSheet,
  ActivityIndicator,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WishlistShareButton = memo(
  ({
    label = "Share Wishlist",

    icon = "share-variant",

    variant = "primary",

    size = "medium",

    fullWidth = false,

    disabled = false,

    loading = false,

    onPress,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Handler                                                                */
    /* ---------------------------------------------------------------------- */

    const handlePress =
      useCallback(() => {
        if (!loading && !disabled) {
          onPress?.();
        }
      }, [
        loading,
        disabled,
        onPress,
      ]);

    /* ---------------------------------------------------------------------- */
    /* Derived Styles                                                         */
    /* ---------------------------------------------------------------------- */

    const buttonStyle = [
      styles.button,

      size === "small" &&
        styles.smallButton,

      size === "large" &&
        styles.largeButton,

      fullWidth &&
        styles.fullWidth,

      variant ===
        "primary" && {
        backgroundColor:
          colors.primary,
      },

      variant ===
        "outline" && {
        backgroundColor:
          "transparent",

        borderWidth: 1.5,

        borderColor:
          colors.primary,
      },

      disabled &&
        styles.disabled,

      style,
    ];

    const textColor =
      variant === "primary"
        ? colors.white ||
          "#FFFFFF"
        : colors.primary;

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        accessible
        accessibilityRole="button"
        accessibilityLabel={
          label
        }
        disabled={
          disabled ||
          loading
        }
        onPress={
          handlePress
        }
        style={buttonStyle}
      >
        {loading ? (
          <ActivityIndicator
            size="small"
            color={textColor}
          />
        ) : (
          <>
            <MaterialCommunityIcons
              name={icon}
              size={
                size === "small"
                  ? 18
                  : 20
              }
              color={textColor}
            />

            <Text
              style={[
                styles.text,
                {
                  color:
                    textColor,
                },

                size ===
                  "small" &&
                  styles.smallText,

                size ===
                  "large" &&
                  styles.largeText,
              ]}
            >
              {label}
            </Text>
          </>
        )}
      </Pressable>
    );
  }
);

WishlistShareButton.displayName =
  "WishlistShareButton";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WishlistShareButton.propTypes = {
  label:
    PropTypes.string,

  icon:
    PropTypes.string,

  variant:
    PropTypes.oneOf([
      "primary",
      "outline",
    ]),

  size:
    PropTypes.oneOf([
      "small",
      "medium",
      "large",
    ]),

  fullWidth:
    PropTypes.bool,

  disabled:
    PropTypes.bool,

  loading:
    PropTypes.bool,

  onPress:
    PropTypes.func,

  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

WishlistShareButton.defaultProps =
  {
    label:
      "Share Wishlist",

    icon:
      "share-variant",

    variant:
      "primary",

    size:
      "medium",

    fullWidth: false,

    disabled: false,

    loading: false,

    onPress: null,

    style: null,
  };

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    button: {
      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "center",

      borderRadius: 14,

      height: 50,

      paddingHorizontal: 22,
    },

    fullWidth: {
      width: "100%",
    },

    disabled: {
      opacity: 0.5,
    },

    smallButton: {
      height: 40,

      paddingHorizontal: 16,
    },

    largeButton: {
      height: 56,

      paddingHorizontal: 28,
    },

    text: {
      marginLeft: 8,

      fontSize: 15,

      fontWeight: "700",
    },

    smallText: {
      fontSize: 13,
    },

    largeText: {
      fontSize: 16,
    },
  });

export default WishlistShareButton;