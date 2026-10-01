/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/products/FeaturedProductsEmpty.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const FeaturedProductsEmpty = memo(
  ({
    icon = "shopping-outline",

    title = "No Products Available",

    message =
      "We couldn't find any products to display right now. Please check back later or explore another category.",

    buttonText = "Browse Categories",

    showButton = false,

    onPress,
  }) => {
    const { colors } = theme;


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
        {/* -------------------------------------------------------------- */}
        {/* Icon */}
        {/* -------------------------------------------------------------- */}

        <View
          style={[
            styles.iconContainer,
            {
              backgroundColor:
                colors.primary + "15",
            },
          ]}
        >
          <MaterialCommunityIcons
            name={icon}
            size={56}
            color={colors.primary}
          />
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Title */}
        {/* -------------------------------------------------------------- */}

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
          {message}
        </Text>

        {/* -------------------------------------------------------------- */}
        {/* Action */}
        {/* -------------------------------------------------------------- */}

        {showButton && (
          <Pressable
            style={[
              styles.button,
              {
                backgroundColor:
                  colors.primary,
              },
            ]}
            onPress={onPress}
          >
            <Text
              style={styles.buttonText}
            >
              {buttonText}
            </Text>
          </Pressable>
        )}
      </View>
    );
  }
);

FeaturedProductsEmpty.displayName =
  "FeaturedProductsEmpty";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginVertical: 20,

    paddingHorizontal: 24,
    paddingVertical: 36,

    borderRadius: 20,
    borderWidth: 1,

    justifyContent: "center",
    alignItems: "center",
  },

  iconContainer: {
    width: 96,
    height: 96,
    borderRadius: 48,

    justifyContent: "center",
    alignItems: "center",

    marginBottom: 20,
  },

  title: {
    fontSize: 22,
    fontWeight: "700",

    textAlign: "center",
  },

  message: {
    marginTop: 12,

    fontSize: 15,
    lineHeight: 24,

    textAlign: "center",

    maxWidth: 340,
  },

  button: {
    marginTop: 28,

    paddingHorizontal: 28,
    paddingVertical: 14,

    borderRadius: 14,

    justifyContent: "center",
    alignItems: "center",
  },

  buttonText: {
    color: "#FFFFFF",

    fontWeight: "700",

    fontSize: 15,
  },
});

export default FeaturedProductsEmpty;