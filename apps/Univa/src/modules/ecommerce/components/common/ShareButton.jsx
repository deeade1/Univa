/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ShareButton.jsx         */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
  useMemo,
  useState,
} from "react";

import {
  Pressable,
  StyleSheet,
  ActivityIndicator,
  Share,
  Alert,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const ShareButton = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Share Data                                                              */
    /* ---------------------------------------------------------------------- */

    title,

    message,

    url,

    subject,

    /* ---------------------------------------------------------------------- */
    /* Behaviour                                                               */
    /* ---------------------------------------------------------------------- */

    onPress,

    onShared,

    onError,

    disabled = false,

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                              */
    /* ---------------------------------------------------------------------- */

    size = "md", // xs | sm | md | lg | xl

    variant = "filled", // filled | outlined | ghost

    color,

    backgroundColor,

    style,
  }) => {
    const { colors } = theme;


    const [loading, setLoading] =
      useState(false);

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

    const containerStyle =
      useMemo(() => {
        switch (variant) {
          case "outlined":
            return {
              backgroundColor:
                backgroundColor ??
                colors.background,

              borderWidth: 1,

              borderColor:
                colors.border,
            };

          case "ghost":
            return {
              backgroundColor:
                "transparent",

              borderWidth: 0,
            };

          default:
            return {
              backgroundColor:
                backgroundColor ??
                colors.card,

              borderWidth: 0,
            };
        }
      }, [
        variant,
        backgroundColor,
        colors,
      ]);

    /* ---------------------------------------------------------------------- */

    const handleShare =
      useCallback(async () => {
        if (
          disabled ||
          loading
        ) {
          return;
        }

        onPress?.();

        try {
          setLoading(true);

          const response =
            await Share.share({
              title,

              message,

              url,

              subject,
            });

          if (
            response.action ===
            Share.sharedAction
          ) {
            onShared?.(
              response
            );
          }
        } catch (error) {
          console.error(
            error
          );

          Alert.alert(
            "Share Failed",
            "Unable to share at the moment."
          );

          onError?.(
            error
          );
        } finally {
          setLoading(false);
        }
      }, [
        title,
        message,
        url,
        subject,
        disabled,
        loading,
        onPress,
        onShared,
        onError,
      ]);

    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        onPress={
          handleShare
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

          containerStyle,

          {
            width:
              metrics.button,

            height:
              metrics.button,

            borderRadius:
              metrics.button /
              2,

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
              color ??
              colors.primary
            }
          />
        ) : (
          <MaterialCommunityIcons
            name="share-variant"
            size={
              metrics.icon
            }
            color={
              color ??
              colors.text
            }
          />
        )}
      </Pressable>
    );
  }
);

/* -------------------------------------------------------------------------- */

ShareButton.displayName =
  "ShareButton";

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

export default ShareButton;