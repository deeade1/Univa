/* -------------------------------------------------------------------------- */
/*                                OrderSummary                                */
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
} from '@/theme';

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const safeNumber = (value) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
};

/* -------------------------------------------------------------------------- */
/*                                Component                                   */
/* -------------------------------------------------------------------------- */

const OrderSummary = ({
  subtotal,
  shipping,
  discount,
  tax,
  itemCount,
  currencySymbol,
  couponCode,
  showTax,
  showCoupon,
  title,
  freeLabel,
  style,
}) => {
  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const subtotalAmount = useMemo(
    () => safeNumber(subtotal),
    [subtotal]
  );

  const shippingAmount = useMemo(
    () => safeNumber(shipping),
    [shipping]
  );

  const discountAmount = useMemo(
    () => safeNumber(discount),
    [discount]
  );

  const taxAmount = useMemo(
    () => safeNumber(tax),
    [tax]
  );

  const totalAmount = useMemo(
    () =>
      subtotalAmount +
      shippingAmount +
      (showTax ? taxAmount : 0) -
      discountAmount,
    [
      subtotalAmount,
      shippingAmount,
      taxAmount,
      discountAmount,
      showTax,
    ]
  );

  /* ---------------------------------------------------------------------- */
  /* Formatted Values                                                       */
  /* ---------------------------------------------------------------------- */

  const formattedSubtotal = useMemo(
    () => `${currencySymbol}${subtotalAmount.toFixed(2)}`,
    [currencySymbol, subtotalAmount]
  );

  const formattedShipping = useMemo(
    () =>
      shippingAmount <= 0
        ? freeLabel
        : `${currencySymbol}${shippingAmount.toFixed(2)}`,
    [
      currencySymbol,
      shippingAmount,
      freeLabel,
    ]
  );

  const formattedDiscount = useMemo(
    () => `-${currencySymbol}${discountAmount.toFixed(2)}`,
    [
      currencySymbol,
      discountAmount,
    ]
  );

  const formattedTax = useMemo(
    () => `${currencySymbol}${taxAmount.toFixed(2)}`,
    [
      currencySymbol,
      taxAmount,
    ]
  );

  const formattedTotal = useMemo(
    () => `${currencySymbol}${totalAmount.toFixed(2)}`,
    [
      currencySymbol,
      totalAmount,
    ]
  );

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View
      style={[
        styles.container,
        style,
      ]}
    >
      <Text style={styles.title}>{title}</Text>

      {/* ------------------------------------------------------------------ */}
      {/* Pricing Breakdown                                                  */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.summarySection}>
        <View style={styles.summaryRow}>
          <Text style={styles.label}>
            Items
            {itemCount > 0 ? ` (${itemCount})` : ''}
          </Text>

          <Text style={styles.value}>
            {formattedSubtotal}
          </Text>
        </View>

        <View style={styles.summaryRow}>
          <Text style={styles.label}>Shipping</Text>

          <Text
            style={[
              styles.value,
              shippingAmount <= 0 && styles.freeText,
            ]}
          >
            {formattedShipping}
          </Text>
        </View>

        {discountAmount > 0 && (
          <View style={styles.summaryRow}>
            <Text style={styles.discountLabel}>
              Discount
            </Text>

            <Text style={styles.discountValue}>
              {formattedDiscount}
            </Text>
          </View>
        )}

        {showTax && (
          <View style={styles.summaryRow}>
            <Text style={styles.label}>Tax</Text>

            <Text style={styles.value}>
              {formattedTax}
            </Text>
          </View>
        )}

        <View style={styles.divider} />

        {/* ---------------------------------------------------------------- */}
        {/* Grand Total                                                      */}
        {/* ---------------------------------------------------------------- */}

        <View style={styles.totalRow}>
          <Text style={styles.totalLabel}>
            Total
          </Text>

          <Text style={styles.totalValue}>
            {formattedTotal}
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Applied Coupon                                                     */}
      {/* ------------------------------------------------------------------ */}

      {showCoupon && !!couponCode && (
        <>
          <View style={styles.divider} />

          <View style={styles.couponContainer}>
            <View style={styles.couponLeft}>
              <Ionicons
                name="pricetag-outline"
                size={18}
                color={colors.success}
              />

              <Text style={styles.couponLabel}>
                Coupon Applied
              </Text>
            </View>

            <View style={styles.couponRight}>
              <Text style={styles.couponCode}>
                {couponCode}
              </Text>

              <Ionicons
                name="checkmark-circle"
                size={18}
                color={colors.success}
              />
            </View>
          </View>
        </>
      )}
    </View>
  );
};

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
  /* Summary                                                                */
  /* ---------------------------------------------------------------------- */

  summarySection: {
    width: '100%',
  },

  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },

  label: {
    flex: 1,
    fontSize: typography.fontSize.md,
    color: colors.textSecondary,
  },

  value: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.medium,
    color: colors.text,
    textAlign: 'right',
  },

  /* ---------------------------------------------------------------------- */
  /* Discount                                                               */
  /* ---------------------------------------------------------------------- */

  discountLabel: {
    flex: 1,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.medium,
    color: colors.success,
  },

  discountValue: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.medium,
    color: colors.success,
    textAlign: 'right',
  },

  freeText: {
    color: colors.success,
    fontWeight: typography.fontWeight.medium,
  },

  /* ---------------------------------------------------------------------- */
  /* Divider                                                                */
  /* ---------------------------------------------------------------------- */

  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.border,
    marginVertical: spacing.md,
  },

  /* ---------------------------------------------------------------------- */
  /* Total                                                                  */
  /* ---------------------------------------------------------------------- */

  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: spacing.xs,
  },

  totalLabel: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
  },

  totalValue: {
    fontSize: typography.fontSize.xl,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary,
  },

  /* ---------------------------------------------------------------------- */
  /* Coupon                                                                 */
  /* ---------------------------------------------------------------------- */

  couponContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.successLight || '#F0FDF4',
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },

  couponLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },

  couponLabel: {
    marginLeft: spacing.sm,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.success,
  },

  couponRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },

  couponCode: {
    marginRight: spacing.xs,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    color: colors.success,
    textTransform: 'uppercase',
  },
});

/* -------------------------------------------------------------------------- */
/*                              PropTypes & Export                            */
/* -------------------------------------------------------------------------- */

OrderSummary.propTypes = {
  /**
   * Cart subtotal before shipping, discounts and taxes.
   */
  subtotal: PropTypes.oneOfType([
    PropTypes.number,
    PropTypes.string,
  ]),

  /**
   * Shipping cost.
   */
  shipping: PropTypes.oneOfType([
    PropTypes.number,
    PropTypes.string,
  ]),

  /**
   * Discount amount.
   */
  discount: PropTypes.oneOfType([
    PropTypes.number,
    PropTypes.string,
  ]),

  /**
   * Tax amount.
   */
  tax: PropTypes.oneOfType([
    PropTypes.number,
    PropTypes.string,
  ]),

  /**
   * Number of items in the cart.
   */
  itemCount: PropTypes.number,

  /**
   * Currency symbol displayed before all prices.
   */
  currencySymbol: PropTypes.string,

  /**
   * Applied coupon code.
   */
  couponCode: PropTypes.string,

  /**
   * Whether to display the tax row.
   */
  showTax: PropTypes.bool,

  /**
   * Whether to display the applied coupon section.
   */
  showCoupon: PropTypes.bool,

  /**
   * Card title.
   */
  title: PropTypes.string,

  /**
   * Label used when shipping is free.
   */
  freeLabel: PropTypes.string,

  /**
   * Optional container style.
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

OrderSummary.defaultProps = {
  subtotal: 0,
  shipping: 0,
  discount: 0,
  tax: 0,
  itemCount: 0,
  currencySymbol: '₦',
  couponCode: '',
  showTax: false,
  showCoupon: true,
  title: 'Order Summary',
  freeLabel: 'Free',
  style: null,
};

export default memo(OrderSummary);