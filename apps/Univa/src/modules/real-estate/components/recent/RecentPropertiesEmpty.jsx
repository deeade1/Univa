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
/* Recent Properties Empty */
/* -------------------------------------------------------------------------- */

function RecentPropertiesEmpty() {
  const router = useRouter();

  const { colors } = useTheme();

  return (
    <View style={styles.container}>
      {/* ------------------------------------------------------------------ */}
      {/* Icon */}
      {/* ------------------------------------------------------------------ */}

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
          name="home-outline"
          size={46}
          color={colors.primary}
        />
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Title */}
      {/* ------------------------------------------------------------------ */}

      <Text
        style={[
          styles.title,
          {
            color: colors.text,
          },
        ]}
      >
        No Recent Properties
      </Text>

      {/* ------------------------------------------------------------------ */}
      {/* Description */}
      {/* ------------------------------------------------------------------ */}

      <Text
        style={[
          styles.description,
          {
            color:
              colors.textSecondary,
          },
        ]}
      >
        We couldn't find any recently added
        properties right now.
        {"\n"}
        Check back later or browse all
        available listings.
      </Text>

      {/* ------------------------------------------------------------------ */}
      {/* Browse Button */}
      {/* ------------------------------------------------------------------ */}

      <Pressable
        style={[
          styles.button,
          {
            backgroundColor:
              colors.primary,
          },
        ]}
        onPress={() =>
          router.push(
            "/real-estate"
          )
        }
      >
        <Ionicons
          name="search-outline"
          size={18}
          color="#FFFFFF"
        />

        <Text style={styles.buttonText}>
          Browse Properties
        </Text>
      </Pressable>
    </View>
  );
}

const styles =
  StyleSheet.create({
    container: {
      alignItems: "center",

      justifyContent: "center",

      paddingHorizontal: 32,

      paddingVertical: 56,
    },

    iconContainer: {
      width: 90,

      height: 90,

      borderRadius: 45,

      justifyContent: "center",

      alignItems: "center",

      marginBottom: 20,
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
    },

    button: {
      marginTop: 28,

      flexDirection: "row",

      alignItems: "center",

      paddingHorizontal: 22,

      paddingVertical: 14,

      borderRadius: 12,
    },

    buttonText: {
      color: "#FFFFFF",

      fontWeight: "700",

      fontSize: 15,

      marginLeft: 8,
    },
  });

export default memo(
  RecentPropertiesEmpty
);