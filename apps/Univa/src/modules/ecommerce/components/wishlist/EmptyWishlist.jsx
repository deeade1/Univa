/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/EmptyWishlist.jsx     */
/* -------------------------------------------------------------------------- */

import React, { memo, useCallback } from "react";
import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const EmptyWishlist = memo(({
  title = "Your wishlist is empty",
  description = "Save products you love so you can easily find them later.",
  buttonText = "Start Shopping",
  icon = "heart-outline",
  showButton = true,
  onPress,
  style,
}) => {
  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Memoized Handlers                                                      */
  /* ---------------------------------------------------------------------- */

  const handlePress = useCallback(() => {
    onPress?.();
  }, [onPress]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View
      accessible
      accessibilityRole="summary"
      accessibilityLabel={`Empty wishlist: ${title}`}
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
            backgroundColor: colors.primary + "15",
          },
        ]}
      >
        <MaterialCommunityIcons
          name={icon}
          size={72}
          color={colors.primary}
        />
      </View>

      {/* -------------------------------------------------------------- */}
      {/* Title */}
      {/* -------------------------------------------------------------- */}

      <Text
        style={[
          styles.title,
          { color: colors.text },
        ]}
      >
        {title}
      </Text>

      {/* -------------------------------------------------------------- */}
      {/* Description */}
      {/* -------------------------------------------------------------- */}

      <Text
        style={[
          styles.description,
          { color: colors.textSecondary },
        ]}
      >
        {description}
      </Text>

      {/* -------------------------------------------------------------- */}
      {/* Button */}
      {/* -------------------------------------------------------------- */}

      {showButton && (
        <Pressable
          accessible
          accessibilityRole="button"
          accessibilityLabel={buttonText}
          accessibilityState={{ disabled: !onPress }}
          disabled={!onPress}
          onPress={handlePress}
          style={[
            styles.button,
            {
              backgroundColor: onPress ? colors.primary : colors.border,
            },
          ]}
        >
          <MaterialCommunityIcons
            name="shopping"
            size={20}
            color={colors.white}
          />

          <Text
            style={[
              styles.buttonText,
              {
                color: onPress ? colors.white : colors.textSecondary,
              },
            ]}
          >
            {buttonText}
          </Text>
        </Pressable>
      )}
    </View>
  );
});

EmptyWishlist.displayName = "EmptyWishlist";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

EmptyWishlist.propTypes = {
  /**
   * Main title of the empty state
   */
  title: PropTypes.string,

  /**
   * Description/help text
   */
  description: PropTypes.string,

  /**
   * Text for the action button
   */
  buttonText: PropTypes.string,

  /**
   * Icon name from MaterialCommunityIcons
   */
  icon: PropTypes.string,

  /**
   * Whether to show the action button
   */
  showButton: PropTypes.bool,

  /**
   * Called when the button is pressed
   */
  onPress: PropTypes.func,

  /**
   * Optional style overrides
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

EmptyWishlist.defaultProps = {
  title: "Your wishlist is empty",
  description: "Save products you love so you can easily find them later.",
  buttonText: "Start Shopping",
  icon: "heart-outline",
  showButton: true,
  onPress: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
    paddingVertical: 48,
  },

  iconContainer: {
    width: 140,
    height: 140,
    borderRadius: 70,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 28,
  },

  title: {
    fontSize: 24,
    fontWeight: "700",
    textAlign: "center",
  },

  description: {
    marginTop: 12,
    fontSize: 15,
    lineHeight: 22,
    textAlign: "center",
    maxWidth: 320,
  },

  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 32,
    paddingHorizontal: 24,
    height: 52,
    borderRadius: 14,
  },

  buttonText: {
    marginLeft: 8,
    fontSize: 16,
    fontWeight: "700",
  },
});

export default EmptyWishlist;