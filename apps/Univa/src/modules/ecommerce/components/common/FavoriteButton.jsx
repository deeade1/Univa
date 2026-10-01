/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/FavoriteButton.jsx      */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
  useMemo,
} from "react";

import {
  Pressable,
  StyleSheet,
  ActivityIndicator,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const FavoriteButton = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* State                                                                   */
    /* ---------------------------------------------------------------------- */

    favorite = false,

    loading = false,

    disabled = false,

    /* ---------------------------------------------------------------------- */
    /* Behaviour                                                               */
    /* ---------------------------------------------------------------------- */

    onPress,

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                              */
    /* ---------------------------------------------------------------------- */

    size = "md", // xs | sm | md | lg | xl

    variant = "filled", // filled | outlined | ghost

    activeColor,

    inactiveColor,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const metrics =
      useMemo(() => {
        switch (size) {
          case "xs":
            return {
              button: 28,
              icon: 14,
            };

          case "sm":
            return {
              button: 34,
              icon: 18,
            };

          case "lg":
            return {
              button: 48,
              icon: 26,
            };

          case "xl":
            return {
              button: 56,
              icon: 32,
            };

          default:
            return {
              button: 40,
              icon: 22,
            };
        }
      }, [size]);

    /* ---------------------------------------------------------------------- */

    const iconColor =
      favorite
        ? activeColor ??
          colors.error
        : inactiveColor ??
          colors.textSecondary;

    /* ---------------------------------------------------------------------- */

    const backgroundColor =
      useMemo(() => {
        switch (variant) {
          case "ghost":
            return "transparent";

          case "outlined":
            return colors.background;

          default:
            return colors.card;
        }
      }, [
        variant,
        colors,
      ]);

    /* ---------------------------------------------------------------------- */

    const borderWidth =
      variant ===
      "outlined"
        ? 1
        : 0;

    /* ---------------------------------------------------------------------- */

    const handlePress =
      useCallback(() => {
        if (
          disabled ||
          loading
        ) {
          return;
        }

        onPress?.(
          !favorite
        );
      }, [
        favorite,
        disabled,
        loading,
        onPress,
      ]);

    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        onPress={
          handlePress
        }
        disabled={
          disabled ||
          loading
        }
        android_ripple={{
          color:
            colors.border,
          borderless: true,
        }}
        style={[
          styles.container,

          {
            width:
              metrics.button,

            height:
              metrics.button,

            borderRadius:
              metrics.button /
              2,

            backgroundColor,

            borderWidth,

            borderColor:
              colors.border,

            opacity:
              disabled
                ? 0.45
                : 1,
          },

          style,
        ]}
      >
        {loading ? (
          <ActivityIndicator
            size="small"
            color={
              iconColor
            }
          />
        ) : (
          <MaterialCommunityIcons
            name={
              favorite
                ? "heart"
                : "heart-outline"
            }
            size={
              metrics.icon
            }
            color={
              iconColor
            }
          />
        )}
      </Pressable>
    );
  }
);

/* -------------------------------------------------------------------------- */

FavoriteButton.displayName =
  "FavoriteButton";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      justifyContent:
        "center",

      alignItems:
        "center",
    },
  });

/* -------------------------------------------------------------------------- */

export default FavoriteButton;