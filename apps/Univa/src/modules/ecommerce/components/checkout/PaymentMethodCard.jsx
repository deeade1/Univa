/* -------------------------------------------------------------------------- */
/*                             PaymentMethodCard                              */
/* -------------------------------------------------------------------------- */

import React, { memo, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from 'react-native';

import { Ionicons } from '@expo/vector-icons';

import {
  colors,
  spacing,
  typography,
  radius,
} from '../../../theme';

/* -------------------------------------------------------------------------- */
/*                                Component                                   */
/* -------------------------------------------------------------------------- */

const PaymentMethodCard = ({
  method,
  selected,
  onPress,
  style,
  showDefaultBadge,
}) => {
  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const {
    type,
    name,
    brand,
    last4,
    holderName,
    expiry,
    icon: CustomIcon,
    isDefault,
    disabled,
  } = method;

  /**
   * Determine the icon to display.
   * A custom icon component takes precedence over the default icon.
   */
  const iconName = useMemo(() => {
    switch (type) {
      case 'card':
        return 'card-outline';

      case 'wallet':
        return 'wallet-outline';

      case 'bank':
        return 'business-outline';

      case 'paypal':
        return 'logo-paypal';

      case 'cash':
        return 'cash-outline';

      default:
        return 'wallet-outline';
    }
  }, [type]);

  /**
   * Primary title shown on the card.
   */
  const title = useMemo(
    () => brand || name || 'Payment Method',
    [brand, name]
  );

  /**
   * Secondary description.
   */
  const subtitle = useMemo(() => {
    switch (type) {
      case 'card':
        return last4
          ? `•••• •••• •••• ${last4}`
          : 'Saved Card';

      case 'wallet':
        return 'Wallet Balance';

      case 'bank':
        return holderName || 'Bank Account';

      case 'paypal':
        return holderName || 'PayPal Account';

      case 'cash':
        return 'Pay on Delivery';

      default:
        return '';
    }
  }, [
    type,
    last4,
    holderName,
  ]);

  /**
   * Additional information displayed beneath the subtitle.
   */
  const footerText = useMemo(() => {
    if (type === 'card' && expiry) {
      return `Exp: ${expiry}`;
    }

    if (
      (type === 'bank' || type === 'paypal') &&
      holderName
    ) {
      return holderName;
    }

    return '';
  }, [
    type,
    expiry,
    holderName,
  ]);
    /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <Pressable
      onPress={() => !disabled && onPress(method)}
      disabled={disabled}
      style={({ pressed }) => [
        styles.card,
        selected && styles.selectedCard,
        disabled && styles.disabledCard,
        pressed && !disabled && styles.pressedCard,
        style,
      ]}
    >
      {/* ------------------------------------------------------------------ */}
      {/* Left Section                                                       */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.leftSection}>
        <View
          style={[
            styles.radioOuter,
            selected && styles.radioOuterSelected,
          ]}
        >
          {selected && <View style={styles.radioInner} />}
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Payment Icon                                                       */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.iconContainer}>
        {CustomIcon ? (
          <CustomIcon
            width={24}
            height={24}
          />
        ) : (
          <Ionicons
            name={iconName}
            size={24}
            color={colors.primary}
          />
        )}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Payment Details                                                    */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.content}>
        <View style={styles.headerRow}>
          <Text
            style={styles.title}
            numberOfLines={1}
          >
            {title}
          </Text>

          {showDefaultBadge && isDefault && (
            <View style={styles.defaultBadge}>
              <Text style={styles.defaultBadgeText}>
                DEFAULT
              </Text>
            </View>
          )}
        </View>

        {!!subtitle && (
          <Text
            style={styles.subtitle}
            numberOfLines={1}
          >
            {subtitle}
          </Text>
        )}

        {!!footerText && (
          <Text
            style={styles.footerText}
            numberOfLines={1}
          >
            {footerText}
          </Text>
        )}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Selected Indicator                                                 */}
      {/* ------------------------------------------------------------------ */}

      {selected && (
        <View style={styles.checkContainer}>
          <Ionicons
            name="checkmark-circle"
            size={22}
            color={colors.primary}
          />
        </View>
      )}
    </Pressable>
  );
}
/* -------------------------------------------------------------------------- */
/*                                    Styles                                  */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
  },

  selectedCard: {
    borderColor: colors.primary,
    backgroundColor: colors.primaryLight || '#F4F9FF',
  },

  pressedCard: {
    opacity: 0.85,
  },

  disabledCard: {
    opacity: 0.6,
  },

  /* ---------------------------------------------------------------------- */
  /* Selection Indicator                                                    */
  /* ---------------------------------------------------------------------- */

  leftSection: {
    marginRight: spacing.md,
    justifyContent: 'center',
    alignItems: 'center',
  },

  radioOuter: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colors.borderDark || colors.gray400,
    justifyContent: 'center',
    alignItems: 'center',
  },

  radioOuterSelected: {
    borderColor: colors.primary,
  },

  radioInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary,
  },

  /* ---------------------------------------------------------------------- */
  /* Payment Icon                                                           */
  /* ---------------------------------------------------------------------- */

  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.primaryLight || '#EEF6FF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.md,
  },

  /* ---------------------------------------------------------------------- */
  /* Content                                                                */
  /* ---------------------------------------------------------------------- */

  content: {
    flex: 1,
    justifyContent: 'center',
  },

  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },

  title: {
    flex: 1,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text,
    marginRight: spacing.sm,
  },

  subtitle: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  footerText: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.xs,
    color: colors.textSecondary,
  },

  /* ---------------------------------------------------------------------- */
  /* Default Badge                                                          */
  /* ---------------------------------------------------------------------- */

  defaultBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.full || 999,
    backgroundColor: colors.successLight || '#ECFDF5',
  },

  defaultBadgeText: {
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.bold,
    color: colors.success,
    letterSpacing: 0.5,
  },

  /* ---------------------------------------------------------------------- */
  /* Selected Check                                                         */
  /* ---------------------------------------------------------------------- */

  checkContainer: {
    marginLeft: spacing.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
/* -------------------------------------------------------------------------- */
/*                              PropTypes & Export                            */
/* -------------------------------------------------------------------------- */

PaymentMethodCard.propTypes = {
  /**
   * Payment method object.
   */
  method: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]).isRequired,

    /**
     * card | wallet | bank | paypal | cash
     */
    type: PropTypes.oneOf([
      'card',
      'wallet',
      'bank',
      'paypal',
      'cash',
    ]).isRequired,

    name: PropTypes.string,
    brand: PropTypes.string,
    last4: PropTypes.string,
    holderName: PropTypes.string,
    expiry: PropTypes.string,

    /**
     * Optional custom icon component.
     */
    icon: PropTypes.elementType,

    /**
     * Whether this is the default payment method.
     */
    isDefault: PropTypes.bool,

    /**
     * Whether the payment method is disabled.
     */
    disabled: PropTypes.bool,
  }).isRequired,

  /**
   * Whether this payment method is selected.
   */
  selected: PropTypes.bool,

  /**
   * Called when the card is pressed.
   */
  onPress: PropTypes.func,

  /**
   * Show the "DEFAULT" badge.
   */
  showDefaultBadge: PropTypes.bool,

  /**
   * Optional style overrides.
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

PaymentMethodCard.defaultProps = {
  selected: false,
  onPress: () => {},
  showDefaultBadge: true,
  style: null,
};

export default memo(PaymentMethodCard);