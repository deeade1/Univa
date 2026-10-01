/* -------------------------------------------------------------------------- */
/*                         OrderConfirmationCard                              */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from 'react';

import PropTypes from 'prop-types';

import {
  View,
  Text,
  StyleSheet,
} from 'react-native';

import { Ionicons } from '@expo/vector-icons';

import Button from '../../common/Button';

import {
  colors,
  spacing,
  typography,
  radius,
} from '../../../theme';

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const SUCCESS_STATUSES = new Set([
  'CONFIRMED',
  'PROCESSING',
  'SHIPPED',
  'DELIVERED',
  'COMPLETED',
]);

/* -------------------------------------------------------------------------- */
/*                                Component                                   */
/* -------------------------------------------------------------------------- */

const OrderConfirmationCard = ({
  order,
  onTrackOrder,
  onContinueShopping,
  loading,
}) => {
  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const isSuccessful = useMemo(
    () => order?.status && SUCCESS_STATUSES.has(order.status),
    [order?.status]
  );

  const isPaymentPending = useMemo(
    () => order?.paymentStatus === 'PENDING',
    [order?.paymentStatus]
  );

  const statusTitle = useMemo(() => {
    if (isSuccessful && !isPaymentPending) {
      return 'Order Confirmed!';
    }

    if (isPaymentPending) {
      return 'Payment Processing';
    }

    return 'Order Received';
  }, [isSuccessful, isPaymentPending]);

  const statusMessage = useMemo(() => {
    if (isSuccessful && !isPaymentPending) {
      return 'Your order has been placed successfully.';
    }

    if (isPaymentPending) {
      return 'Your order was received, but payment confirmation is pending.';
    }

    return 'We have received your order and are processing it.';
  }, [isSuccessful, isPaymentPending]);

  const formattedTotal = useMemo(() => {
    if (order?.total == null) {
      return '₦0';
    }

    const total = typeof order.total === 'string'
      ? parseFloat(order.total)
      : order.total;

    if (isNaN(total)) {
      return '₦0';
    }

    const currency = order.currency || 'NGN';

    // Use currencySymbol if provided, otherwise fallback to symbol lookup
    const symbol = order.currencySymbol ||
      (currency === 'NGN' ? '₦' : '');

    try {
      return new Intl.NumberFormat('en-NG', {
        style: 'currency',
        currency,
        minimumFractionDigits: 0,
      }).format(total);
    } catch {
      // Fallback if currency is not supported
      return `${symbol}${total.toLocaleString()}`;
    }
  }, [
    order?.total,
    order?.currency,
    order?.currencySymbol,
  ]);

  const formattedDate = useMemo(() => {
    if (!order?.createdAt) return null;

    try {
      const date = new Date(order.createdAt);

      if (Number.isNaN(date.getTime())) {
        return order.createdAt;
      }

      return date.toLocaleDateString('en-NG', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return order.createdAt;
    }
  }, [order?.createdAt]);

  const statusIcon = isSuccessful ? 'checkmark' : 'time-outline';
  const statusColor = isSuccessful ? colors.success : colors.warning;
  const iconContainerStyle = isSuccessful
    ? styles.successIconContainer
    : styles.pendingIconContainer;

  /* ---------------------------------------------------------------------- */
  /* Handlers                                                               */
  /* ---------------------------------------------------------------------- */

  const handleTrackOrder = useCallback(() => {
    if (!loading) {
      onTrackOrder?.(order);
    }
  }, [loading, onTrackOrder, order]);

  const handleContinueShopping = useCallback(() => {
    if (!loading) {
      onContinueShopping?.();
    }
  }, [loading, onContinueShopping]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View style={styles.container}>
      {/* ------------------------------------------------------------------ */}
      {/* Status Icon                                                        */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.iconContainer,
          iconContainerStyle,
        ]}
      >
        <Ionicons
          name={statusIcon}
          size={42}
          color={statusColor}
        />
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Status Message                                                     */}
      {/* ------------------------------------------------------------------ */}

      <Text style={styles.title}>
        {statusTitle}
      </Text>

      <Text style={styles.message}>
        {statusMessage}
      </Text>

      {/* ------------------------------------------------------------------ */}
      {/* Order Details                                                      */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.detailsContainer}>
        {/* Order Number */}
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>
            Order Number
          </Text>

          <Text style={styles.detailValue}>
            {order?.orderNumber || '-'}
          </Text>
        </View>

        {/* Order Date */}
        {!!formattedDate && (
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>
              Order Date
            </Text>

            <Text style={styles.detailValue}>
              {formattedDate}
            </Text>
          </View>
        )}

        {/* Payment Status */}
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>
            Payment
          </Text>

          <Text
            style={[
              styles.detailValue,
              isPaymentPending && styles.pendingText,
              !isPaymentPending && isSuccessful && styles.successText,
            ]}
          >
            {order?.paymentStatus || 'UNKNOWN'}
          </Text>
        </View>

        {/* Payment Method */}
        {!!order?.paymentMethod && (
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>
              Payment Method
            </Text>

            <Text style={styles.detailValue}>
              {order.paymentMethod}
            </Text>
          </View>
        )}

        {/* Delivery Estimate */}
        {!!(order?.deliveryEstimate || order?.estimatedDelivery) && (
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>
              Delivery
            </Text>

            <Text style={styles.detailValue}>
              {order.deliveryEstimate || order.estimatedDelivery}
            </Text>
          </View>
        )}

        {/* Tracking Number */}
        {!!order?.trackingNumber && (
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>
              Tracking Number
            </Text>

            <Text style={styles.detailValue}>
              {order.trackingNumber}
            </Text>
          </View>
        )}

        {/* Total */}
        <View style={styles.totalRow}>
          <Text style={styles.totalLabel}>
            Total Paid
          </Text>

          <Text style={styles.totalValue}>
            {formattedTotal}
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Actions                                                            */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.actions}>
        <Button
          title="Track Order"
          onPress={handleTrackOrder}
          loading={loading}
          style={styles.primaryButton}
          accessibilityLabel="Track this order"
        />

        <Button
          title="Continue Shopping"
          variant="outline"
          onPress={handleContinueShopping}
          disabled={loading}
          style={styles.secondaryButton}
          accessibilityLabel="Continue shopping"
        />
      </View>
    </View>
  );
};

/* -------------------------------------------------------------------------- */
/*                                    Styles                                  */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  /* ---------------------------------------------------------------------- */
  /* Container                                                              */
  /* ---------------------------------------------------------------------- */

  container: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.xl,
    alignItems: 'center',
  },

  /* ---------------------------------------------------------------------- */
  /* Status Icon                                                            */
  /* ---------------------------------------------------------------------- */

  iconContainer: {
    width: 84,
    height: 84,
    borderRadius: 42,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },

  successIconContainer: {
    backgroundColor: colors.successLight || '#ECFDF5',
  },

  pendingIconContainer: {
    backgroundColor: colors.warningLight || '#FFFBEB',
  },

  /* ---------------------------------------------------------------------- */
  /* Title & Message                                                        */
  /* ---------------------------------------------------------------------- */

  title: {
    fontSize: typography.fontSize.xl,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
    textAlign: 'center',
  },

  message: {
    marginTop: spacing.sm,
    fontSize: typography.fontSize.md,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: spacing.md,
  },

  /* ---------------------------------------------------------------------- */
  /* Details                                                                */
  /* ---------------------------------------------------------------------- */

  detailsContainer: {
    width: '100%',
    marginTop: spacing.xl,
    borderRadius: radius.md,
    backgroundColor: colors.background || '#F8FAFC',
    padding: spacing.lg,
  },

  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },

  detailLabel: {
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  detailValue: {
    maxWidth: '60%',
    textAlign: 'right',
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text,
  },

  successText: {
    color: colors.success,
  },

  pendingText: {
    color: colors.warning,
  },

  /* ---------------------------------------------------------------------- */
  /* Total                                                                  */
  /* ---------------------------------------------------------------------- */

  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.sm,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },

  totalLabel: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text,
  },

  totalValue: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary,
  },

  /* ---------------------------------------------------------------------- */
  /* Actions                                                                */
  /* ---------------------------------------------------------------------- */

  actions: {
    width: '100%',
    marginTop: spacing.xl,
  },

  primaryButton: {
    width: '100%',
  },

  secondaryButton: {
    width: '100%',
    marginTop: spacing.md,
  },
});

/* -------------------------------------------------------------------------- */
/*                              PropTypes & Export                            */
/* -------------------------------------------------------------------------- */

OrderConfirmationCard.propTypes = {
  /**
   * Created order information.
   */
  order: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    orderNumber: PropTypes.string,

    status: PropTypes.string,

    paymentStatus: PropTypes.string,

    paymentMethod: PropTypes.string,

    total: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    currency: PropTypes.string,

    currencySymbol: PropTypes.string,

    deliveryEstimate: PropTypes.string,

    estimatedDelivery: PropTypes.string,

    trackingNumber: PropTypes.string,

    createdAt: PropTypes.string,
  }),

  /**
   * Track order callback.
   */
  onTrackOrder: PropTypes.func,

  /**
   * Continue shopping callback.
   */
  onContinueShopping: PropTypes.func,

  /**
   * Action loading state.
   */
  loading: PropTypes.bool,
};

OrderConfirmationCard.defaultProps = {
  order: null,

  onTrackOrder: null,

  onContinueShopping: null,

  loading: false,
};

export default memo(OrderConfirmationCard);