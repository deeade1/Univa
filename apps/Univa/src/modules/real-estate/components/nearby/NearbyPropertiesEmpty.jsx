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
/* Nearby Properties Empty */
/* -------------------------------------------------------------------------- */

function NearbyPropertiesEmpty() {
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
          name="location-outline"
          size={52}
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
        No Nearby Properties
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
        We couldn't find any properties
        near your current location.
        {"\n"}
        Try searching another area or
        browse all available listings.
      </Text>

      {/* ------------------------------------------------------------------ */}
      {/* Action */}
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
            "/real-estate/map"
          )
        }
      >
        <Ionicons
          name="map-outline"
          size={18}
          color="#FFFFFF"
        />

        <Text style={styles.buttonText}>
          Explore on Map
        </Text>
      </Pressable>
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
      width: 96,

      height: 96,

      borderRadius: 48,

      alignItems: "center",

      justifyContent: "center",

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
    },

    button: {
      marginTop: 30,

      flexDirection: "row",

      alignItems: "center",

      justifyContent: "center",

      paddingHorizontal: 24,

      paddingVertical: 14,

      borderRadius: 12,
    },

    buttonText: {
      marginLeft: 8,

      color: "#FFFFFF",

      fontSize: 15,

      fontWeight: "700",
    },
  });

export default memo(
  NearbyPropertiesEmpty
);