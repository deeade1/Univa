import React, { memo } from "react";
import {
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Map Unavailable */
/* -------------------------------------------------------------------------- */

const MapUnavailable = memo(
  ({
    title = "Map Unavailable",
    description = "The interactive map is currently unavailable on this device or platform.",
    buttonText = "Try Again",
    onRetry,
  }) => {
    const { colors } = useTheme();

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <View
          style={[
            styles.iconWrapper,
            {
              backgroundColor:
                colors.primary + "15",
            },
          ]}
        >
          <MaterialCommunityIcons
            name="map-off"
            size={64}
            color={colors.primary}
          />
        </View>

        <Text
          style={[
            styles.title,
            {
              color: colors.text,
            },
          ]}
        >
          {title}
        </Text>

        <Text
          style={[
            styles.description,
            {
              color: colors.textSecondary,
            },
          ]}
        >
          {description}
        </Text>

        <View style={styles.tips}>
          <Tip
            icon="check-circle-outline"
            text="Check your internet connection."
          />

          <Tip
            icon="check-circle-outline"
            text="Enable device location services."
          />

          <Tip
            icon="check-circle-outline"
            text="Restart the application if necessary."
          />
        </View>

        {onRetry && (
          <Pressable
            onPress={onRetry}
            android_ripple={{
              color: colors.border,
            }}
            style={[
              styles.button,
              {
                backgroundColor:
                  colors.primary,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="refresh"
              size={18}
              color={
                colors.onPrimary ||
                "#FFFFFF"
              }
            />

            <Text
              style={[
                styles.buttonText,
                {
                  color:
                    colors.onPrimary ||
                    "#FFFFFF",
                },
              ]}
            >
              {buttonText}
            </Text>
          </Pressable>
        )}
      </View>
    );
  }
);

MapUnavailable.displayName =
  "MapUnavailable";

/* -------------------------------------------------------------------------- */
/* Tip */
/* -------------------------------------------------------------------------- */

const Tip = memo(({ icon, text }) => {
  const { colors } = useTheme();

  return (
    <View style={styles.tip}>
      <MaterialCommunityIcons
        name={icon}
        size={18}
        color="#22C55E"
      />

      <Text
        style={[
          styles.tipText,
          {
            color: colors.textSecondary,
          },
        ]}
      >
        {text}
      </Text>
    </View>
  );
});

Tip.displayName = "Tip";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: 24,
    padding: 28,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 420,
  },

  iconWrapper: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 22,
  },

  title: {
    fontSize: 22,
    fontWeight: "700",
    textAlign: "center",
  },

  description: {
    marginTop: 12,
    fontSize: 15,
    lineHeight: 24,
    textAlign: "center",
    maxWidth: 340,
  },

  tips: {
    alignSelf: "stretch",
    marginTop: 26,
    marginBottom: 30,
  },

  tip: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
  },

  tipText: {
    marginLeft: 10,
    fontSize: 14,
    flex: 1,
  },

  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 14,
  },

  buttonText: {
    marginLeft: 8,
    fontSize: 15,
    fontWeight: "700",
  },
});

export default MapUnavailable;