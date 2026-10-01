/* -------------------------------------------------------------------------- */
/*                           OrderPaymentCard.jsx                             */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from 'react';

import PropTypes from 'prop-types';

import {
  View,
  Text,
  StyleSheet,
} from 'react-native';

import {
  MaterialCommunityIcons,
} from '@expo/vector-icons';

import {
  colors,
  spacing,
  radius,
  typography,
} from '../../../theme';

import Money from '../common/Money';
import Badge from '../common/Badge';
import Divider from '../common/Divider';
import IconLabel from '../common/IconLabel';

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

function OrderPaymentCard({
  payment,
  currency,
  showBreakdown,
  showTransaction,
}) {
  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const paymentStatus = useMemo(() => {
    const status = payment?.status;

    switch (status) {
      case 'PAID':
        return { label: 'Paid', variant: 'success' };

      case 'PENDING':
        return { label: 'Pending', variant: 'warning' };

      case 'FAILED':
        return { label: 'Failed', variant: 'danger' };

      case 'REFUNDED':
        return { label: 'Refunded', variant: 'info' };

      case 'AUTHORIZED':
        return { label: 'Authorized', variant: 'info' };

      case 'PARTIALLY_REFUNDED':
        return { label: 'Partially Refunded', variant: 'warning' };

      case 'CANCELLED':
        return { label: 'Cancelled', variant: 'danger' };

      default:
        return { label: status || 'Unknown', variant: 'default' };
    }
  }, [payment]);

  const formattedPaidDate = useMemo(() => {
    if (!payment?.paidAt) return null;

    try {
      const date = new Date(payment.paidAt);
      if (Number.isNaN(date.getTime())) {
        return null;
      }
      return date.toLocaleString('en-GB');
    } catch {
      return null;
    }
  }, [payment?.paidAt]);

  if (!payment) {
    return null;
  }

  return (
    <View
      accessibilityRole="summary"
      accessibilityLabel="Payment information"
      style={styles.card}
    >
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                             */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <MaterialCommunityIcons
            name="credit-card-outline"
            size={22}
            color={colors.primary}
          />

          <Text style={styles.title}>
            Payment Information
          </Text>
        </View>

        <Badge
          label={paymentStatus.label}
          variant={paymentStatus.variant}
        />
      </View>

      <Divider />

      {/* ------------------------------------------------------------------ */}
      {/* Payment Method                                                     */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.section}>
        <IconLabel
          icon="wallet-outline"
          label="Payment Method"
          value={payment?.method || payment?.gateway || 'Unknown'}
        />

        {payment?.provider && (
          <IconLabel
            icon="domain"
            label="Provider"
            value={payment.provider}
            style={styles.infoItem}
          />
        )}

        {payment?.cardBrand && (
          <IconLabel
            icon="credit-card"
            label="Card"
            value={[
              payment.cardBrand,
              payment.last4 ? `•••• ${payment.last4}` : null,
            ]
              .filter(Boolean)
              .join(' ')}
            style={styles.infoItem}
          />
        )}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Transaction Details                                                */}
      {/* ------------------------------------------------------------------ */}

      {showTransaction && (
        <>
          <Divider />

          <View style={styles.section}>
            {payment?.transactionId && (
              <IconLabel
                icon="identifier"
                label="Transaction ID"
                value={payment.transactionId}
                style={styles.infoItem}
              />
            )}

            {payment?.reference && (
              <IconLabel
                icon="barcode"
                label="Reference"
                value={payment.reference}
                style={styles.infoItem}
              />
            )}

            {formattedPaidDate && (
              <IconLabel
                icon="calendar-check-outline"
                label="Paid On"
                value={formattedPaidDate}
                style={styles.infoItem}
              />
            )}
          </View>
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Price Breakdown                                                    */}
      {/* ------------------------------------------------------------------ */}

      {showBreakdown && (
        <>
          <Divider />

          <View style={styles.section}>
            <View style={styles.priceRow}>
              <Text style={styles.priceLabel}>Subtotal</Text>
              <Money
                amount={payment?.subtotal ?? 0}
                currency={currency}
                style={styles.priceValue}
              />
            </View>

            <View style={styles.priceRow}>
              <Text style={styles.priceLabel}>Shipping</Text>
              <Money
                amount={payment?.shipping ?? 0}
                currency={currency}
                style={styles.priceValue}
              />
            </View>

            <View style={styles.priceRow}>
              <Text style={styles.priceLabel}>Tax</Text>
              <Money
                amount={payment?.tax ?? 0}
                currency={currency}
                style={styles.priceValue}
              />
            </View>

            {(payment?.discount ?? 0) > 0 && (
              <View style={styles.priceRow}>
                <Text style={styles.discountLabel}>Discount</Text>
                <Money
                  amount={-Number(payment.discount)}
                  currency={currency}
                  style={styles.discountValue}
                />
              </View>
            )}

            <View style={styles.totalDivider} />

            <View style={styles.priceRow}>
              <Text style={styles.totalLabel}>Grand Total</Text>
              <Money
                amount={
                  payment?.total ??
                  (Number(payment?.subtotal ?? 0) +
                   Number(payment?.shipping ?? 0) +
                   Number(payment?.tax ?? 0) -
                   Number(payment?.discount ?? 0))
                }
                currency={currency}
                style={styles.totalValue}
              />
            </View>
          </View>
        </>
      )}
    </View>
  );
}

/* -------------------------------------------------------------------------- */
/*                                   Styles                                   */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.lg,

    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border || '#E5E7EB',
  },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },

  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },

  title: {
    marginLeft: spacing.sm,
    color: colors.text,
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
  },

  section: {
    marginTop: spacing.md,
  },

  infoItem: {
    marginTop: spacing.sm,
  },

  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: spacing.xs,
  },

  priceLabel: {
    color: colors.textSecondary,
    fontSize: typography.fontSize.md,
  },

  priceValue: {
    color: colors.text,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.medium,
  },

  discountLabel: {
    color: colors.success,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.medium,
  },

  discountValue: {
    color: colors.success,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.semibold,
  },

  totalDivider: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border || '#E5E7EB',
    marginVertical: spacing.md,
  },

  totalLabel: {
    color: colors.text,
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
  },

  totalValue: {
    color: colors.primary,
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
  },
});

/* -------------------------------------------------------------------------- */
/*                         PropTypes & Default Props                          */
/* -------------------------------------------------------------------------- */

OrderPaymentCard.propTypes = {
  /* ---------------------------------------------------------------------- */
  /* Payment                                                                */
  /* ---------------------------------------------------------------------- */

  payment: PropTypes.shape({
    /* Status */
    status: PropTypes.string,

    /* Method */
    method: PropTypes.string,
    gateway: PropTypes.string,
    provider: PropTypes.string,

    /* Card */
    cardBrand: PropTypes.string,
    last4: PropTypes.string,

    /* Transaction */
    transactionId: PropTypes.string,
    reference: PropTypes.string,
    paidAt: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.instanceOf(Date),
    ]),

    /* Pricing */
    subtotal: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    shipping: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    tax: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    discount: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    total: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),
  }),

  /* ---------------------------------------------------------------------- */
  /* Display                                                                */
  /* ---------------------------------------------------------------------- */

  currency: PropTypes.string,

  showBreakdown: PropTypes.bool,

  showTransaction: PropTypes.bool,
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

OrderPaymentCard.defaultProps = {
  payment: null,

  currency: 'NGN',

  showBreakdown: true,

  showTransaction: true,
};

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default memo(OrderPaymentCard);