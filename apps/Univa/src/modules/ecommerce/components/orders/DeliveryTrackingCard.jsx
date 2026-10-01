/* -------------------------------------------------------------------------- */
/*                         DeliveryTrackingCard                               */
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

const STATUS_CONFIG = {
  DELIVERED: {
    label: 'Delivered',
    color: colors.success,
    icon: 'checkmark-circle',
  },
  OUT_FOR_DELIVERY: {
    label: 'Out for Delivery',
    color: colors.primary,
    icon: 'bicycle',
  },
  IN_TRANSIT: {
    label: 'In Transit',
    color: colors.warning,
    icon: 'airplane',
  },
  PROCESSING: {
    label: 'Processing',
    color: colors.info || colors.primary,
    icon: 'time',
  },
  PENDING: {
    label: 'Pending',
    color: colors.textSecondary,
    icon: 'clock',
  },
  SHIPPED: {
    label: 'Shipped',
    color: colors.primary,
    icon: 'cube',
  },
};

const DEFAULT_STATUS = {
  label: 'Unknown',
  color: colors.textSecondary,
  icon: 'help-circle',
};

/* -------------------------------------------------------------------------- */
/*                                Component                                   */
/* -------------------------------------------------------------------------- */

const DeliveryTrackingCard = ({
  delivery,
  onTrackShipment,
  loading,
  style,
}) => {
  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const trackingNumber = useMemo(
    () => delivery?.trackingNumber || 'Not Available',
    [delivery]
  );

  const courierName = useMemo(
    () => delivery?.courier?.name || 'Unknown Courier',
    [delivery]
  );

  const deliveryStatus = useMemo(
    () => delivery?.status || 'PENDING',
    [delivery]
  );

  const statusConfig = useMemo(
    () => STATUS_CONFIG[deliveryStatus] || DEFAULT_STATUS,
    [deliveryStatus]
  );

  const estimatedDelivery = useMemo(() => {
    if (!delivery?.estimatedDelivery) {
      return null;
    }

    try {
      const date = new Date(delivery.estimatedDelivery);

      if (!Number.isNaN(date.getTime())) {
        const now = new Date();
        const isThisYear = date.getFullYear() === now.getFullYear();

        return date.toLocaleDateString('en-NG', {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
          ...(isThisYear ? {} : { year: 'numeric' }),
        });
      }

      return delivery.estimatedDelivery;
    } catch {
      return delivery.estimatedDelivery;
    }
  }, [delivery]);

  const hasTrackingNumber = useMemo(
    () => !!delivery?.trackingNumber && delivery.trackingNumber !== 'Not Available',
    [delivery]
  );

  /* ---------------------------------------------------------------------- */
  /* Handlers                                                               */
  /* ---------------------------------------------------------------------- */

  const handleTrackShipment = useCallback(() => {
    if (!loading && onTrackShipment) {
      onTrackShipment(delivery);
    }
  }, [loading, onTrackShipment, delivery]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View style={[styles.container, style]}>
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                             */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Ionicons
            name="cube-outline"
            size={22}
            color={colors.primary}
          />

          <Text style={styles.title}>
            Delivery Tracking
          </Text>
        </View>

        <View
          style={[
            styles.statusBadge,
            {
              backgroundColor: statusConfig.color + '20',
            },
          ]}
        >
          <Text
            style={[
              styles.statusText,
              {
                color: statusConfig.color,
              },
            ]}
          >
            {statusConfig.label}
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Tracking Information                                               */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.infoContainer}>
        <View style={styles.infoRow}>
          <Text style={styles.label}>
            Tracking Number
          </Text>

          <Text style={styles.value}>
            {trackingNumber}
          </Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.label}>
            Courier
          </Text>

          <Text style={styles.value}>
            {courierName}
          </Text>
        </View>

        {!!estimatedDelivery && (
          <View style={styles.infoRow}>
            <Text style={styles.label}>
              Estimated Delivery
            </Text>

            <Text style={styles.value}>
              {estimatedDelivery}
            </Text>
          </View>
        )}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Delivery Timeline                                                  */}
      {/* ------------------------------------------------------------------ */}

      {!!delivery?.timeline?.length && (
        <View style={styles.timelineContainer}>
          <Text style={styles.sectionTitle}>
            Delivery Progress
          </Text>

          {delivery.timeline.map((item, index) => {
            const isLast = index === delivery.timeline.length - 1;

            return (
              <View
                key={`${item.title}-${index}`}
                style={styles.timelineRow}
              >
                <View style={styles.timelineIndicator}>
                  <View
                    style={[
                      styles.timelineDot,
                      item.completed && styles.timelineDotCompleted,
                    ]}
                  >
                    {item.completed && (
                      <Ionicons
                        name="checkmark"
                        size={10}
                        color={colors.white}
                      />
                    )}
                  </View>

                  {!isLast && (
                    <View
                      style={[
                        styles.timelineLine,
                        item.completed && styles.timelineLineCompleted,
                      ]}
                    />
                  )}
                </View>

                <View style={styles.timelineContent}>
                  <Text
                    style={[
                      styles.timelineTitle,
                      item.completed && styles.timelineTitleCompleted,
                    ]}
                  >
                    {item.title}
                  </Text>

                  {!!item.date && (
                    <Text style={styles.timelineDate}>
                      {item.date}
                    </Text>
                  )}
                </View>
              </View>
            );
          })}
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Actions                                                            */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.actions}>
        <Button
          title={hasTrackingNumber ? 'Track Shipment' : 'Request Tracking'}
          onPress={handleTrackShipment}
          loading={loading}
          disabled={!hasTrackingNumber}
          style={styles.trackButton}
          accessibilityLabel={
            hasTrackingNumber
              ? 'Track shipment'
              : 'Request tracking information'
          }
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
  /* Card                                                                   */
  /* ---------------------------------------------------------------------- */

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

  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },

  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },

  title: {
    marginLeft: spacing.sm,
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
  },

  statusBadge: {
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },

  statusText: {
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.bold,
    letterSpacing: 0.5,
  },

  /* ---------------------------------------------------------------------- */
  /* Tracking Info                                                          */
  /* ---------------------------------------------------------------------- */

  infoContainer: {
    marginBottom: spacing.lg,
  },

  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },

  label: {
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  value: {
    flex: 1,
    marginLeft: spacing.md,
    textAlign: 'right',
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
    color: colors.text,
  },

  /* ---------------------------------------------------------------------- */
  /* Timeline                                                               */
  /* ---------------------------------------------------------------------- */

  timelineContainer: {
    marginTop: spacing.sm,
    marginBottom: spacing.lg,
    paddingTop: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },

  sectionTitle: {
    marginBottom: spacing.lg,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
  },

  timelineRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },

  timelineIndicator: {
    width: 28,
    alignItems: 'center',
  },

  timelineDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.white,
    justifyContent: 'center',
    alignItems: 'center',
  },

  timelineDotCompleted: {
    backgroundColor: colors.success,
    borderColor: colors.success,
  },

  timelineLine: {
    width: 2,
    flex: 1,
    minHeight: 36,
    backgroundColor: colors.border,
    marginTop: 2,
  },

  timelineLineCompleted: {
    backgroundColor: colors.success,
  },

  timelineContent: {
    flex: 1,
    paddingBottom: spacing.lg,
    paddingLeft: spacing.sm,
  },

  timelineTitle: {
    fontSize: typography.fontSize.md,
    color: colors.textSecondary,
  },

  timelineTitleCompleted: {
    color: colors.text,
    fontWeight: typography.fontWeight.semibold,
  },

  timelineDate: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  /* ---------------------------------------------------------------------- */
  /* Actions                                                                */
  /* ---------------------------------------------------------------------- */

  actions: {
    marginTop: spacing.md,
  },

  trackButton: {
    width: '100%',
  },
});

/* -------------------------------------------------------------------------- */
/*                              PropTypes & Export                            */
/* -------------------------------------------------------------------------- */

const timelineItemShape = PropTypes.shape({
  /**
   * Timeline step title.
   */
  title: PropTypes.string,

  /**
   * Whether the step has been completed.
   */
  completed: PropTypes.bool,

  /**
   * Date or timestamp for the step.
   */
  date: PropTypes.string,
});

const courierShape = PropTypes.shape({
  /**
   * Courier company name.
   */
  name: PropTypes.string,

  /**
   * Courier contact number.
   */
  phone: PropTypes.string,

  /**
   * Courier logo URL.
   */
  logo: PropTypes.string,
});

const deliveryShape = PropTypes.shape({
  /**
   * Shipment tracking number.
   */
  trackingNumber: PropTypes.string,

  /**
   * Delivery status.
   * Examples:
   * PENDING
   * PROCESSING
   * SHIPPED
   * OUT_FOR_DELIVERY
   * DELIVERED
   */
  status: PropTypes.string,

  /**
   * Courier information.
   */
  courier: courierShape,

  /**
   * Estimated delivery date.
   */
  estimatedDelivery: PropTypes.string,

  /**
   * Delivery timeline.
   */
  timeline: PropTypes.arrayOf(timelineItemShape),
});

DeliveryTrackingCard.propTypes = {
  /**
   * Delivery information.
   */
  delivery: deliveryShape,

  /**
   * Track shipment callback.
   */
  onTrackShipment: PropTypes.func,

  /**
   * Loading state.
   */
  loading: PropTypes.bool,

  /**
   * Optional style override.
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

DeliveryTrackingCard.defaultProps = {
  delivery: null,

  onTrackShipment: null,

  loading: false,

  style: null,
};

/* -------------------------------------------------------------------------- */
/*                                   Export                                   */
/* -------------------------------------------------------------------------- */

export default memo(DeliveryTrackingCard);