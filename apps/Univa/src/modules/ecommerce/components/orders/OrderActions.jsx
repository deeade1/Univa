/* -------------------------------------------------------------------------- */
/*                             OrderActions.jsx                               */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
} from 'react';

import PropTypes from 'prop-types';

import {
  View,
  TouchableOpacity,
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

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

function OrderActions({
  order,
  loading,
  showTrack,
  showDetails,
  showBuyAgain,
  showCancel,
  onTrack,
  onDetails,
  onBuyAgain,
  onCancel,
}) {
  /* ---------------------------------------------------------------------- */
  /* Handlers                                                               */
  /* ---------------------------------------------------------------------- */

  const handleTrack = useCallback(() => {
    onTrack?.(order);
  }, [order, onTrack]);

  const handleDetails = useCallback(() => {
    onDetails?.(order);
  }, [order, onDetails]);

  const handleBuyAgain = useCallback(() => {
    onBuyAgain?.(order);
  }, [order, onBuyAgain]);

  const handleCancel = useCallback(() => {
    onCancel?.(order);
  }, [order, onCancel]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View style={styles.container}>
      {/* ------------------------------------------------------------------ */}
      {/* Track Order                                                        */}
      {/* ------------------------------------------------------------------ */}

      {showTrack && (
        <TouchableOpacity
          activeOpacity={0.85}
          disabled={loading}
          accessibilityRole="button"
          accessibilityLabel="Track order"
          style={[
            styles.actionButton,
            loading && styles.disabledButton,
          ]}
          onPress={handleTrack}
        >
          <MaterialCommunityIcons
            name="truck-delivery-outline"
            size={18}
            color={colors.primary}
          />

          <Text style={styles.primaryText}>
            Track
          </Text>
        </TouchableOpacity>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* View Details                                                       */}
      {/* ------------------------------------------------------------------ */}

      {showDetails && (
        <TouchableOpacity
          activeOpacity={0.85}
          disabled={loading}
          accessibilityRole="button"
          accessibilityLabel="View order details"
          style={[
            styles.actionButton,
            loading && styles.disabledButton,
          ]}
          onPress={handleDetails}
        >
          <MaterialCommunityIcons
            name="file-document-outline"
            size={18}
            color={colors.text}
          />

          <Text style={styles.actionText}>
            Details
          </Text>
        </TouchableOpacity>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Buy Again                                                          */}
      {/* ------------------------------------------------------------------ */}

      {showBuyAgain && (
        <TouchableOpacity
          activeOpacity={0.85}
          disabled={loading}
          accessibilityRole="button"
          accessibilityLabel="Buy this order again"
          style={[
            styles.actionButton,
            styles.buyAgainButton,
            loading && styles.disabledButton,
          ]}
          onPress={handleBuyAgain}
        >
          <MaterialCommunityIcons
            name="cart-plus"
            size={18}
            color={colors.success}
          />

          <Text style={styles.successText}>
            Buy Again
          </Text>
        </TouchableOpacity>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Cancel Order                                                       */}
      {/* ------------------------------------------------------------------ */}

      {showCancel && (
        <TouchableOpacity
          activeOpacity={0.85}
          disabled={loading}
          accessibilityRole="button"
          accessibilityLabel="Cancel order"
          style={[
            styles.actionButton,
            styles.cancelButton,
            loading && styles.disabledButton,
          ]}
          onPress={handleCancel}
        >
          <MaterialCommunityIcons
            name="close-circle-outline"
            size={18}
            color={colors.error}
          />

          <Text style={styles.cancelText}>
            Cancel
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

/* -------------------------------------------------------------------------- */
/*                                   Styles                                   */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  /* ---------------------------------------------------------------------- */
  /* Container                                                              */
  /* ---------------------------------------------------------------------- */

  container: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border || '#E5E7EB',
  },

  /* ---------------------------------------------------------------------- */
  /* Base Button                                                            */
  /* ---------------------------------------------------------------------- */

  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',

    flexGrow: 1,
    minWidth: 100,

    minHeight: 42,

    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,

    borderRadius: radius.full,

    backgroundColor: colors.surface || '#F8FAFC',

    borderWidth: 1,
    borderColor: colors.border || '#E5E7EB',

    // Add margin for wrapping
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },

  /* ---------------------------------------------------------------------- */
  /* Button Variants                                                        */
  /* ---------------------------------------------------------------------- */

  buyAgainButton: {
    borderColor: colors.success,
    backgroundColor: colors.successLight || '#ECFDF5',
  },

  cancelButton: {
    borderColor: colors.error,
    backgroundColor: colors.errorLight || '#FEF2F2',
  },

  disabledButton: {
    opacity: 0.45,
  },

  /* ---------------------------------------------------------------------- */
  /* Typography                                                             */
  /* ---------------------------------------------------------------------- */

  actionText: {
    marginLeft: spacing.xs,
    color: colors.text,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
  },

  primaryText: {
    marginLeft: spacing.xs,
    color: colors.primary,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
  },

  successText: {
    marginLeft: spacing.xs,
    color: colors.success,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
  },

  cancelText: {
    marginLeft: spacing.xs,
    color: colors.error,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
  },
});

/* -------------------------------------------------------------------------- */
/*                         PropTypes & Default Props                          */
/* -------------------------------------------------------------------------- */

OrderActions.propTypes = {
  /* ---------------------------------------------------------------------- */
  /* Data                                                                   */
  /* ---------------------------------------------------------------------- */

  order: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    number: PropTypes.string,

    status: PropTypes.string,

    trackingNumber: PropTypes.string,

    paymentStatus: PropTypes.string,

    total: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    createdAt: PropTypes.string,

    lines: PropTypes.array,
  }),

  loading: PropTypes.bool,

  /* ---------------------------------------------------------------------- */
  /* Visibility                                                             */
  /* ---------------------------------------------------------------------- */

  showTrack: PropTypes.bool,

  showDetails: PropTypes.bool,

  showBuyAgain: PropTypes.bool,

  showCancel: PropTypes.bool,

  /* ---------------------------------------------------------------------- */
  /* Callbacks                                                              */
  /* ---------------------------------------------------------------------- */

  onTrack: PropTypes.func,

  onDetails: PropTypes.func,

  onBuyAgain: PropTypes.func,

  onCancel: PropTypes.func,
};

OrderActions.defaultProps = {
  order: null,

  loading: false,

  showTrack: true,

  showDetails: true,

  showBuyAgain: true,

  showCancel: false,

  onTrack: undefined,

  onDetails: undefined,

  onBuyAgain: undefined,

  onCancel: undefined,
};

/* -------------------------------------------------------------------------- */
/*                                   Display Name                             */
/* -------------------------------------------------------------------------- */

OrderActions.displayName = 'OrderActions';

/* -------------------------------------------------------------------------- */
/*                                   Export                                   */
/* -------------------------------------------------------------------------- */

export default memo(OrderActions);