/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/NetworkImage.jsx        */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useState,
} from "react";

import {
  View,
  Image,
  ActivityIndicator,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const NetworkImage = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Source                                                                  */
    /* ---------------------------------------------------------------------- */

    source,

    uri,

    alt,

    resizeMode = "cover",

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                              */
    /* ---------------------------------------------------------------------- */

    width,

    height,

    borderRadius = 12,

    backgroundColor,

    showLoader = true,

    showPlaceholder = true,

    placeholderIcon = "image-outline",

    style,

    imageStyle,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                  */
    /* ---------------------------------------------------------------------- */

    onLoad,

    onError,

    onLoadStart,

    onLoadEnd,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const [loading, setLoading] =
      useState(false);

    const [failed, setFailed] =
      useState(false);

    /* ---------------------------------------------------------------------- */

    const imageSource =
      useMemo(() => {
        if (source) {
          return source;
        }

        if (
          typeof uri ===
            "string" &&
          uri.length > 0
        ) {
          return {
            uri,
          };
        }

        return null;
      }, [
        source,
        uri,
      ]);

    /* ---------------------------------------------------------------------- */

    const containerStyle =
      useMemo(
        () => ({
          width,

          height,

          borderRadius,

          backgroundColor:
            backgroundColor ??
            colors.surface ??
            colors.card,
        }),
        [
          width,
          height,
          borderRadius,
          backgroundColor,
          colors,
        ]
      );

    /* ---------------------------------------------------------------------- */

    return (
      <View
        accessible
        accessibilityLabel={
          alt
        }
        style={[
          styles.container,

          containerStyle,

          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Placeholder */}
        {/* -------------------------------------------------------------- */}

        {(!imageSource ||
          failed) &&
          showPlaceholder && (
            <View
              style={
                styles.placeholder
              }
            >
              <MaterialCommunityIcons
                name={
                  placeholderIcon
                }
                size={34}
                color={
                  colors.textSecondary
                }
              />
            </View>
          )}

        {/* -------------------------------------------------------------- */}
        {/* Image */}
        {/* -------------------------------------------------------------- */}

        {!!imageSource &&
          !failed && (
            <Image
              source={
                imageSource
              }
              resizeMode={
                resizeMode
              }
              style={[
                styles.image,

                {
                  borderRadius,
                },

                imageStyle,
              ]}
              onLoadStart={() => {
                setLoading(
                  true
                );

                onLoadStart?.();
              }}
              onLoad={(e) => {
                setLoading(
                  false
                );

                onLoad?.(
                  e
                );
              }}
              onLoadEnd={() => {
                setLoading(
                  false
                );

                onLoadEnd?.();
              }}
              onError={(
                e
              ) => {
                setLoading(
                  false
                );

                setFailed(
                  true
                );

                onError?.(
                  e
                );
              }}
            />
          )}

        {/* -------------------------------------------------------------- */}
        {/* Loader */}
        {/* -------------------------------------------------------------- */}

        {loading &&
          showLoader && (
            <View
              style={
                styles.loader
              }
            >
              <ActivityIndicator
                color={
                  colors.primary
                }
              />
            </View>
          )}
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

NetworkImage.displayName =
  "NetworkImage";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      overflow: "hidden",

      justifyContent:
        "center",

      alignItems:
        "center",
    },

    image: {
      width: "100%",

      height: "100%",
    },

    loader: {
      ...StyleSheet.absoluteFillObject,

      justifyContent:
        "center",

      alignItems:
        "center",
    },

    placeholder: {
      ...StyleSheet.absoluteFillObject,

      justifyContent:
        "center",

      alignItems:
        "center",
    },
  });

/* -------------------------------------------------------------------------- */

export default NetworkImage;