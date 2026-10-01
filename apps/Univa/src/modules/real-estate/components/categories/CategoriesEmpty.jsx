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

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/*
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

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Categories Empty */
/* -------------------------------------------------------------------------- */

function CategoriesEmpty({
  onRefresh,
}) {
  const { colors } = useTheme();

  return (
    <View style={styles.container}>
      {/* ------------------------------------------------------ */}
      {/* Icon */}
      {/* ------------------------------------------------------ */}

      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor:
              `${colors.primary}15`,
          },
        ]}
      >
        <Ionicons
          name="grid-outline"
          size={56}
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
        No Categories Found
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
        We couldn't find any property
        categories at the moment.
        Please try again later.
      </Text>

      {/* ------------------------------------------------------ */}
      {/* Action */}
      {/* ------------------------------------------------------ */}

      {onRefresh && (
        <Pressable
          onPress={onRefresh}
          style={[
            styles.button,
            {
              backgroundColor:
                colors.primary,
            },
          ]}
        >
          <Ionicons
            name="refresh-outline"
            size={18}
            color="#FFFFFF"
          />

          <Text
            style={styles.buttonText}
          >
            Refresh
          </Text>
        </Pressable>
      )}
    </View>
  );
}

const styles =
  StyleSheet.create({
    container: {
      marginTop: 28,

      marginHorizontal: 16,

      paddingVertical: 40,

      paddingHorizontal: 24,

      alignItems: "center",

      justifyContent: "center",
    },

    iconContainer: {
      width: 96,

      height: 96,

      borderRadius: 48,

      alignItems: "center",

      justifyContent: "center",
    },

    title: {
      marginTop: 24,

      fontSize: 22,

      fontWeight: "700",

      textAlign: "center",
    },

    description: {
      marginTop: 12,

      fontSize: 15,

      lineHeight: 22,

      textAlign: "center",

      maxWidth: 280,
    },

    button: {
      marginTop: 28,

      flexDirection: "row",

      alignItems: "center",

      justifyContent: "center",

      paddingHorizontal: 24,

      paddingVertical: 14,

      borderRadius: 12,
    },

    buttonText: {
      color: "#FFFFFF",

      fontSize: 15,

      fontWeight: "700",

      marginLeft: 8,
    },
  });

export default memo(
  CategoriesEmpty
);