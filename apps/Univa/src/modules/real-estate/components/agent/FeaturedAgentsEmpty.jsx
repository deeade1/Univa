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
/* Featured Agents Empty */
/* -------------------------------------------------------------------------- */

const FeaturedAgentsEmpty = memo(({
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
        name="account-search-outline"
        size={56}
        color={colors.textSecondary}
      />

      <Text
        style={[
          styles.title,
          {
            color: colors.text,
          },
        ]}
      >
        No featured agents available
      </Text>

      <Text
        style={[
          styles.description,
          {
            color: colors.textSecondary,
          },
        ]}
      >
        We couldn't find any featured real estate agents at the moment.
        Please check back later or refresh the page.
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
          <MaterialCommunityIcons
            name="refresh"
            size={18}
            color={colors.onPrimary || "#FFFFFF"}
          />

          <Text
            style={[
              styles.buttonText,
              {
                color: colors.onPrimary || "#FFFFFF",
              },
            ]}
          >
            Try Again
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
});

FeaturedAgentsEmpty.displayName = "FeaturedAgentsEmpty";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 20,
    marginTop: 24,
    paddingVertical: 40,
    paddingHorizontal: 24,
    borderRadius: 20,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },

  title: {
    marginTop: 18,
    fontSize: 20,
    fontWeight: "700",
    textAlign: "center",
  },

  description: {
    marginTop: 10,
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
    maxWidth: 300,
  },

  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 24,
    paddingHorizontal: 22,
    paddingVertical: 12,
    borderRadius: 12,
  },

  buttonText: {
    marginLeft: 8,
    fontSize: 15,
    fontWeight: "700",
  },
});

export default FeaturedAgentsEmpty;