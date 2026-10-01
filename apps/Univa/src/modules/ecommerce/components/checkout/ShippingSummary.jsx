/* -------------------------------------------------------------------------- */
/*                              ShippingSummary                               */
/* -------------------------------------------------------------------------- */

import React, { memo, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  View,
  Text,
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
/*                              Component                                     */
/* -------------------------------------------------------------------------- */

const ShippingSummary = ({
  shippingMethod,
  subtotal,
  currencySymbol,
  destination,
  showDestination,
  title,
  freeLabel,
}) => {
  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const shippingCost = useMemo(
    () => Number(shippingMethod?.price ?? 0),
    [shippingMethod]
  );

  const total = useMemo(
    () => Number(subtotal) + shippingCost,
    [subtotal, shippingCost]
  );

  const formattedSubtotal = useMemo(
    () => `${currencySymbol}${Number(subtotal).toFixed(2)}`,
    [currencySymbol, subtotal]
  );

  const formattedShipping = useMemo(
    () =>
      shippingCost <= 0
        ? freeLabel
        : `${currencySymbol}${shippingCost.toFixed(2)}`,
    [currencySymbol, shippingCost, freeLabel]
  );

  const formattedTotal = useMemo(
    () => `${currencySymbol}${total.toFixed(2)}`,
    [currencySymbol, total]
  );
    /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>

      {shippingMethod ? (
        <>
          {/* -------------------------------------------------------------- */}
          {/* Selected Shipping Method                                      */}
          {/* -------------------------------------------------------------- */}

          <View style={styles.methodCard}>
            <View style={styles.iconContainer}>
              <Ionicons
                name="car-outline"
                size={22}
                color={colors.primary}
              />
            </View>

            <View style={styles.methodContent}>
              <Text style={styles.methodName}>
                {shippingMethod.name}
              </Text>

              {!!shippingMethod.description && (
                <Text style={styles.description}>
                  {shippingMethod.description}
                </Text>
              )}

              {!!shippingMethod.estimatedDays && (
                <Text style={styles.eta}>
                  Delivery: {shippingMethod.estimatedDays}
                </Text>
              )}

              {showDestination && !!destination && (
                <Text style={styles.destination}>
                  Destination: {destination}
                </Text>
              )}
            </View>

            <View style={styles.priceContainer}>
              <Text
                style={[
                  styles.shippingPrice,
                  shippingCost <= 0 && styles.freeText,
                ]}
              >
                {formattedShipping}
              </Text>
            </View>
          </View>

          {/* -------------------------------------------------------------- */}
          {/* Cost Breakdown                                                 */}
          {/* -------------------------------------------------------------- */}

          <View style={styles.summarySection}>
            <View style={styles.summaryRow}>
              <Text style={styles.label}>Items</Text>
              <Text style={styles.value}>
                {formattedSubtotal}
              </Text>
            </View>

            <View style={styles.summaryRow}>
              <Text style={styles.label}>Shipping</Text>
              <Text
                style={[
                  styles.value,
                  shippingCost <= 0 && styles.freeText,
                ]}
              >
                {formattedShipping}
              </Text>
            </View>

            <View style={styles.divider} />

            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Total</Text>
              <Text style={styles.totalValue}>
                {formattedTotal}
              </Text>
            </View>
          </View>
        </>
      ) : (
        <View style={styles.emptyContainer}>
          <Ionicons
            name="car-outline"
            size={32}
            color={colors.textSecondary}
          />

          <Text style={styles.emptyTitle}>
            No shipping method selected
          </Text>

          <Text style={styles.emptyDescription}>
            Choose a shipping option to view the delivery
            estimate and order total.
          </Text>
        </View>
      )}
    </View>
  );
}
/* -------------------------------------------------------------------------- */
/*                                    Styles                                  */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
  },

  /* ---------------------------------------------------------------------- */
  /* Header                                                                 */
  /* ---------------------------------------------------------------------- */

  title: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
    marginBottom: spacing.lg,
  },

  /* ---------------------------------------------------------------------- */
  /* Shipping Method Card                                                   */
  /* ---------------------------------------------------------------------- */

  methodCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.surface || '#F8FAFC',
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },

  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.primaryLight || '#EEF6FF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.md,
  },

  methodContent: {
    flex: 1,
  },

  methodName: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text,
  },

  description: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
    lineHeight: 20,
  },

  eta: {
    marginTop: spacing.sm,
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  destination: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  priceContainer: {
    justifyContent: 'center',
    alignItems: 'flex-end',
    marginLeft: spacing.md,
  },

  shippingPrice: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary,
  },

  freeText: {
    color: colors.success,
  },

  /* ---------------------------------------------------------------------- */
  /* Summary                                                                */
  /* ---------------------------------------------------------------------- */

  summarySection: {
    marginTop: spacing.sm,
  },

  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },

  label: {
    fontSize: typography.fontSize.md,
    color: colors.textSecondary,
  },

  value: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.medium,
    color: colors.text,
  },

  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.border,
    marginVertical: spacing.md,
  },

  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },

  totalLabel: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
  },

  totalValue: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary,
  },

  /* ---------------------------------------------------------------------- */
  /* Empty State                                                            */
  /* ---------------------------------------------------------------------- */

  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl,
  },

  emptyTitle: {
    marginTop: spacing.md,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text,
    textAlign: 'center',
  },

  emptyDescription: {
    marginTop: spacing.sm,
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: spacing.lg,
  },
});
/* -------------------------------------------------------------------------- */
/*                              PropTypes & Export                            */
/* -------------------------------------------------------------------------- */

ShippingSummary.propTypes = {
  /**
   * Selected shipping method.
   */
  shippingMethod: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),
    name: PropTypes.string.isRequired,
    description: PropTypes.string,
    price: PropTypes.number,
    estimatedDays: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),
    badge: PropTypes.string,
    icon: PropTypes.elementType,
  }),

  /**
   * Cart subtotal (before shipping).
   */
  subtotal: PropTypes.number,

  /**
   * Currency symbol used for prices.
   */
  currencySymbol: PropTypes.string,

  /**
   * Shipping destination.
   */
  destination: PropTypes.string,

  /**
   * Whether to display the destination.
   */
  showDestination: PropTypes.bool,

  /**
   * Section heading.
   */
  title: PropTypes.string,

  /**
   * Label displayed when shipping is free.
   */
  freeLabel: PropTypes.string,
};

ShippingSummary.defaultProps = {
  shippingMethod: null,
  subtotal: 0,
  currencySymbol: '$',
  destination: '',
  showDestination: false,
  title: 'Shipping Summary',
  freeLabel: 'Free',
};

export default memo(ShippingSummary);