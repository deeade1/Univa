/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistMoveToCart.jsx */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  Pressable,
  Text,
  ActivityIndicator,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WishlistMoveToCart = memo(
  ({
    product = null,

    label = "Move to Cart",

    icon = "cart-plus",

    inStock = true,

    fullWidth = true,

    size = "medium",

    loading = false,

    disabled = false,

    onPress,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Derived State                                                          */
    /* ---------------------------------------------------------------------- */

    const isDisabled =
      disabled ||
      loading ||
      !inStock;

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handlePress =
      useCallback(() => {
        if (isDisabled) {
          return;
        }

        onPress?.(product);
      }, [
        isDisabled,
        onPress,
        product,
      ]);

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
        accessibilityState={{
          disabled: isDisabled,
        }}
        disabled={isDisabled}
        onPress={handlePress}
        style={[
          styles.button,

          fullWidth &&
            styles.fullWidth,

          size === "small" &&
            styles.smallButton,

          size === "large" &&
            styles.largeButton,

          {
            backgroundColor:
              isDisabled
                ? colors.border
                : colors.primary,
          },

          style,
        ]}
      >
        {loading ? (
          <ActivityIndicator
            size="small"
            color={
              colors.white ||
              "#FFFFFF"
            }
          />
        ) : (
          <>
            <MaterialCommunityIcons
              name={
                inStock
                  ? icon
                  : "cart-off"
              }
              size={
                size === "small"
                  ? 18
                  : 20
              }
              color={
                colors.white ||
                "#FFFFFF"
              }
            />

            <Text
              style={[
                styles.text,

                size ===
                  "small" &&
                  styles.smallText,

                size ===
                  "large" &&
                  styles.largeText,
              ]}
            >
              {inStock
                ? label
                : "Out of Stock"}
            </Text>
          </>
        )}
      </Pressable>
    );
  }
);

WishlistMoveToCart.displayName =
  "WishlistMoveToCart";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WishlistMoveToCart.propTypes = {
  product:
    PropTypes.object,

  label:
    PropTypes.string,

  icon:
    PropTypes.string,

  inStock:
    PropTypes.bool,

  fullWidth:
    PropTypes.bool,

  size:
    PropTypes.oneOf([
      "small",
      "medium",
      "large",
    ]),

  loading:
    PropTypes.bool,

  disabled:
    PropTypes.bool,

  onPress:
    PropTypes.func,

  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

WishlistMoveToCart.defaultProps =
  {
    product: null,

    label:
      "Move to Cart",

    icon:
      "cart-plus",

    inStock: true,

    fullWidth: true,

    size: "medium",

    loading: false,

    disabled: false,

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

      color: "#FFFFFF",

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

export default WishlistMoveToCart;