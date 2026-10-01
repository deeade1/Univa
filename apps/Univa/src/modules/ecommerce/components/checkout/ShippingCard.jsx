/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/cart/ShippingCard.jsx          */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
} from "react";

import {
    Pressable,
    StyleSheet,
    Text,
    View,
} from "react-native";

import PropTypes from "prop-types";

import theme from "@/theme";

// Destructure theme values for use in styles
const { colors, spacing, typography, radius } = theme;

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ShippingCard = memo(({

    /* ---------------------------------------------------------------------- */
    /* Shipping                                                               */
    /* ---------------------------------------------------------------------- */

    title,

    carrier,

    estimatedDelivery,

    price = 0,

    currency = "₦",

    freeShipping = false,

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    selected = false,

    disabled = false,

    /* ---------------------------------------------------------------------- */
    /* Extras                                                                 */
    /* ---------------------------------------------------------------------- */

    icon,

    onPress,

    style,

}) => {

    /* ---------------------------------------------------------------------- */
    /* Formatted Price                                                        */
    /* ---------------------------------------------------------------------- */

    const formattedPrice = useMemo(() => {

        if (freeShipping) {

            return "Free";

        }

        const amount =
            Number(price) || 0;

        return `${currency}${amount.toLocaleString()}`;

    }, [

        currency,

        freeShipping,

        price,

    ]);

    /* ---------------------------------------------------------------------- */
    /* Card Colors                                                            */
    /* ---------------------------------------------------------------------- */

    const borderColor = selected

        ? (colors.primary ?? "#2563EB")

        : (colors.border ?? "#E5E7EB");

    const backgroundColor = disabled

        ? (colors.surfaceVariant ?? "#F5F5F5")

        : (colors.surface ?? "#FFFFFF");

    const opacity = disabled ? 0.6 : 1;

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (

        <Pressable

            accessibilityRole="button"

            accessibilityState={{

                selected,

                disabled,

            }}

            accessibilityLabel={title}

            disabled={disabled}

            onPress={onPress}

            style={({ pressed }) => [

                styles.card,

                {

                    borderColor,

                    backgroundColor,

                    opacity,

                },

                pressed &&
                    !disabled &&
                    styles.pressed,

                style,

            ]}

        >

            {/* -------------------------------------------------------------- */}
            {/* Left Section                                                  */}
            {/* -------------------------------------------------------------- */}

            <View

                style={styles.leftSection}

            >

                {!!icon && (

                    <View

                        style={styles.iconContainer}

                    >

                        {icon}

                    </View>

                )}

                <View

                    style={styles.content}

                >

                    <Text

                        numberOfLines={1}

                        style={styles.title}

                    >

                        {title}

                    </Text>

                    {!!carrier && (

                        <Text

                            numberOfLines={1}

                            style={styles.carrier}

                        >

                            {carrier}

                        </Text>

                    )}

                    {!!estimatedDelivery && (

                        <Text

                            numberOfLines={2}

                            style={styles.delivery}

                        >

                            {estimatedDelivery}

                        </Text>

                    )}

                </View>

            </View>

            {/* -------------------------------------------------------------- */}
            {/* Right Section                                                 */}
            {/* -------------------------------------------------------------- */}

            <View

                style={styles.rightSection}

            >

                <Text

                    style={[

                        styles.price,

                        freeShipping &&
                            styles.freePrice,

                    ]}

                >

                    {formattedPrice}

                </Text>

                {selected && (

                    <View

                        style={styles.selectedBadge}

                    >

                        <Text

                            style={styles.selectedText}

                        >

                            ✓

                        </Text>

                    </View>

                )}

            </View>

        </Pressable>

    );

});

/* -------------------------------------------------------------------------- */
/*                                    Styles                                  */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.surface ?? '#FFFFFF',
    borderRadius: radius.lg ?? 12,
    borderWidth: 1,
    borderColor: colors.border ?? '#E5E7EB',
    padding: spacing.md ?? 16,
    marginBottom: spacing.md ?? 16,
  },

  pressed: {
    opacity: 0.7,
  },

  /* ---------------------------------------------------------------------- */
  /* Left Section                                                           */
  /* ---------------------------------------------------------------------- */

  leftSection: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },

  iconContainer: {
    marginRight: spacing.md ?? 16,
    width: 40,
    height: 40,
    borderRadius: radius.md ?? 8,
    backgroundColor: colors.surfaceVariant ?? '#F3F4F6',
    alignItems: 'center',
    justifyContent: 'center',
  },

  content: {
    flex: 1,
  },

  title: {
    fontSize: typography.fontSize?.md ?? 16,
    fontWeight: typography.fontWeight?.semibold ?? '600',
    color: colors.text ?? '#1F2937',
    marginBottom: spacing.xs ?? 4,
  },

  carrier: {
    fontSize: typography.fontSize?.sm ?? 14,
    color: colors.textSecondary ?? '#6B7280',
    marginBottom: spacing.xs ?? 4,
  },

  delivery: {
    fontSize: typography.fontSize?.xs ?? 12,
    color: colors.textSecondary ?? '#6B7280',
  },

  /* ---------------------------------------------------------------------- */
  /* Right Section                                                          */
  /* ---------------------------------------------------------------------- */

  rightSection: {
    alignItems: 'flex-end',
    marginLeft: spacing.md ?? 16,
  },

  price: {
    fontSize: typography.fontSize?.md ?? 16,
    fontWeight: typography.fontWeight?.bold ?? '700',
    color: colors.primary ?? '#2563EB',
  },

  freePrice: {
    color: colors.success ?? '#10B981',
  },

  selectedBadge: {
    marginTop: spacing.xs ?? 4,
    width: 20,
    height: 20,
    borderRadius: radius.full ?? 999,
    backgroundColor: colors.primary ?? '#2563EB',
    alignItems: 'center',
    justifyContent: 'center',
  },

  selectedText: {
    color: colors.white ?? '#FFFFFF',
    fontSize: 12,
    fontWeight: 'bold',
  },
});

/* -------------------------------------------------------------------------- */
/*                              PropTypes & Export                            */
/* -------------------------------------------------------------------------- */

ShippingCard.propTypes = {
  /**
   * Shipping method title
   */
  title: PropTypes.string.isRequired,

  /**
   * Carrier name
   */
  carrier: PropTypes.string,

  /**
   * Estimated delivery date or timeframe
   */
  estimatedDelivery: PropTypes.string,

  /**
   * Shipping price
   */
  price: PropTypes.number,

  /**
   * Currency symbol
   */
  currency: PropTypes.string,

  /**
   * Whether shipping is free
   */
  freeShipping: PropTypes.bool,

  /**
   * Whether this option is selected
   */
  selected: PropTypes.bool,

  /**
   * Whether this option is disabled
   */
  disabled: PropTypes.bool,

  /**
   * Optional icon component
   */
  icon: PropTypes.node,

  /**
   * Called when card is pressed
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

ShippingCard.defaultProps = {
  carrier: null,
  estimatedDelivery: null,
  price: 0,
  currency: '₦',
  freeShipping: false,
  selected: false,
  disabled: false,
  icon: null,
  onPress: () => {},
  style: null,
};

export default memo(ShippingCard);