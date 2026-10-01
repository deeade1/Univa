import React, {
  memo,
  useCallback,
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
/* Featured Properties Empty */
/* -------------------------------------------------------------------------- */

function FeaturedPropertiesEmpty() {
  const router = useRouter();

  const { colors } = useTheme();

  /* -------------------------------------------------------------------------- */
  /* Actions */
  /* -------------------------------------------------------------------------- */

  const handleBrowse =
    useCallback(() => {
      router.push(
        "/real-estate/properties"
      );
    }, [router]);

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor:
            colors.card,
        },
      ]}
    >
      {/* ------------------------------------------------------ */}
      {/* Icon */}
      {/* ------------------------------------------------------ */}

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
          size={52}
          color={colors.primary}
        />
      </View>

      {/* ------------------------------------------------------ */}
      {/* Title */}
      {/* ------------------------------------------------------ */}

      <Text
        style={[
          styles.title,
          {
            color: colors.text,
          },
        ]}
      >
        No Featured Properties
      </Text>

      {/* ------------------------------------------------------ */}
      {/* Description */}
      {/* ------------------------------------------------------ */}

      <Text
        style={[
          styles.description,
          {
            color:
              colors.textSecondary,
          },
        ]}
      >
        There are no featured properties
        available at the moment.
        Browse all available listings to
        discover homes, apartments,
        offices and land.
      </Text>

      {/* ------------------------------------------------------ */}
      {/* Browse Button */}
      {/* ------------------------------------------------------ */}

      <Pressable
        onPress={handleBrowse}
        style={[
          styles.button,
          {
            backgroundColor:
              colors.primary,
          },
        ]}
      >
        <Ionicons
          name="search-outline"
          size={18}
          color="#FFFFFF"
        />

        <Text
          style={styles.buttonText}
        >
          Browse Properties
        </Text>
      </Pressable>
    </View>
  );
}

const styles =
  StyleSheet.create({
    container: {
      marginHorizontal: 16,

      marginTop: 20,

      paddingVertical: 40,

      paddingHorizontal: 24,

      borderRadius: 24,

      alignItems: "center",
    },

    iconContainer: {
      width: 92,

      height: 92,

      borderRadius: 46,

      justifyContent: "center",

      alignItems: "center",

      marginBottom: 24,
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

      paddingHorizontal: 12,
    },

    button: {
      marginTop: 28,

      flexDirection: "row",

      alignItems: "center",

      justifyContent: "center",

      paddingHorizontal: 24,

      paddingVertical: 14,

      borderRadius: 14,
    },

    buttonText: {
      color: "#FFFFFF",

      fontWeight: "700",

      fontSize: 15,

      marginLeft: 8,
    },
  });

export default memo(
  FeaturedPropertiesEmpty
);