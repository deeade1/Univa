import React, { memo } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Popular Locations Empty */
/* -------------------------------------------------------------------------- */

const PopularLocationsEmpty = memo(({
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
      <MaterialCommunityIcons
        name="map-marker-off-outline"
        size={48}
        color={colors.textSecondary}
      />

      <Text
        style={[
          styles.title,
          { color: colors.text },
        ]}
      >
        No popular locations found
      </Text>

      <Text
        style={[
          styles.description,
          { color: colors.textSecondary },
        ]}
      >
        We couldn't find any popular locations right now.
        Please try again in a moment.
      </Text>

      {onRetry && (
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={onRetry}
          style={[
            styles.button,
            {
              backgroundColor: colors.primary,
            },
          ]}
        >
          <Text
            style={[
              styles.buttonText,
              { color: colors.onPrimary || "#FFFFFF" },
            ]}
          >
            Try Again
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
});

PopularLocationsEmpty.displayName = "PopularLocationsEmpty";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 20,
    marginTop: 20,
    paddingVertical: 40,
    paddingHorizontal: 24,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },

  title: {
    marginTop: 16,
    fontSize: 18,
    fontWeight: "700",
    textAlign: "center",
  },

  description: {
    marginTop: 8,
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
    maxWidth: 280,
  },

  button: {
    marginTop: 24,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },

  buttonText: {
    fontSize: 15,
    fontWeight: "700",
  },
});

export default PopularLocationsEmpty;