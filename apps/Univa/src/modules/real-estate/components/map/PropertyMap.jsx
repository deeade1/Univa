import React, { memo, useMemo } from "react";
import {
  ActivityIndicator,
  Platform,
  StyleSheet,
  Text,
  View,
} from "react-native";

import * as Device from "expo-device";

import { useTheme } from "@/theme";

import NativePropertyMap from "./NativePropertyMap";
import WebPropertyMap from "./WebPropertyMap";

/* -------------------------------------------------------------------------- */
/* Property Map */
/* -------------------------------------------------------------------------- */

const PropertyMap = memo((props) => {
  const { colors } = useTheme();

  const {
    loading = false,
    error = null,
    disabled = false,
  } = props;

  /* ---------------------------------------------------------------------- */
  /* Platform Detection */
  /* ---------------------------------------------------------------------- */

  const isWeb = Platform.OS === "web";

  const isAndroidEmulator = useMemo(
    () =>
      Platform.OS === "android" &&
      !Device.isDevice,
    []
  );

  /* ---------------------------------------------------------------------- */
  /* Loading */
  /* ---------------------------------------------------------------------- */

  if (loading) {
    return (
      <View
        style={[
          styles.center,
          {
            backgroundColor: colors.card,
          },
        ]}
      >
        <ActivityIndicator
          size="large"
          color={colors.primary}
        />

        <Text
          style={[
            styles.message,
            {
              color: colors.textSecondary,
            },
          ]}
        >
          Loading map...
        </Text>
      </View>
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  if (error) {
    return (
      <View
        style={[
          styles.center,
          {
            backgroundColor: colors.card,
          },
        ]}
      >
        <Text
          style={[
            styles.title,
            {
              color: colors.text,
            },
          ]}
        >
          Unable to load map
        </Text>

        <Text
          style={[
            styles.message,
            {
              color: colors.textSecondary,
            },
          ]}
        >
          {typeof error === "string"
            ? error
            : "Something went wrong while loading the map."}
        </Text>
      </View>
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Disabled */
  /* ---------------------------------------------------------------------- */

  if (disabled) {
    return (
      <View
        style={[
          styles.center,
          {
            backgroundColor: colors.card,
          },
        ]}
      >
        <Text
          style={[
            styles.title,
            {
              color: colors.text,
            },
          ]}
        >
          Map unavailable
        </Text>

        <Text
          style={[
            styles.message,
            {
              color: colors.textSecondary,
            },
          ]}
        >
          Map services are currently unavailable.
        </Text>
      </View>
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Web */
  /* ---------------------------------------------------------------------- */

  if (isWeb) {
    return <WebPropertyMap {...props} />;
  }

  /* ---------------------------------------------------------------------- */
  /* Android Emulator */
  /* ---------------------------------------------------------------------- */

  if (isAndroidEmulator) {
    console.log("Running on Android Emulator");
  }

  /* ---------------------------------------------------------------------- */
  /* Android / iOS */
  /* ---------------------------------------------------------------------- */

  return <NativePropertyMap {...props} />;
});

PropertyMap.displayName = "PropertyMap";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  center: {
    height: 320,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
  },

  title: {
    marginTop: 16,
    fontSize: 20,
    fontWeight: "700",
    textAlign: "center",
  },

  message: {
    marginTop: 10,
    fontSize: 15,
    lineHeight: 22,
    textAlign: "center",
  },
});

export default PropertyMap;