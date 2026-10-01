import React, {
  memo,
} from "react";

import {
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { useRouter } from "expo-router";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Recommended Properties Empty */
/* -------------------------------------------------------------------------- */

function RecommendedPropertiesEmpty() {
  const router = useRouter();

  const { colors } = useTheme();

  return (
    <View style={styles.container}>
      {/* -------------------------------------------------- */}
      {/* Icon */}
      {/* -------------------------------------------------- */}

      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor:
              colors.primary + "15",
          },
        ]}
      >
        <Ionicons
          name="sparkles-outline"
          size={54}
          color={colors.primary}
        />
      </View>

      {/* -------------------------------------------------- */}
      {/* Title */}
      {/* -------------------------------------------------- */}

      <Text
        style={[
          styles.title,
          {
            color: colors.text,
          },
        ]}
      >
        No Recommendations Yet
      </Text>

      {/* -------------------------------------------------- */}
      {/* Description */}
      {/* -------------------------------------------------- */}

      <Text
        style={[
          styles.description,
          {
            color:
              colors.textSecondary,
          },
        ]}
      >
        Browse more properties, save your
        favorites, or update your search
        preferences to receive personalized
        recommendations selected just for
        you.
      </Text>

      {/* -------------------------------------------------- */}
      {/* Actions */}
      {/* -------------------------------------------------- */}

      <View style={styles.actions}>
        <Pressable
          style={[
            styles.primaryButton,
            {
              backgroundColor:
                colors.primary,
            },
          ]}
          onPress={() =>
            router.push(
              "/real-estate/map"
            )
          }
        >
          <Ionicons
            name="compass-outline"
            size={18}
            color="#FFFFFF"
          />

          <Text
            style={
              styles.primaryButtonText
            }
          >
            Explore Properties
          </Text>
        </Pressable>

        <Pressable
          style={[
            styles.secondaryButton,
            {
              borderColor:
                colors.border,
            },
          ]}
          onPress={() =>
            router.push(
              "/real-estate/saved"
            )
          }
        >
          <Ionicons
            name="heart-outline"
            size={18}
            color={colors.primary}
          />

          <Text
            style={[
              styles.secondaryButtonText,
              {
                color:
                  colors.primary,
              },
            ]}
          >
            View Saved
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles =
  StyleSheet.create({
    container: {
      paddingHorizontal: 32,

      paddingVertical: 56,

      alignItems: "center",

      justifyContent: "center",
    },

    iconContainer: {
      width: 100,

      height: 100,

      borderRadius: 50,

      alignItems: "center",

      justifyContent: "center",

      marginBottom: 24,
    },

    title: {
      fontSize: 24,

      fontWeight: "700",

      textAlign: "center",
    },

    description: {
      marginTop: 14,

      fontSize: 15,

      lineHeight: 24,

      textAlign: "center",
    },

    actions: {
      marginTop: 30,

      width: "100%",
    },

    primaryButton: {
      flexDirection: "row",

      justifyContent: "center",

      alignItems: "center",

      paddingVertical: 14,

      borderRadius: 12,
    },

    primaryButtonText: {
      marginLeft: 8,

      color: "#FFFFFF",

      fontSize: 15,

      fontWeight: "700",
    },

    secondaryButton: {
      marginTop: 14,

      flexDirection: "row",

      justifyContent: "center",

      alignItems: "center",

      borderWidth: 1,

      borderRadius: 12,

      paddingVertical: 14,
    },

    secondaryButtonText: {
      marginLeft: 8,

      fontSize: 15,

      fontWeight: "700",
    },
  });

export default memo(
  RecommendedPropertiesEmpty
);