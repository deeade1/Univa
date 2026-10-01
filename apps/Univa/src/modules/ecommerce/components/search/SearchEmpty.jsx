/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchEmpty.jsx         */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
} from "react";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */

const SearchEmpty = memo(
  ({
    query = "",

    title,

    message,

    icon = "magnify-close",

    buttonText = "Browse Products",

    showButton = false,

    onPress,

    style,
  }) => {
    const { colors } = theme;


    const emptyTitle =
      title ??
      (query
        ? "No Results Found"
        : "Start Searching");

    const emptyMessage =
      message ??
      (query
        ? `We couldn't find anything matching "${query}". Try another keyword or adjust your filters.`
        : "Search for products, brands, categories, or sellers.");

    return (
      <View
        style={[
          styles.container,
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Icon */}
        {/* -------------------------------------------------------------- */}

        <View
          style={[
            styles.iconContainer,
            {
              backgroundColor:
                colors.surface ??
                colors.card,
            },
          ]}
        >
          <MaterialCommunityIcons
            name={icon}
            size={64}
            color={
              colors.primary
            }
          />
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Title */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.title,
            {
              color:
                colors.text,
            },
          ]}
        >
          {emptyTitle}
        </Text>

        {/* -------------------------------------------------------------- */}
        {/* Message */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.message,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          {emptyMessage}
        </Text>

        {/* -------------------------------------------------------------- */}
        {/* Action */}
        {/* -------------------------------------------------------------- */}

        {showButton && (
          <Pressable
            accessibilityRole="button"
            onPress={onPress}
            style={[
              styles.button,
              {
                backgroundColor:
                  colors.primary,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="shopping-outline"
              size={20}
              color="#FFF"
            />

            <Text
              style={
                styles.buttonText
              }
            >
              {buttonText}
            </Text>
          </Pressable>
        )}
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

SearchEmpty.displayName =
  "SearchEmpty";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flex: 1,

      alignItems:
        "center",

      justifyContent:
        "center",

      paddingHorizontal: 32,

      paddingVertical: 48,
    },

    iconContainer: {
      width: 120,

      height: 120,

      borderRadius: 60,

      alignItems:
        "center",

      justifyContent:
        "center",

      marginBottom: 24,
    },

    title: {
      fontSize: 22,

      fontWeight: "700",

      textAlign:
        "center",

      marginBottom: 12,
    },

    message: {
      fontSize: 15,

      lineHeight: 24,

      textAlign:
        "center",

      marginBottom: 28,
    },

    button: {
      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "center",

      paddingHorizontal: 22,

      paddingVertical: 14,

      borderRadius: 14,
    },

    buttonText: {
      color: "#FFF",

      fontSize: 15,

      fontWeight: "700",

      marginLeft: 8,
    },
  });

/* -------------------------------------------------------------------------- */

export default SearchEmpty;