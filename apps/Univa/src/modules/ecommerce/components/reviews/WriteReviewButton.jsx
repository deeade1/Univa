/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/reviews/WriteReviewButton.jsx  */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";

import {
  Pressable,
  Text,
  ActivityIndicator,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WriteReviewButton = memo(
  ({
    title = "Write a Review",

    icon = "pencil-outline",

    variant = "filled", // filled | outlined | text

    size = "medium", // small | medium | large

    fullWidth = true,

    disabled = false,

    loading = false,

    onPress,

    style,

    textStyle,
  }) => {
    const { colors } = theme;


    const isFilled =
      variant === "filled";

    const isOutlined =
      variant === "outlined";

    const isSmall =
      size === "small";

    const isLarge =
      size === "large";

    return (
      <Pressable
        disabled={
          disabled || loading
        }
        onPress={onPress}
        style={({ pressed }) => [
          styles.button,

          fullWidth &&
            styles.fullWidth,

          isSmall &&
            styles.small,

          isLarge &&
            styles.large,

          isFilled && {
            backgroundColor:
              colors.primary,
          },

          isOutlined && {
            borderWidth: 1.5,
            borderColor:
              colors.primary,
            backgroundColor:
              "transparent",
          },

          pressed &&
            !disabled && {
              opacity: 0.85,
            },

          disabled &&
            styles.disabled,

          style,
        ]}
      >
        {loading ? (
          <ActivityIndicator
            size="small"
            color={
              isFilled
                ? "#FFFFFF"
                : colors.primary
            }
          />
        ) : (
          <>
            <MaterialCommunityIcons
              name={icon}
              size={
                isSmall
                  ? 18
                  : isLarge
                  ? 24
                  : 20
              }
              color={
                isFilled
                  ? "#FFFFFF"
                  : colors.primary
              }
            />

            <Text
              style={[
                styles.text,

                {
                  color:
                    isFilled
                      ? "#FFFFFF"
                      : colors.primary,
                },

                isSmall &&
                  styles.smallText,

                isLarge &&
                  styles.largeText,

                textStyle,
              ]}
            >
              {title}
            </Text>
          </>
        )}
      </Pressable>
    );
  }
);

WriteReviewButton.displayName =
  "WriteReviewButton";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    button: {
      flexDirection: "row",

      justifyContent:
        "center",

      alignItems: "center",

      borderRadius: 14,

      paddingHorizontal: 18,

      height: 52,
    },

    fullWidth: {
      width: "100%",
    },

    small: {
      height: 40,

      paddingHorizontal: 14,

      borderRadius: 10,
    },

    large: {
      height: 60,

      paddingHorizontal: 24,

      borderRadius: 16,
    },

    disabled: {
      opacity: 0.5,
    },

    text: {
      marginLeft: 8,

      fontSize: 16,

      fontWeight: "700",
    },

    smallText: {
      fontSize: 14,
    },

    largeText: {
      fontSize: 18,
    },
  });

export default WriteReviewButton;