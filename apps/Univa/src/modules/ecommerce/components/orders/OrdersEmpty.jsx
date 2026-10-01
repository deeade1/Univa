/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/orders/OrdersEmpty.jsx         */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import {
  colors,
  spacing,
  radius,
  typography,
} from "../../../theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const OrdersEmpty = memo(
  ({
    title = "No Orders Yet",
    description = "You haven't placed any orders yet. Browse our products and place your first order.",
    buttonText = "Start Shopping",
    icon = "package-variant-closed-remove",
    showButton = true,
    disabled = false,
    onPress,
    style,
  }) => {
    return (
      <View
        style={[
          styles.container,
          style,
        ]}
      >
        {/* ---------------------------------------------------------------- */}
        {/* Illustration                                                     */}
        {/* ---------------------------------------------------------------- */}

        <View
          accessibilityElementsHidden
          style={[
            styles.iconContainer,
            {
              backgroundColor: `${colors.primary}15`,
            },
          ]}
        >
          <MaterialCommunityIcons
            name={icon}
            size={72}
            color={colors.primary}
          />
        </View>

        {/* ---------------------------------------------------------------- */}
        {/* Content                                                          */}
        {/* ---------------------------------------------------------------- */}

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

        <Text
          style={[
            styles.description,
            {
              color: colors.textSecondary,
            },
          ]}
        >
          {description}
        </Text>

        {/* ---------------------------------------------------------------- */}
        {/* CTA                                                              */}
        {/* ---------------------------------------------------------------- */}

        {showButton && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={buttonText}
            disabled={disabled}
            onPress={onPress}
            style={({ pressed }) => [
              styles.button,
              {
                backgroundColor: colors.primary,
              },
              pressed && styles.buttonPressed,
              disabled && styles.disabledButton,
            ]}
          >
            <MaterialCommunityIcons
              name="shopping-outline"
              size={20}
              color={colors.white}
            />

            <Text
              style={[
                styles.buttonText,
                {
                  color: colors.white,
                },
              ]}
            >
              {buttonText}
            </Text>
          </Pressable>
        )}
      </View>
    );
  }
);

OrdersEmpty.displayName = "OrdersEmpty";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

OrdersEmpty.propTypes = {
  /**
   * Title text
   */
  title: PropTypes.string,

  /**
   * Description text
   */
  description: PropTypes.string,

  /**
   * Button text
   */
  buttonText: PropTypes.string,

  /**
   * Icon name from MaterialCommunityIcons
   */
  icon: PropTypes.string,

  /**
   * Whether to show the CTA button
   */
  showButton: PropTypes.bool,

  /**
   * Whether the button is disabled
   */
  disabled: PropTypes.bool,

  /**
   * Button press callback
   */
  onPress: PropTypes.func,

  /**
   * Optional style override
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

OrdersEmpty.defaultProps = {
  title: "No Orders Yet",
  description: "You haven't placed any orders yet. Browse our products and place your first order.",
  buttonText: "Start Shopping",
  icon: "package-variant-closed-remove",
  showButton: true,
  disabled: false,
  onPress: undefined,
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
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.xxxl,
  },

  iconContainer: {
    width: 140,
    height: 140,
    borderRadius: 70,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: spacing.xl,
  },

  title: {
    fontSize: typography.fontSize.xxl,
    fontWeight: typography.fontWeight.bold,
    textAlign: "center",
    marginBottom: spacing.md,
  },

  description: {
    fontSize: typography.fontSize.md,
    lineHeight: 24,
    textAlign: "center",
    marginBottom: spacing.xl,
  },

  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
    height: 52,
    borderRadius: radius.md,
  },

  buttonPressed: {
    opacity: 0.85,
  },

  disabledButton: {
    opacity: 0.5,
  },

  buttonText: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
    marginLeft: spacing.sm,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default OrdersEmpty;